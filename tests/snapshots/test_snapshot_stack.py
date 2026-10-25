from pathlib import Path
from typing import Any

import aws_cdk as cdk
from aws_cdk.assertions import Template
from syrupy.assertion import SnapshotAssertion

from company_cdk import ServerlessWebAppStack
from company_cdk.configs import WebAppConfig

LAMBDA_SRC = Path(__file__).parents[1] / "fixtures" / "lambda_src"


def synth(**overrides: Any) -> Any:
    data: dict[str, Any] = {
        "app_name": "snapshot-app",
        "environment": "dev",
        "owner_team": "platform",
        "cost_center": "CC-1",
        "s3": {"bucket_name": "snapshot-assets-bucket"},
        "lambda_backend": {"function_name": "snap-fn", "entry_point_dir": str(LAMBDA_SRC)},
    }
    data.update(overrides)
    app = cdk.App(context={"aws:cdk:version-reporting": False})
    config = WebAppConfig.model_validate(data)
    stack = ServerlessWebAppStack(app, "SnapStack", config=config, enable_compliance=False)
    return Template.from_stack(stack).to_json()


def test_dev_stack_snapshot(snapshot: SnapshotAssertion) -> None:
    assert synth() == snapshot


def test_prod_stack_snapshot(snapshot: SnapshotAssertion) -> None:
    assert synth(environment="prod") == snapshot


def test_worker_stack_snapshot(snapshot: SnapshotAssertion) -> None:
    worker = synth(
        s3=None,
        api_gateway={"enable_proxy": False},
        triggers={
            "schedule": {"expression": "rate(1 hour)"},
            "event_rule": {"source": ["orders.service"], "detail_type": ["Order Created"]},
            "sns": {"topic_name": "snapshot-topic"},
        },
    )
    assert worker == snapshot
