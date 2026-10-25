"""Pydantic schemas: validate user input before any AWS resource is created."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_RUNTIMES = (
    "PYTHON_3_10",
    "PYTHON_3_11",
    "PYTHON_3_12",
    "PYTHON_3_13",
    "PYTHON_3_14",
)
DEFAULT_RUNTIME = "PYTHON_3_14"

_SCHEDULE_RE = re.compile(r"^(rate|cron)\(.+\)$")


class _Strict(BaseModel):
    """Base class: unknown fields are rejected, so a typo never passes silently."""

    model_config = ConfigDict(extra="forbid")


class S3Config(_Strict):
    """Private static-site bucket (served through CloudFront)."""

    bucket_name: str = Field(min_length=3, max_length=63, pattern=r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$")
    auto_delete_objects: bool = False


class LambdaConfig(_Strict):
    """The Lambda function. Works for web backends and for worker functions."""

    function_name: str
    entry_point_dir: str  # relative paths are resolved from the config file's folder
    handler: str = "index.handler"
    runtime: str = DEFAULT_RUNTIME
    memory_mb: int = Field(default=512, ge=128, le=3072)
    timeout_seconds: int = Field(default=30, ge=1, le=900)
    environment_vars: dict[str, str] = Field(default_factory=dict)

    @field_validator("runtime")
    @classmethod
    def check_runtime(cls, value: str) -> str:
        if value not in ALLOWED_RUNTIMES:
            raise ValueError(f"runtime must be one of {list(ALLOWED_RUNTIMES)}")
        return value


class ApiGatewayConfig(_Strict):
    """API Gateway in front of the Lambda. Set enable_proxy=false for worker Lambdas."""

    enable_proxy: bool = True
    stage_name: str = Field(default="prod", pattern=r"^[A-Za-z0-9_-]+$")
    enable_cors: bool = True
    cors_allowed_origins: list[str] = Field(default_factory=lambda: ["*"])
    rate_limit: int = Field(default=1000, gt=0)
    burst_limit: int = Field(default=500, gt=0)


class ScheduleTriggerConfig(_Strict):
    """EventBridge schedule, e.g. 'rate(5 minutes)' or 'cron(0 12 * * ? *)'."""

    expression: str

    @field_validator("expression")
    @classmethod
    def check_expression(cls, value: str) -> str:
        if not _SCHEDULE_RE.match(value):
            raise ValueError("expression must look like 'rate(5 minutes)' or 'cron(0 12 * * ? *)'")
        return value


class EventRuleTriggerConfig(_Strict):
    """EventBridge rule that matches events by source (and optionally detail-type)."""

    source: list[str] = Field(min_length=1)
    detail_type: list[str] = Field(default_factory=list)
    event_bus_name: str | None = None  # None means the account's default event bus


class SnsTriggerConfig(_Strict):
    """SNS topic (encrypted, SSL only) that invokes the Lambda for each message."""

    topic_name: str = Field(min_length=1, max_length=256, pattern=r"^[A-Za-z0-9_-]+$")


class TriggerConfig(_Strict):
    """Optional event sources for the Lambda. Leave everything empty for none."""

    schedule: ScheduleTriggerConfig | None = None
    event_rule: EventRuleTriggerConfig | None = None
    sns: SnsTriggerConfig | None = None


class WebAppConfig(_Strict):
    """Top-level configuration for ServerlessWebAppStack."""

    app_name: str = Field(min_length=1)
    environment: Literal["dev", "staging", "prod"]
    owner_team: str = Field(min_length=1)
    cost_center: str | None = None
    encrypt_logs: bool = True
    s3: S3Config | None = None
    lambda_backend: LambdaConfig  # `lambda` is a Python keyword, so lambda_backend
    api_gateway: ApiGatewayConfig = Field(default_factory=ApiGatewayConfig)
    triggers: TriggerConfig = Field(default_factory=TriggerConfig)
