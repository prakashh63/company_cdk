"""Environment-dependent rules shared by several constructs."""

from aws_cdk import RemovalPolicy
from aws_cdk import aws_logs as logs

_RETENTION: dict[str, logs.RetentionDays] = {
    "dev": logs.RetentionDays.ONE_WEEK,  # 7 days
    "staging": logs.RetentionDays.ONE_MONTH,  # 30 days (assumption: spec defines dev and prod)
    "prod": logs.RetentionDays.THREE_MONTHS,  # 90 days
}


def log_retention(environment: str) -> logs.RetentionDays:
    """dev 7 days, staging 30 days, prod 90 days."""
    return _RETENTION[environment]


def removal_policy(environment: str) -> RemovalPolicy:
    """Keep data in prod; everything else is removed by `cdk destroy`."""
    return RemovalPolicy.RETAIN if environment == "prod" else RemovalPolicy.DESTROY
