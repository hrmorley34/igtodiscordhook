import discord
import instagrapi
import instagrapi.types
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional


class IGHook:
    client: instagrapi.Client
    webhook: discord.SyncWebhook

    def __init__(self, url: str):
        self.client = instagrapi.Client()
        self.webhook = discord.SyncWebhook.from_url(url)

    def login_ig(
        self, username: str, password: str, settings_file: Optional[Path] = None
    ):
        if settings_file is not None and settings_file.exists():
            self.client.load_settings(settings_file)
        self.client.login(username=username, password=password)

    def dump_settings(self, settings_file: Optional[Path] = None):
        if settings_file is not None:
            self.client.dump_settings(settings_file)

    def push_post(
        self,
        user: instagrapi.types.User,
        post: instagrapi.types.Media,
    ) -> discord.SyncWebhookMessage:
        with TemporaryDirectory() as tmpdir:
            DEST_FOLDER = Path(tmpdir)

            paths = self.client.album_download(int(post.pk), DEST_FOLDER)
            files = [
                discord.File(p, filename=f"page{i}{p.suffix}")
                for i, p in enumerate(paths)
            ]

            try:
                embed = discord.Embed(
                    description=discord.utils.escape_markdown(post.caption_text),
                    timestamp=post.taken_at,
                )
                embed.set_author(name=user.username, icon_url=str(user.profile_pic_url))

                return self.webhook.send(
                    username=user.username,
                    avatar_url=str(user.profile_pic_url),
                    embed=embed,
                    files=files,
                    wait=True,
                )
            finally:
                for f in files:
                    f.close()
