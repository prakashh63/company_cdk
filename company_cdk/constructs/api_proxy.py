"""ApiGatewayProxy: optional REST API that forwards every route to a Lambda function."""

from aws_cdk import Acknowledgment, Validations
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_kms as kms
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_logs as logs
from constructs import Construct

from ..configs import ApiGatewayConfig
from ._common import log_retention, removal_policy


class ApiGatewayProxy(Construct):
    """REST API with proxy integration, CORS, throttling, access logs and request validation."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        handler: _lambda.IFunction,
        api_config: ApiGatewayConfig,
        environment: str,
        log_key: kms.IKey | None = None,
    ) -> None:
        super().__init__(scope, construct_id)

        self.access_log_group = logs.LogGroup(
            self,
            "AccessLogs",
            retention=log_retention(environment),
            removal_policy=removal_policy(environment),
            encryption_key=log_key,
        )

        cors = (
            apigw.CorsOptions(
                allow_origins=api_config.cors_allowed_origins,
                allow_methods=apigw.Cors.ALL_METHODS,
            )
            if api_config.enable_cors
            else None
        )

        self.rest_api = apigw.LambdaRestApi(
            self,
            "Api",
            handler=handler,
            proxy=True,
            cloud_watch_role=True,
            default_cors_preflight_options=cors,
            deploy_options=apigw.StageOptions(
                stage_name=api_config.stage_name,
                throttling_rate_limit=api_config.rate_limit,
                throttling_burst_limit=api_config.burst_limit,
                logging_level=apigw.MethodLoggingLevel.ERROR,
                access_log_destination=apigw.LogGroupLogDestination(self.access_log_group),
                access_log_format=apigw.AccessLogFormat.clf(),
            ),
        )

        # Fixes AwsSolutions-APIG2 (request validation)
        self.rest_api.add_request_validator(
            "RequestValidator",
            validate_request_body=True,
            validate_request_parameters=True,
        )

        # Accepted cdk-nag findings, each with a written reason
        Validations.of(self.rest_api).acknowledge(
            Acknowledgment(
                id="AwsSolutions::AwsSolutions-APIG4",
                reason="Auth is not in the current spec; add an authorizer per application.",
            ),
            Acknowledgment(
                id="AwsSolutions::AwsSolutions-COG4",
                reason="No Cognito user pool in the current spec; identity is app-specific.",
            ),
            Acknowledgment(
                id="AwsSolutions::AwsSolutions-APIG3",
                reason="WAF is a paid add-on; enable per application when required.",
            ),
            Acknowledgment(
                id=(
                    "AwsSolutions::AwsSolutions-IAM4"
                    "[Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/"
                    "AmazonAPIGatewayPushToCloudWatchLogs]"
                ),
                reason="AWS-managed service role that API Gateway needs to push logs to CloudWatch.",
            ),
        )
