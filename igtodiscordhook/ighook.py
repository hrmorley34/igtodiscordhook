from datetime import datetime, timezone
import discord
import instagrapi
import instagrapi.types
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from sqlalchemy.engine import Engine
from sqlmodel import Session
from tempfile import TemporaryDirectory
from typing import Iterable, List, Optional

from .database import DB
from . import imaging


class IGHook:
    client: instagrapi.Client
    webhook: discord.SyncWebhook
    db: DB

    post_width: int = 2
    post_pad: int = 20

    def __init__(self, webhook_url: str, engine: Engine):
        self.client = instagrapi.Client()
        self.webhook = discord.SyncWebhook.from_url(webhook_url)
        self.db = DB(engine)

    def login_ig(
        self,
        username: str,
        password: str,
        settings_file: Optional[Path] = None,
    ):
        if settings_file is not None and settings_file.exists():
            self.client.load_settings(settings_file)
        self.client.login(username=username, password=password)

    def dump_settings(self, settings_file: Optional[Path] = None):
        if settings_file is not None:
            self.client.dump_settings(settings_file)

    def push_post(
        self,
        session: Session,
        user: instagrapi.types.User,
        post: instagrapi.types.Media,
    ) -> discord.SyncWebhookMessage:
        with TemporaryDirectory() as tmpdir:
            DEST_FOLDER = Path(tmpdir)

            account = self.db.get_ig_account(session, int(user.pk), self.webhook.id)
            db_post = account.make_post(session, int(post.pk))

            if post.media_type == 1:
                # media_type of 1 is photo
                paths = [self.client.photo_download(int(post.pk), DEST_FOLDER)]
            elif post.media_type == 2:
                # media_type of 2 is video/igtv/reel
                paths = [self.client.video_download(int(post.pk), DEST_FOLDER)]
            elif post.media_type == 8:
                # media_type of 8 is album
                paths = self.client.album_download(int(post.pk), DEST_FOLDER)
            else:
                raise ValueError(f"Unknown media_type: {post.media_type}")

            merged_paths: list[Path] = []
            mergeable_images: list[Image.Image] = []
            for i, p in enumerate(paths):
                merge = i == (len(paths) - 1)
                readd_path = False
                try:
                    im = imaging.load(p)
                except UnidentifiedImageError:
                    # may be video; bundle up the previous images and then put this on the end
                    merge = True
                    readd_path = True
                else:
                    mergeable_images.append(im)

                if merge:
                    for im in imaging.combine_images_row(
                        mergeable_images,
                        width=self.post_width,
                        pad=self.post_pad,
                    ):
                        merged_paths.append(imaging.save(DEST_FOLDER, im))
                        im.close()
                    for im in mergeable_images:
                        im.close()
                    mergeable_images = []
                if readd_path:
                    merged_paths.append(p)

            assert len(mergeable_images) == 0

            files = [
                discord.File(p, filename=f"page{i}{p.suffix}")
                for i, p in enumerate(merged_paths)
            ]

            try:
                embed = discord.Embed(
                    description=discord.utils.escape_markdown(post.caption_text),
                    timestamp=post.taken_at,
                )
                embed.set_author(name=user.username, icon_url=str(user.profile_pic_url))

                msg = self.webhook.send(
                    username=user.username,
                    avatar_url=str(user.profile_pic_url),
                    embed=embed,
                    files=files,
                    wait=True,
                )
                db_post.webhook_message_id = msg.id
                return msg
            finally:
                for f in files:
                    f.close()

    def delete_post(self, webhook_id: int) -> None:
        self.webhook.delete_message(webhook_id)

    def get_all_posts(
        self,
        session: Session,
        user: instagrapi.types.User,
    ) -> Iterable[instagrapi.types.Media]:
        "Get all posts published after database min_time, and return them in reverse chronological order"
        db_account = self.db.get_ig_account(session, int(user.pk), self.webhook.id)

        last_dt = datetime.utcnow().replace(tzinfo=timezone.utc)
        while last_dt >= db_account.aware_min_time:
            end_cursor = ""
            posts, end_cursor = self.client.user_medias_paginated(
                int(user.pk), end_cursor=end_cursor
            )
            for post in posts:
                last_dt = post.taken_at
                if last_dt < db_account.aware_min_time:
                    break
                yield post

    def filter_unsent_posts(
        self,
        session: Session,
        user: instagrapi.types.User,
        posts: Iterable[instagrapi.types.Media],
    ) -> List[instagrapi.types.Media]:
        unsent_posts: List[instagrapi.types.Media] = []

        db_account = self.db.get_ig_account(session, int(user.pk), self.webhook.id)
        existing_pks = {
            p.ig_pk for p in db_account.ig_posts if p.webhook_message_id is not None
        }

        for post in posts:
            last_dt = post.taken_at
            if last_dt < db_account.aware_min_time:
                break
            if int(post.pk) in existing_pks:
                continue
            unsent_posts.insert(0, post)

        return unsent_posts

    def push_unsent_posts(
        self,
        user: instagrapi.types.User,
        posts: Iterable[instagrapi.types.Media],
    ) -> None:
        with self.db.session() as session:
            unsents = self.filter_unsent_posts(session, user, posts)
            session.commit()

            for post in unsents:
                self.push_post(session, user, post)
                session.commit()

    def delete_missing_posts(
        self,
        user: instagrapi.types.User,
        posts: Iterable[instagrapi.types.Media],
    ) -> None:
        with self.db.session() as session:
            db_account = self.db.get_ig_account(session, int(user.pk), self.webhook.id)
            existing_pks = {int(p.pk) for p in posts}

            for db_post in db_account.ig_posts:
                if db_post.webhook_message_id is None:
                    continue
                if db_post.ig_pk not in existing_pks:
                    self.delete_post(db_post.webhook_message_id)
                    session.delete(db_post)
                    session.commit()
