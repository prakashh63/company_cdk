from collections.abc import Callable

from aws_cdk.assertions import Match, Template

Build = Callable[..., Template]

TAGGED_TYPES = [
    "AWS::S3::Bucket",
    "AWS::Lambda::Function",
    "AWS::Logs::LogGroup",
    "AWS::CloudFront::Distribution",
    "AWS::ApiGateway::RestApi",
    "AWS::KMS::Key",
]


def tag(key: str, value: str) -> object:
    return Match.array_with([{"Key": key, "Value": value}])


def test_standard_tags_on_main_resources(build: Build) -> None:
    t = build(environment="prod", owner_team="team-a")
    expected = {"Environment": "prod", "Owner": "team-a", "ManagedBy": "company_cdk"}
    for resource_type in TAGGED_TYPES:
        for key, value in expected.items():
            t.has_resource_properties(resource_type, {"Tags": tag(key, value)})


def test_cost_center_tag_when_given(build: Build) -> None:
    build(cost_center="CC-1024").has_resource_properties(
        "AWS::S3::Bucket", {"Tags": tag("CostCenter", "CC-1024")}
    )


def test_cost_center_tag_absent_when_not_given(build: Build) -> None:
    t = build()
    resources = t.find_resources("AWS::S3::Bucket")
    for resource in resources.values():
        keys = [item["Key"] for item in resource["Properties"]["Tags"]]
        assert "CostCenter" not in keys
