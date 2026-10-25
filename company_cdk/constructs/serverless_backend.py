"""ServerlessBackend: SecureLambda plus an optional API Gateway proxy."""

from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_kms as kms
from constructs import Construct

from ..configs import ApiGatewayConfig, LambdaConfig
from .api_proxy import ApiGatewayProxy
from .secure_lambda import SecureLambda


class ServerlessBackend(Construct):
    """Lambda function, and (when api_config.enable_proxy is true) the API in front of it."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        lambda_config: LambdaConfig,
        api_config: ApiGatewayConfig,
        environment: str,
        log_key: kms.IKey | None = None,
    ) -> None:
        super().__init__(scope, construct_id)

        self.secure_lambda = SecureLambda(
            self,
            "Lambda",
            lambda_config=lambda_config,
            environment=environment,
            log_key=log_key,
        )
        self.function = self.secure_lambda.function

        self.rest_api: apigw.RestApi | None = None
        if api_config.enable_proxy:
            proxy = ApiGatewayProxy(
                self,
                "Api",
                handler=self.function,
                api_config=api_config,
                environment=environment,
                log_key=log_key,
            )
            self.rest_api = proxy.rest_api
