"""LambdaTriggers: optional EventBridge and SNS event sources for a Lambda function."""

from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_kms as kms
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subs
from constructs import Construct

from ..configs import TriggerConfig


class LambdaTriggers(Construct):
    """Creates only the triggers present in the config; an empty config creates nothing."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        function: _lambda.IFunction,
        config: TriggerConfig,
    ) -> None:
        super().__init__(scope, construct_id)

        self.schedule_rule: events.Rule | None = None
        self.event_rule: events.Rule | None = None
        self.topic: sns.Topic | None = None

        if config.schedule is not None:
            self.schedule_rule = events.Rule(
                self,
                "ScheduleRule",
                description="Scheduled trigger created by company_cdk",
                schedule=events.Schedule.expression(config.schedule.expression),
            )
            self.schedule_rule.add_target(targets.LambdaFunction(function, retry_attempts=2))

        if config.event_rule is not None:
            rule_config = config.event_rule
            bus = (
                events.EventBus.from_event_bus_name(self, "Bus", rule_config.event_bus_name)
                if rule_config.event_bus_name
                else None
            )
            self.event_rule = events.Rule(
                self,
                "EventRule",
                description="Event pattern trigger created by company_cdk",
                event_bus=bus,
                event_pattern=events.EventPattern(
                    source=rule_config.source,
                    detail_type=rule_config.detail_type or None,
                ),
            )
            self.event_rule.add_target(targets.LambdaFunction(function, retry_attempts=2))

        if config.sns is not None:
            # AWS-managed SNS key: encrypted at rest without paying for a custom key.
            sns_key: kms.IKey = kms.Alias.from_alias_name(self, "SnsKey", "alias/aws/sns")
            self.topic = sns.Topic(
                self,
                "Topic",
                topic_name=config.sns.topic_name,
                enforce_ssl=True,
                master_key=sns_key,
            )
            self.topic.add_subscription(subs.LambdaSubscription(function))
