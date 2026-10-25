import aws_cdk as cdk
from aws_cdk.assertions import Match, Template

from company_cdk.constructs import SecureBucket


def build(environment: str) -> Template:
    stack = cdk.Stack()
    SecureBucket(stack, "Web", bucket_name="demo-bucket-123", environment=environment)
    return Template.from_stack(stack)


def test_public_access_fully_blocked() -> None:
    build("dev").has_resource_properties(
        "AWS::S3::Bucket",
        {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            }
        },
    )


def test_encryption_enabled() -> None:
    build("dev").has_resource_properties(
        "AWS::S3::Bucket",
        {
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": [
                    {"ServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
                ]
            }
        },
    )


def test_versioning_only_in_prod() -> None:
    build("prod").has_resource_properties(
        "AWS::S3::Bucket", {"VersioningConfiguration": {"Status": "Enabled"}}
    )
    build("dev").has_resource_properties(
        "AWS::S3::Bucket", {"VersioningConfiguration": Match.absent()}
    )


def test_ssl_enforced() -> None:
    build("dev").resource_count_is("AWS::S3::BucketPolicy", 1)
