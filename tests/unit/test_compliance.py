from collections.abc import Callable

import aws_cdk as cdk

from company_cdk import ServerlessWebAppStack
from company_cdk.aspects import enable_compliance_checks
from company_cdk.configs import WebAppConfig

MARKER_ID = "CompanyCdkNagEnabled"


def markers(app: cdk.App) -> list[str]:
    return [child.node.id for child in app.node.children if child.node.id == MARKER_ID]


def test_compliance_registered_only_once_per_app() -> None:
    app = cdk.App()
    enable_compliance_checks(cdk.Stack(app, "A"))
    enable_compliance_checks(cdk.Stack(app, "B"))
    assert len(markers(app)) == 1


def test_stack_enables_compliance_by_default(make_config: Callable[..., WebAppConfig]) -> None:
    app = cdk.App()
    ServerlessWebAppStack(app, "WithNag", config=make_config())
    assert len(markers(app)) == 1


def test_stack_can_skip_compliance(make_config: Callable[..., WebAppConfig]) -> None:
    app = cdk.App()
    ServerlessWebAppStack(app, "NoNag", config=make_config(), enable_compliance=False)
    assert markers(app) == []
