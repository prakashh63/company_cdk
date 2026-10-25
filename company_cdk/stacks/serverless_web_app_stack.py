"""ServerlessWebAppStack: the one class a developer needs."""

from typing import Any

from aws_cdk import Aspects, CfnOutput, Stack
from constructs import Construct

from ..aspects import TaggingAspect, enable_compliance_checks
from ..configs import WebAppConfig
from ..constructs import (
    LambdaTriggers,
    LogKey,
    SecureBucket,
    ServerlessBackend,
    WebDistribution,
)


class ServerlessWebAppStack(Stack):
    """Lambda, plus whatever the config asks for: S3 + CloudFront, API Gateway, triggers."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: WebAppConfig,
        enable_compliance: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.config = config
        environment = config.environment

        # 1. Optional customer-managed key for CloudWatch log encryption
        self.log_key: LogKey | None = (
            LogKey(self, "LogKey", environment=environment) if config.encrypt_logs else None
        )
        key = self.log_key.key if self.log_key is not None else None

        # 2. Optional private frontend bucket
        self.web_bucket: SecureBucket | None = None
        if config.s3 is not None:
            self.web_bucket = SecureBucket(
                self,
                "WebBucket",
                bucket_name=config.s3.bucket_name,
                environment=environment,
                auto_delete_objects=config.s3.auto_delete_objects,
            )

        # 3. Lambda (+ API Gateway proxy when enabled)
        self.backend = ServerlessBackend(
            self,
            "Backend",
            lambda_config=config.lambda_backend,
            api_config=config.api_gateway,
            environment=environment,
            log_key=key,
        )

        # 4. Optional EventBridge / SNS triggers (creates nothing for an empty config)
        self.triggers = LambdaTriggers(
            self, "Triggers", function=self.backend.function, config=config.triggers
        )

        # 5. CloudFront, only when there is a frontend bucket
        self.cdn: WebDistribution | None = None
        if self.web_bucket is not None:
            self.cdn = WebDistribution(
                self, "Cdn", bucket=self.web_bucket.bucket, api=self.backend.rest_api
            )
            CfnOutput(
                self, "SiteUrl", value=f"https://{self.cdn.distribution.distribution_domain_name}"
            )
            CfnOutput(self, "BucketName", value=self.web_bucket.bucket.bucket_name)

        CfnOutput(self, "FunctionName", value=self.backend.function.function_name)
        if self.triggers.topic is not None:
            CfnOutput(self, "TopicArn", value=self.triggers.topic.topic_arn)

        # 6. Governance: standard tags on every taggable resource
        tags = {
            "Environment": environment,
            "Owner": config.owner_team,
            "ManagedBy": "company_cdk",
        }
        if config.cost_center:
            tags["CostCenter"] = config.cost_center
        Aspects.of(self).add(TaggingAspect(tags))

        # 7. Governance: security gate (cdk-nag AwsSolutionsChecks)
        if enable_compliance:
            enable_compliance_checks(self)
