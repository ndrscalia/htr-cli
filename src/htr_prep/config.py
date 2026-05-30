from pathlib import Path

import keyring
import tomllib
import tomli_w
from platformdirs import user_config_dir

SERVICE = "htr-prep"
CONFIG_DIR = Path(user_config_dir(appname=SERVICE))
CONFIG_FILE = CONFIG_DIR / "config.toml"


def load() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE, "rb") as f:
        return tomllib.load(f)


def save(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(data, f)


def set_email(email: str) -> None:
    data = load()
    data["email"] = email
    save(data)


def get_email() -> str | None:
    return load().get("email")


def set_password(password: str) -> None:
    keyring.set_password(service_name=SERVICE, username="password", password=password)


def get_password() -> str | None:
    return keyring.get_password(service_name=SERVICE, username="password")
