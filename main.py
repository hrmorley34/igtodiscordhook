from dotenv import load_dotenv
import json
from os import environ
from pathlib import Path
from sqlmodel import create_engine

from igtodiscordhook.ighook import IGHookManager


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

    for accopts in OPTIONS["accounts"]:
        USER_USERNAME = accopts["igaccount"]
        USER_ID = manager.username_to_id(USER_USERNAME)
        ighook = manager.get_hook(USER_ID, accopts["webhook"])
        ighook.update_hook()

    manager.dump_settings(settings_file=SETTINGS_FILE)
