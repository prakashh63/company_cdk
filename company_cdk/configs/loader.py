"""Load and validate a YAML configuration file."""

from pathlib import Path
from typing import Any

import yaml

from .models import WebAppConfig


def load_config(path: str | Path) -> WebAppConfig:
    """Read a YAML file and return a validated WebAppConfig.

    A relative lambda_backend.entry_point_dir is resolved from the folder that
    contains the config file, so the app works no matter where it is started from.
    """
    config_path = Path(path)
    if not config_path.is_file():
        raise FileNotFoundError(f"Config file not found: {config_path.resolve()}")

    with open(config_path, encoding="utf-8") as handle:
        data: Any = yaml.safe_load(handle)

    is_mapping = isinstance(data, dict)
    if not is_mapping:
        raise ValueError(
            f"{config_path} is empty or is not a YAML mapping. "
            "Expected key: value pairs such as 'app_name: my-app'."
        )

    config = WebAppConfig.model_validate(data)

    code_dir = Path(config.lambda_backend.entry_point_dir)
    if not code_dir.is_absolute():
        code_dir = (config_path.resolve().parent / code_dir).resolve()
    if not code_dir.is_dir():
        raise FileNotFoundError(f"Lambda code folder not found: {code_dir}")
    config.lambda_backend.entry_point_dir = str(code_dir)
    return config
