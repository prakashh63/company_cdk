"""LogKey: customer-managed KMS key that encrypts CloudWatch log groups."""

from aws_cdk import Aws, Duration
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from constructs import Construct

from ._common import removal_policy


class LogKey(Construct):
    """KMS key with rotation. Only CloudWatch Logs (in this account) may use it for logs."""

    def __init__(self, scope: Construct, construct_id: str, *, environment: str) -> None:
        super().__init__(scope, construct_id)

        self.key = kms.Key(
            self,
            "Key",
            description="company_cdk: encrypts CloudWatch log groups",
            enable_key_rotation=True,
            removal_policy=removal_policy(environment),
            pending_window=Duration.days(7),
        )

        self.key.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCloudWatchLogs",
                principals=[iam.ServicePrincipal(f"logs.{Aws.REGION}.amazonaws.com")],
                actions=[
                    "kms:Encrypt*",
                    "kms:Decrypt*",
                    "kms:ReEncrypt*",
                    "kms:GenerateDataKey*",
                    "kms:Describe*",
                ],
                resources=["*"],
                conditions={
                    "ArnLike": {
                        "kms:EncryptionContext:aws:logs:arn": (
                            f"arn:{Aws.PARTITION}:logs:{Aws.REGION}:{Aws.ACCOUNT_ID}:*"
                        )
                    }
                },
            )
        )
