# Same stack, configured in Python instead of YAML (the sample from the assignment).
import aws_cdk as cdk

from company_cdk import ServerlessWebAppStack
from company_cdk.configs import ApiGatewayConfig, LambdaConfig, S3Config, WebAppConfig

app = cdk.App()

config = WebAppConfig(
    app_name="customer-portal",
    environment="prod",
    owner_team="frontend-devs",
    s3=S3Config(bucket_name="cust-portal-web-assets-prod"),
    lambda_backend=LambdaConfig(
        function_name="portal-api-handler",
        entry_point_dir="src/backend_lambda",  # relative to the folder you run cdk from
        memory_mb=1024,
        environment_vars={"TABLE_NAME": "Customers"},
    ),
    api_gateway=ApiGatewayConfig(stage_name="v1", rate_limit=2000),
)

ServerlessWebAppStack(app, "CustomerPortalProdStack", config=config)
app.synth()
