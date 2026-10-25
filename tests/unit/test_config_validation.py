from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from company_cdk.configs import (
    ApiGatewayConfig,
    EventRuleTriggerConfig,
    LambdaConfig,
    S3Config,
    ScheduleTriggerConfig,
    WebAppConfig,
    load_config,
)

ROOT = Path(__file__).parents[2]


def valid_data() -> dict[str, Any]:
    return {
        "app_name": "demo",
        "environment": "dev",
        "owner_team": "team-a",
        "s3": {"bucket_name": "demo-assets-bucket"},
        "lambda_backend": {"function_name": "fn", "entry_point_dir": "src"},
    }


def write_yaml(folder: Path, body: str) -> Path:
    (folder / "code").mkdir(exist_ok=True)
    path = folder / "config.yaml"
    path.write_text(body)
    return path


def test_valid_config_loads_with_defaults() -> None:
    config = WebAppConfig.model_validate(valid_data())
    assert config.lambda_backend.memory_mb == 512
    assert config.lambda_backend.runtime == "PYTHON_3_14"
    assert config.lambda_backend.timeout_seconds == 30
    assert config.api_gateway.enable_proxy is True
    assert config.api_gateway.stage_name == "prod"
    assert config.encrypt_logs is True
    assert config.triggers.schedule is None


def test_worker_config_without_s3_is_valid() -> None:
    data = valid_data()
    del data["s3"]
    data["api_gateway"] = {"enable_proxy": False}
    config = WebAppConfig.model_validate(data)
    assert config.s3 is None
    assert config.api_gateway.enable_proxy is False


def test_memory_below_minimum_rejected() -> None:
    with pytest.raises(ValidationError):
        LambdaConfig(function_name="fn", entry_point_dir="src", memory_mb=50)


def test_memory_above_maximum_rejected() -> None:
    with pytest.raises(ValidationError):
        LambdaConfig(function_name="fn", entry_point_dir="src", memory_mb=4000)


def test_unknown_environment_rejected() -> None:
    data = valid_data()
    data["environment"] = "qa"
    with pytest.raises(ValidationError):
        WebAppConfig.model_validate(data)


def test_unknown_runtime_rejected() -> None:
    with pytest.raises(ValidationError):
        LambdaConfig(function_name="fn", entry_point_dir="src", runtime="PYTHON_9_99")


def test_unknown_field_rejected() -> None:
    data = valid_data()
    data["memory_mbb"] = 1
    with pytest.raises(ValidationError):
        WebAppConfig.model_validate(data)


def test_bad_bucket_name_rejected() -> None:
    with pytest.raises(ValidationError):
        S3Config(bucket_name="Bad_Name")


def test_bad_stage_name_rejected() -> None:
    with pytest.raises(ValidationError):
        ApiGatewayConfig(stage_name="bad stage!")


def test_bad_schedule_expression_rejected() -> None:
    with pytest.raises(ValidationError):
        ScheduleTriggerConfig(expression="every day")


def test_event_rule_requires_a_source() -> None:
    with pytest.raises(ValidationError):
        EventRuleTriggerConfig(source=[])


def test_load_example_configs() -> None:
    web = load_config(ROOT / "examples" / "config.yaml")
    assert web.app_name == "customer-portal"
    assert Path(web.lambda_backend.entry_point_dir).is_absolute()

    worker = load_config(ROOT / "examples" / "worker" / "config.yaml")
    assert worker.s3 is None
    assert worker.api_gateway.enable_proxy is False
    assert worker.triggers.sns is not None
    assert worker.triggers.schedule is not None
    assert worker.triggers.event_rule is not None


def test_entry_point_resolved_relative_to_config(tmp_path: Path) -> None:
    path = write_yaml(
        tmp_path,
        "app_name: x\nenvironment: dev\nowner_team: t\n"
        "lambda_backend:\n  function_name: f\n  entry_point_dir: code\n",
    )
    config = load_config(path)
    assert config.lambda_backend.entry_point_dir == str((tmp_path / "code").resolve())


def test_load_invalid_yaml_rejected(tmp_path: Path) -> None:
    path = write_yaml(
        tmp_path,
        "app_name: x\nenvironment: dev\nowner_team: t\n"
        "lambda_backend:\n  function_name: f\n  entry_point_dir: code\n  memory_mb: 50\n",
    )
    with pytest.raises(ValidationError):
        load_config(path)


def test_empty_yaml_gives_clear_error(tmp_path: Path) -> None:
    empty = tmp_path / "empty.yaml"
    empty.write_text("")
    with pytest.raises(ValueError, match="empty or is not a YAML mapping"):
        load_config(empty)


def test_missing_file_gives_clear_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Config file not found"):
        load_config(tmp_path / "nope.yaml")


def test_missing_code_folder_gives_clear_error(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        "app_name: x\nenvironment: dev\nowner_team: t\n"
        "lambda_backend:\n  function_name: f\n  entry_point_dir: missing_folder\n"
    )
    with pytest.raises(FileNotFoundError, match="Lambda code folder not found"):
        load_config(path)
