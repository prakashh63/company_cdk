from collections.abc import Callable

from aws_cdk.assertions import Match, Template

Build = Callable[..., Template]

WORKER = {"s3": None, "api_gateway": {"enable_proxy": False}}


def test_no_triggers_by_default(build: Build) -> None:
    t = build()
    t.resource_count_is("AWS::Events::Rule", 0)
    t.resource_count_is("AWS::SNS::Topic", 0)


def test_schedule_trigger(build: Build) -> None:
    t = build(**WORKER, triggers={"schedule": {"expression": "rate(1 hour)"}})
    t.has_resource_properties(
        "AWS::Events::Rule",
        {
            "ScheduleExpression": "rate(1 hour)",
            "Targets": Match.array_with([Match.object_like({"Arn": Match.any_value()})]),
        },
    )
    t.has_resource_properties("AWS::Lambda::Permission", {"Principal": "events.amazonaws.com"})


def test_event_pattern_trigger(build: Build) -> None:
    t = build(
        **WORKER,
        triggers={"event_rule": {"source": ["orders.service"], "detail_type": ["Order Created"]}},
    )
    t.has_resource_properties(
        "AWS::Events::Rule",
        {"EventPattern": {"source": ["orders.service"], "detail-type": ["Order Created"]}},
    )


def test_sns_trigger_is_encrypted_and_ssl_only(build: Build) -> None:
    t = build(**WORKER, triggers={"sns": {"topic_name": "orders-topic"}})
    t.resource_count_is("AWS::SNS::Topic", 1)
    t.has_resource_properties(
        "AWS::SNS::Topic",
        {"TopicName": "orders-topic", "KmsMasterKeyId": Match.any_value()},
    )
    t.has_resource_properties("AWS::SNS::Subscription", {"Protocol": "lambda"})
    t.has_resource_properties("AWS::Lambda::Permission", {"Principal": "sns.amazonaws.com"})
    t.resource_count_is("AWS::SNS::TopicPolicy", 1)


def test_all_triggers_together(build: Build) -> None:
    t = build(
        **WORKER,
        triggers={
            "schedule": {"expression": "rate(5 minutes)"},
            "event_rule": {"source": ["a.b"]},
            "sns": {"topic_name": "t1"},
        },
    )
    t.resource_count_is("AWS::Events::Rule", 2)
    t.resource_count_is("AWS::SNS::Topic", 1)
    t.resource_count_is("AWS::Lambda::Function", 1)
