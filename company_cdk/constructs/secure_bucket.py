"""SecureBucket: an S3 bucket with the company's security rules baked in."""

from aws_cdk import Acknowledgment, Validations
from aws_cdk import aws_s3 as s3
from constructs import Construct

from ._common import removal_policy


class SecureBucket(Construct):
    """Private, encrypted S3 bucket. Versioned in prod."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        bucket_name: str,
        environment: str,
        auto_delete_objects: bool = False,
    ) -> None:
        super().__init__(scope, construct_id)

        is_prod = environment == "prod"

        self.bucket = s3.Bucket(
            self,
            "Bucket",
            bucket_name=bucket_name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=is_prod,
            removal_policy=removal_policy(environment),
            # CDK allows auto-delete only together with DESTROY, so never in prod
            auto_delete_objects=auto_delete_objects and not is_prod,
        )

        Validations.of(self.bucket).acknowledge(
            Acknowledgment(
                id="AwsSolutions::AwsSolutions-S1",
                reason="Server access logging needs a dedicated log bucket; tracked improvement.",
            )
        )
