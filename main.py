from dotenv import load_dotenv
import json
from os import environ
from pathlib import Path

from ighook import IGHook


if __name__ == "__main__":
    load_dotenv()
    CREDENTIALS = dict(
        username=environ["INSTAGRAM_USERNAME"],
        password=environ["INSTAGRAM_PASSWORD"],
    )
    with open("options.json", "r") as f:
        OPTIONS = json.load(f)
    USER_USERNAME = OPTIONS["igaccount"]
    SETTINGS_FILE = Path("./instagrapi_settings.json")

    ighook = IGHook(OPTIONS["webhook"])
    ighook.login_ig(**CREDENTIALS)

    USER_DATA = ighook.client.user_info_by_username(USER_USERNAME)
    USER_ID = int(USER_DATA.pk)
    medias = ighook.client.user_medias(USER_ID, 1)
    msg = ighook.push_post(USER_DATA, medias[0])
    print(msg.id)
