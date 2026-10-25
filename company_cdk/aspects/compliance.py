"""Compliance: runs cdk-nag AwsSolutionsChecks against the whole app."""

from typing import cast

from aws_cdk import Validations
from cdk_nag import AwsSolutionsChecks
from constructs import Construct, IConstruct

_MARKER_ID = "CompanyCdkNagEnabled"


def enable_compliance_checks(scope: IConstruct) -> None:
    """Register AwsSolutionsChecks once per app (safe to call from many stacks)."""
    root = cast(Construct, scope.node.root)  # the App is always a Construct
    if root.node.try_find_child(_MARKER_ID) is not None:
        return
    Construct(root, _MARKER_ID)  # marker so the plugin is never registered twice
    Validations.of(root).add_plugins(AwsSolutionsChecks(root))
