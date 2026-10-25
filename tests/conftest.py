from collections.abc import Callable
from pathlib import Path
from typing import Any

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Template

from company_cdk import ServerlessWebAppStack
from company_cdk.configs import WebAppConfig


def pytest_configure(config: pytest.Config) -> None:
    """First run only: let syrupy create the snapshot files when none exist yet."""
    snapshots_dir = Path(__file__).parent / "snapshots" / "__snapshots__"
    if not snapshots_dir.exists() and hasattr(config.option, "update_snapshots"):
        config.option.update_snapshots = True


@pytest.fixture
def lambda_dir(tmp_path: Path) -> str:
    """A tiny Lambda source folder."""
    source = tmp_path / "lambda_src"
    source.mkdir()
    (source / "index.py").write_text("def handler(event, context):\n    return {}\n")
    return str(source)


@pytest.fixture
def make_config(lambda_dir: str) -> Callable[..., WebAppConfig]:
    """Build a valid WebAppConfig; keyword overrides replace whole top-level keys."""

    def _make(**overrides: Any) -> WebAppConfig:
        data: dict[str, Any] = {
            "app_name": "demo",
            "environment": "dev",
            "owner_team": "team-a",
            "s3": {"bucket_name": "demo-assets-bucket"},
            "lambda_backend": {"function_name": "demo-fn", "entry_point_dir": lambda_dir},
        }
        data.update(overrides)
        return WebAppConfig.model_validate(data)

    return _make


@pytest.fixture
def build(make_config: Callable[..., WebAppConfig]) -> Callable[..., Template]:
    """Synthesize a ServerlessWebAppStack (without cdk-nag) and return its Template."""

    def _build(**overrides: Any) -> Template:
        config = make_config(**overrides)
        stack = ServerlessWebAppStack(
            cdk.App(), "TestStack", config=config, enable_compliance=False
        )
        return Template.from_stack(stack)

    return _build
