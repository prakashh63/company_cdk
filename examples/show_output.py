"""Walkthrough: what the developer gives, what the package does, what comes out.

Usage:  python show_output.py [path/to/config.yaml]
Try:    python show_output.py worker/config.yaml
"""

import sys
from collections import Counter
from pathlib import Path
from typing import Any

import aws_cdk as cdk
from aws_cdk.assertions import Template

from company_cdk import ServerlessWebAppStack
from company_cdk.configs import load_config

HERE = Path(__file__).parent
CONFIG_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "config.yaml"


def title(text: str) -> None:
    print(f"\n{'=' * 72}\n{text}\n{'=' * 72}")


def check(label: str, ok: bool) -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}")


def props(template: dict[str, Any], resource_type: str) -> list[dict[str, Any]]:
    return [
        resource.get("Properties", {})
        for resource in template["Resources"].values()
        if resource["Type"] == resource_type
    ]


# STEP 1: what the developer writes
title(f"STEP 1: INPUT (what the developer writes in {CONFIG_PATH.name})")
print(CONFIG_PATH.read_text(encoding="utf-8"))

# STEP 2: validation
title("STEP 2: VALIDATION (Pydantic checks it and fills in defaults)")
config = load_config(CONFIG_PATH)
print(config.model_dump_json(indent=2))
print("\nEvery field the developer did NOT write was filled in from safe defaults.")

# STEP 3: build the stack
title("STEP 3: BUILD (ServerlessWebAppStack creates everything)")
stack = ServerlessWebAppStack(cdk.App(), "DemoStack", config=config, enable_compliance=False)
template: dict[str, Any] = Template.from_stack(stack).to_json()
counts = Counter(r["Type"] for r in template["Resources"].values())
print(
    f"The developer wrote a short config. The package created {sum(counts.values())} resources:\n"
)
for resource_type, count in sorted(counts.items()):
    print(f"  {count} x {resource_type}")

# STEP 4: environment rules
buckets = props(template, "AWS::S3::Bucket")
log_groups = props(template, "AWS::Logs::LogGroup")
title(f"STEP 4: ENVIRONMENT RULES (environment = {config.environment})")
print(f"  Log retention (days) : {[p.get('RetentionInDays') for p in log_groups]}")
print("                         (dev 7, staging 30, prod 90)")
if buckets:
    versioned = "VersioningConfiguration" in buckets[0]
    print(f"  Bucket versioning    : {'ON' if versioned else 'OFF'}   (prod only)")
kept = sorted(
    {
        r.get("DeletionPolicy", "Delete")
        for r in template["Resources"].values()
        if r["Type"] in ("AWS::S3::Bucket", "AWS::Logs::LogGroup", "AWS::KMS::Key")
    }
)
print(f"  Deletion policy      : {kept}   (prod Retain, others Delete)")

# STEP 5: security checks read from the generated template
title("STEP 5: SECURITY CHECKS (read from the generated CloudFormation)")
if buckets:
    pab = buckets[0].get("PublicAccessBlockConfiguration", {})
    check("S3 blocks ALL public access", len(pab) == 4 and all(pab.values()))
    check("S3 encryption enabled", "BucketEncryption" in buckets[0])
    check(
        "CloudFront uses Origin Access Control (OAC)",
        "AWS::CloudFront::OriginAccessControl" in counts,
    )

distributions = props(template, "AWS::CloudFront::Distribution")
api_behaviors: list[dict[str, Any]] = []
if distributions:
    dist = distributions[0]["DistributionConfig"]
    default_policy = dist["DefaultCacheBehavior"]["ViewerProtocolPolicy"]
    check("Default route redirects HTTP to HTTPS", default_policy == "redirect-to-https")
    api_behaviors = dist.get("CacheBehaviors", [])
    for behavior in api_behaviors:
        check(
            f"{behavior['PathPattern']} routed to API Gateway with HTTPS redirect",
            behavior["ViewerProtocolPolicy"] == "redirect-to-https",
        )

stages = props(template, "AWS::ApiGateway::Stage")
if stages:
    throttle = stages[0]["MethodSettings"][0]
    check(
        f"API throttling active (rate {throttle['ThrottlingRateLimit']}, "
        f"burst {throttle['ThrottlingBurstLimit']})",
        "ThrottlingRateLimit" in throttle,
    )
    check("API access logs enabled", "AccessLogSetting" in stages[0])
else:
    print("  [INFO] No API Gateway in this config (worker mode)")

if config.encrypt_logs:
    check("All log groups encrypted with a KMS key", all("KmsKeyId" in p for p in log_groups))
    keys = props(template, "AWS::KMS::Key")
    check("KMS key rotation enabled", bool(keys) and all(k.get("EnableKeyRotation") for k in keys))

actions = [
    action
    for policy in props(template, "AWS::IAM::Policy")
    for statement in policy["PolicyDocument"]["Statement"]
    for action in (
        statement["Action"] if isinstance(statement["Action"], list) else [statement["Action"]]
    )
]
check(f"Lambda role has no wildcard action {sorted(set(actions))}", "*" not in actions)

functions = props(template, "AWS::Lambda::Function")
tags = {t["Key"]: t["Value"] for t in functions[0].get("Tags", [])}
check(f"Auto tags on resources {tags}", {"Environment", "Owner", "ManagedBy"} <= set(tags))

rules = props(template, "AWS::Events::Rule")
topics = props(template, "AWS::SNS::Topic")
if rules or topics:
    print()
    for rule in rules:
        what = rule.get("ScheduleExpression") or rule.get("EventPattern")
        print(f"  [TRIGGER] EventBridge rule: {what}")
    for topic in topics:
        encrypted = "KmsMasterKeyId" in topic
        print(f"  [TRIGGER] SNS topic {topic.get('TopicName')} (encrypted: {encrypted})")

# STEP 6: request flow
title("STEP 6: HOW EVENTS FLOW AFTER DEPLOY")
if buckets:
    print("  Browser -> CloudFront (HTTPS only)")
    print("     /*       -> private S3 bucket (only CloudFront can read, via OAC)")
    for behavior in api_behaviors:
        print(f"     {behavior['PathPattern']}  -> API Gateway -> Lambda")
if rules:
    print("  EventBridge (schedule / events) -> Lambda")
if topics:
    print("  SNS topic -> Lambda")
print("\nDone. Nothing was deployed; this is the plan CloudFormation would execute.")
