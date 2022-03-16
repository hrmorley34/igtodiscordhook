from dotenv import load_dotenv
import instagrapi.types
import json
from os import environ
from pathlib import Path
from sqlmodel import create_engine

from igtodiscordhook.ighook import IGHook, IGHookManager


if __name__ == "__main__":
    load_dotenv()
    CREDENTIALS = dict(
        username=environ["INSTAGRAM_USERNAME"],
        password=environ["INSTAGRAM_PASSWORD"],
    )
    with open("options.json", "r") as f:
        OPTIONS = json.load(f)
    SETTINGS_FILE = Path("./instagrapi_settings.json")

    engine = create_engine("sqlite:///database.db", echo=False)

    manager = IGHookManager(engine)
    manager.login_ig(**CREDENTIALS, settings_file=SETTINGS_FILE)

    all_unsents: list[tuple[IGHook, instagrapi.types.Media]] = []
    for accopts in OPTIONS["accounts"]:
        USER_USERNAME = accopts["igaccount"]
        ighook = manager.get_hook_from_username(USER_USERNAME, accopts["webhook"])

        with ighook.db.session() as session:
            posts = list(ighook.get_all_posts(session))
            unsents = ighook.filter_unsent_posts(session, posts)
            session.commit()

        for post in unsents:
            all_unsents.append((ighook, post))

        ighook.delete_missing_posts(posts)

    all_unsents.sort(key=lambda pair: pair[1].taken_at)
    for ighook, post in all_unsents:
        ighook.push_post(post)

    manager.dump_settings(settings_file=SETTINGS_FILE)
