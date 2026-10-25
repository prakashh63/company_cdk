# Changelog

## 0.2.0
- Default Lambda runtime is now `PYTHON_3_14` (satisfies cdk-nag AwsSolutions-L1).
- CloudWatch log groups are encrypted with a customer-managed KMS key (`encrypt_logs`, default on).
- API Gateway proxy is optional (`api_gateway.enable_proxy`), so worker Lambdas need no API.
- `s3` is optional: API-only and worker-only stacks are supported.
- New `SecureLambda` construct that works for any use case.
- Event triggers: EventBridge schedule, EventBridge event pattern, SNS topic subscription.
- Configurable CORS origins and Lambda timeout.
- `load_config` gives clear errors for missing or empty files and resolves the Lambda code
  folder relative to the config file.

## 0.1.0
- Config schemas (Pydantic) and YAML loader.
- SecureBucket, ServerlessBackend, WebDistribution constructs.
- ServerlessWebAppStack with auto-tagging and cdk-nag (AwsSolutionsChecks).
- Unit and snapshot tests, example apps.
