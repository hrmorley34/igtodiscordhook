from dotenv import load_dotenv
import json
from os import environ
from pathlib import Path
from sqlmodel import create_engine

from igtodiscordhook.ighook import IGHook


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

    engine = create_engine("sqlite:///database.db", echo=False)

    ighook = IGHook(OPTIONS["webhook"], engine)
    ighook.login_ig(**CREDENTIALS)

    USER_DATA = ighook.client.user_info_by_username(USER_USERNAME)

    with ighook.db.session() as session:
        posts = list(ighook.get_all_posts(session, USER_DATA))
    ighook.push_unsent_posts(USER_DATA, posts)
    ighook.delete_missing_posts(USER_DATA, posts)
