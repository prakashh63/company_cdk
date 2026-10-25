import json
from collections.abc import Callable

from aws_cdk.assertions import Match, Template

Build = Callable[..., Template]

CACHING_DISABLED_POLICY_ID = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"


def test_default_resource_counts(build: Build) -> None:
    t = build()
    t.resource_count_is("AWS::S3::Bucket", 1)
    t.resource_count_is("AWS::Lambda::Function", 1)
    t.resource_count_is("AWS::ApiGateway::RestApi", 1)
    t.resource_count_is("AWS::CloudFront::Distribution", 1)
    t.resource_count_is("AWS::KMS::Key", 1)


def test_oac_is_used(build: Build) -> None:
    build().resource_count_is("AWS::CloudFront::OriginAccessControl", 1)


def test_s3_origin_uses_oac(build: Build) -> None:
    build().has_resource_properties(
        "AWS::CloudFront::Distribution",
        {
            "DistributionConfig": {
                "Origins": Match.array_with(
                    [Match.object_like({"OriginAccessControlId": Match.any_value()})]
                )
            }
        },
    )


def test_bucket_policy_allows_only_cloudfront(build: Build) -> None:
    build().has_resource_properties(
        "AWS::S3::BucketPolicy",
        {
            "PolicyDocument": {
                "Statement": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Action": "s3:GetObject",
                                "Principal": {"Service": "cloudfront.amazonaws.com"},
                            }
                        )
                    ]
                )
            }
        },
    )


def test_https_redirect_on_all_behaviors(build: Build) -> None:
    build().has_resource_properties(
        "AWS::CloudFront::Distribution",
        {
            "DistributionConfig": {
                "DefaultCacheBehavior": {"ViewerProtocolPolicy": "redirect-to-https"},
                "CacheBehaviors": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "PathPattern": "/api/*",
                                "ViewerProtocolPolicy": "redirect-to-https",
                            }
                        )
                    ]
                ),
            }
        },
    )


def test_api_behavior_allows_all_methods_and_disables_cache(build: Build) -> None:
    template = build()
    for method in ["POST", "PUT", "PATCH", "DELETE"]:
        template.has_resource_properties(
            "AWS::CloudFront::Distribution",
            {
                "DistributionConfig": {
                    "CacheBehaviors": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "PathPattern": "/api/*",
                                    "AllowedMethods": Match.array_with([method]),
                                    "CachePolicyId": CACHING_DISABLED_POLICY_ID,
                                }
                            )
                        ]
                    )
                }
            },
        )


def test_default_root_object_is_index_html(build: Build) -> None:
    build().has_resource_properties(
        "AWS::CloudFront::Distribution",
        {"DistributionConfig": {"DefaultRootObject": "index.html"}},
    )


def test_api_origin_is_https_only(build: Build) -> None:
    build().has_resource_properties(
        "AWS::CloudFront::Distribution",
        {
            "DistributionConfig": {
                "Origins": Match.array_with(
                    [
                        Match.object_like(
                            {"CustomOriginConfig": {"OriginProtocolPolicy": "https-only"}}
                        )
                    ]
                )
            }
        },
    )


def test_no_wildcard_iam_actions(build: Build) -> None:
    policies = build().find_resources("AWS::IAM::Policy")
    assert policies, "expected at least one IAM policy"
    for policy in policies.values():
        for statement in policy["Properties"]["PolicyDocument"]["Statement"]:
            action = statement["Action"]
            actions = action if isinstance(action, list) else [action]
            assert "*" not in actions


def test_iam_is_least_privilege(build: Build) -> None:
    build().has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
                                "Effect": "Allow",
                            }
                        )
                    ]
                )
            }
        },
    )


def test_prod_differs_from_dev(build: Build) -> None:
    prod = build(environment="prod")
    prod.has_resource_properties(
        "AWS::S3::Bucket", {"VersioningConfiguration": {"Status": "Enabled"}}
    )
    prod.resource_properties_count_is("AWS::Logs::LogGroup", {"RetentionInDays": 90}, 2)

    dev = build(environment="dev")
    dev.has_resource_properties("AWS::S3::Bucket", {"VersioningConfiguration": Match.absent()})
    dev.resource_properties_count_is("AWS::Logs::LogGroup", {"RetentionInDays": 7}, 2)


def test_staging_retention_is_30_days(build: Build) -> None:
    build(environment="staging").resource_properties_count_is(
        "AWS::Logs::LogGroup", {"RetentionInDays": 30}, 2
    )


def test_lambda_defaults(build: Build) -> None:
    build().has_resource_properties(
        "AWS::Lambda::Function",
        {"MemorySize": 512, "Runtime": "python3.14", "Timeout": 30},
    )


def test_lambda_custom_settings(build: Build, lambda_dir: str) -> None:
    template = build(
        lambda_backend={
            "function_name": "demo-fn",
            "entry_point_dir": lambda_dir,
            "memory_mb": 1024,
            "timeout_seconds": 60,
            "runtime": "PYTHON_3_13",
            "environment_vars": {"TABLE_NAME": "Customers"},
        }
    )
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "MemorySize": 1024,
            "Timeout": 60,
            "Runtime": "python3.13",
            "Environment": {"Variables": {"TABLE_NAME": "Customers"}},
        },
    )


def test_log_groups_are_encrypted_with_rotating_key(build: Build) -> None:
    t = build()
    t.resource_properties_count_is("AWS::Logs::LogGroup", {"KmsKeyId": Match.any_value()}, 2)
    t.has_resource_properties("AWS::KMS::Key", {"EnableKeyRotation": True})
    t.has_resource_properties(
        "AWS::KMS::Key",
        {
            "KeyPolicy": {
                "Statement": Match.array_with([Match.object_like({"Sid": "AllowCloudWatchLogs"})])
            }
        },
    )


def test_log_encryption_can_be_disabled(build: Build) -> None:
    t = build(encrypt_logs=False)
    t.resource_count_is("AWS::KMS::Key", 0)
    t.resource_properties_count_is("AWS::Logs::LogGroup", {"KmsKeyId": Match.any_value()}, 0)


def test_api_proxy_route_connected(build: Build) -> None:
    t = build()
    t.has_resource_properties("AWS::ApiGateway::Resource", {"PathPart": "{proxy+}"})
    t.has_resource_properties("AWS::Lambda::Permission", {"Principal": "apigateway.amazonaws.com"})


def test_api_throttling_active(build: Build) -> None:
    build(api_gateway={"rate_limit": 2000, "burst_limit": 800}).has_resource_properties(
        "AWS::ApiGateway::Stage",
        {
            "MethodSettings": Match.array_with(
                [Match.object_like({"ThrottlingRateLimit": 2000, "ThrottlingBurstLimit": 800})]
            )
        },
    )


def test_cors_enabled_by_default(build: Build) -> None:
    build().has_resource_properties("AWS::ApiGateway::Method", {"HttpMethod": "OPTIONS"})


def test_cors_can_be_disabled(build: Build) -> None:
    build(api_gateway={"enable_cors": False}).resource_properties_count_is(
        "AWS::ApiGateway::Method", {"HttpMethod": "OPTIONS"}, 0
    )


def test_cors_custom_origin(build: Build) -> None:
    template = build(api_gateway={"cors_allowed_origins": ["https://app.example.com"]})
    assert "https://app.example.com" in json.dumps(template.to_json())


def test_proxy_can_be_disabled(build: Build) -> None:
    t = build(api_gateway={"enable_proxy": False})
    t.resource_count_is("AWS::ApiGateway::RestApi", 0)
    t.resource_count_is("AWS::Lambda::Function", 1)
    t.resource_count_is("AWS::CloudFront::Distribution", 1)
    t.resource_count_is("AWS::Logs::LogGroup", 1)
    t.has_resource_properties(
        "AWS::CloudFront::Distribution",
        {"DistributionConfig": {"CacheBehaviors": Match.absent()}},
    )


def test_worker_only_stack(build: Build) -> None:
    t = build(s3=None, api_gateway={"enable_proxy": False})
    t.resource_count_is("AWS::Lambda::Function", 1)
    t.resource_count_is("AWS::S3::Bucket", 0)
    t.resource_count_is("AWS::CloudFront::Distribution", 0)
    t.resource_count_is("AWS::ApiGateway::RestApi", 0)


def test_api_only_stack(build: Build) -> None:
    t = build(s3=None)
    t.resource_count_is("AWS::ApiGateway::RestApi", 1)
    t.resource_count_is("AWS::S3::Bucket", 0)
    t.resource_count_is("AWS::CloudFront::Distribution", 0)
