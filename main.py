import discord
import instagrapi
import instagrapi.types
from dotenv import load_dotenv
import json
from os import environ
from pathlib import Path
from tempfile import TemporaryDirectory


def push_post(
    client: instagrapi.Client,
    user: instagrapi.types.User,
    post: instagrapi.types.Media,
    webhook: discord.SyncWebhook,
) -> discord.SyncWebhookMessage:
    with TemporaryDirectory() as tmpdir:
        DEST_FOLDER = Path(tmpdir)
        post.taken_at

        paths = client.album_download(int(post.pk), DEST_FOLDER)
        files = [
            discord.File(p, filename=f"page{i}{p.suffix}") for i, p in enumerate(paths)
        ]

        try:
            embed = discord.Embed(
                description=discord.utils.escape_markdown(post.caption_text)
            )
            embed.set_author(name=user.username, icon_url=str(user.profile_pic_url))

            return webhook.send(
                username=user.username,
                avatar_url=str(user.profile_pic_url),
                embed=embed,
                files=files,
                wait=True,
            )
        finally:
            for f in files:
                f.close()


if __name__ == "__main__":
    load_dotenv()
    CREDENTIALS = dict(
        username=environ["INSTAGRAM_USERNAME"],
        password=environ["INSTAGRAM_PASSWORD"],
    )
    with open("options.json", "r") as f:
        CLIENT_DATA = json.load(f)
    USER_USERNAME = CLIENT_DATA["igaccount"]
    SETTINGS_FILE = Path("./instagrapi_settings.json")

    client = instagrapi.Client()
    webhook = discord.SyncWebhook.from_url(CLIENT_DATA["webhook"])

    if SETTINGS_FILE.exists():
        client.load_settings(SETTINGS_FILE)
    client.login(**CREDENTIALS)
    client.dump_settings(SETTINGS_FILE)

    USER_DATA = client.user_info_by_username(USER_USERNAME)
    USER_ID = int(USER_DATA.pk)
    medias = client.user_medias(USER_ID, 1)
    msg = push_post(client, USER_DATA, medias[0], webhook)
    print(msg.id)
