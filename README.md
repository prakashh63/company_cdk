# company_cdk

Reusable internal Python package that turns a short YAML (or Python) config into a secure
AWS stack built with the AWS CDK. One package covers three shapes:

| Shape | Config | Creates |
| --- | --- | --- |
| Web app | `s3` + default `api_gateway` | S3 + CloudFront (OAC) + API Gateway + Lambda |
| API only | no `s3` | API Gateway + Lambda |
| Worker | `api_gateway.enable_proxy: false` (+ `triggers`) | Lambda triggered by EventBridge / SNS |

## What every stack gets by default

| Area | Behaviour |
| --- | --- |
| S3 | All public access blocked, S3-managed encryption, SSL enforced, versioning in prod |
| CloudFront | Origin Access Control to S3, `/api/*` routed to API Gateway, HTTPS redirect |
| API Gateway | Lambda proxy integration, CORS, throttling, access logs, request validator |
| Lambda | Least-privilege role (writes only to its own log group), latest Python runtime by default |
| Logs | Retention 7 days (dev), 30 days (staging), 90 days (prod); encrypted with a customer-managed KMS key with rotation |
| SNS | Encrypted (AWS-managed key), SSL-only publishing |
| Tags | `Environment`, `Owner`, `ManagedBy=company_cdk`, optional `CostCenter` on every taggable resource |
| Compliance | cdk-nag `AwsSolutionsChecks`; a violation makes `cdk synth` fail (exit code 1) |

## Install

Requirements: Python 3.12+, Node.js and the CDK CLI (`npm install -g aws-cdk`).

```bash
# from a git repository
pip install "git+https://github.com/your-username/company_cdk.git@v0.2.0"

# or from a built wheel
pip install company_cdk-0.2.0-py3-none-any.whl
```

## Quick start (web app)

`config.yaml`:

```yaml
app_name: customer-portal
environment: dev            # dev | staging | prod
owner_team: frontend-devs
cost_center: CC-1024        # optional
s3:
  bucket_name: cust-portal-web-assets-dev
lambda_backend:
  function_name: portal-api-handler
  entry_point_dir: src/backend_lambda   # relative to config.yaml
  memory_mb: 1024
api_gateway:
  stage_name: v1
  rate_limit: 2000
```

`app.py` and `cdk.json` (`{ "app": "python app.py" }`):

```python
from pathlib import Path

import aws_cdk as cdk

from company_cdk import ServerlessWebAppStack
from company_cdk.configs import load_config

app = cdk.App()
config = load_config(Path(__file__).parent / "config.yaml")
ServerlessWebAppStack(app, "CustomerPortalStack", config=config)
app.synth()
```

```bash
cdk synth      # builds the template and runs cdk-nag
cdk deploy     # optional, needs an AWS account
```

## Worker Lambda (no API Gateway)

```yaml
app_name: order-worker
environment: dev
owner_team: backend-devs
lambda_backend:
  function_name: order-worker
  entry_point_dir: src/worker_lambda
api_gateway:
  enable_proxy: false
triggers:
  schedule:
    expression: rate(1 hour)          # or cron(0 12 * * ? *)
  event_rule:
    source: [orders.service]
    detail_type: [Order Created]      # optional
    event_bus_name: my-bus            # optional, default bus when omitted
  sns:
    topic_name: order-worker-topic
```

Any trigger can be left out. Using only the Lambda in your own stack:

```python
from company_cdk.constructs import SecureLambda
```

## Configuration reference

| Field | Default | Rule |
| --- | --- | --- |
| `app_name`, `owner_team` | required | non-empty |
| `environment` | required | `dev`, `staging` or `prod` |
| `cost_center` | none | adds the `CostCenter` tag |
| `encrypt_logs` | `true` | KMS key for log groups (a KMS key has a small monthly cost); set `false` to skip |
| `s3.bucket_name` | required with `s3` | 3 to 63 chars, lowercase, digits, `.` and `-` |
| `s3.auto_delete_objects` | `false` | ignored in prod |
| `lambda_backend.function_name`, `entry_point_dir` | required | folder must exist |
| `lambda_backend.handler` | `index.handler` | |
| `lambda_backend.runtime` | `PYTHON_3_14` | `PYTHON_3_10` to `PYTHON_3_14` |
| `lambda_backend.memory_mb` | 512 | 128 to 3072 |
| `lambda_backend.timeout_seconds` | 30 | 1 to 900 |
| `lambda_backend.environment_vars` | `{}` | |
| `api_gateway.enable_proxy` | `true` | `false` creates no API Gateway |
| `api_gateway.stage_name` | `prod` | letters, digits, `_`, `-` |
| `api_gateway.enable_cors` | `true` | |
| `api_gateway.cors_allowed_origins` | `["*"]` | restrict this in production |
| `api_gateway.rate_limit` / `burst_limit` | 1000 / 500 | greater than 0 |
| `triggers.schedule.expression` | none | `rate(...)` or `cron(...)` |
| `triggers.event_rule.source` | none | at least one source |
| `triggers.sns.topic_name` | none | letters, digits, `_`, `-` |

Unknown fields and invalid values fail when the config is loaded, before any AWS resource exists.

## cdk-nag findings

Findings fixed in code: runtime (L1), request validator (APIG2), stage logging (APIG6),
log encryption, SNS encryption and SSL.

Findings acknowledged with a written reason (see the constructs):

| Rule | Reason |
| --- | --- |
| S1, CFR3 | Access logging needs a dedicated log bucket (tracked improvement) |
| APIG4, COG4 | No authorizer in the current spec; add one per application |
| APIG3, CFR2 | WAF is a paid add-on; enable per application |
| CFR1 | Geo restriction is a per-application business decision |
| CFR4 | Default CloudFront certificate; a TLS floor needs a custom domain |
| IAM4 | AWS-managed service role API Gateway uses to push logs |

To acknowledge another rule inside a construct:

```python
Validations.of(self.bucket).acknowledge(
    Acknowledgment(id="AwsSolutions::AwsSolutions-XXX", reason="Why this is acceptable")
)
```

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python scripts/verify.py      # ruff, mypy, pytest, cdk synth for both examples
```

Individual commands:

```bash
pytest -q
pytest tests/snapshots --snapshot-update    # after an intended template change
mypy company_cdk tests
ruff check . && ruff format --check .
```

See what the package does, step by step: `python examples/show_output.py`
(or `python examples/show_output.py examples/worker/config.yaml`).

## Build a package for others

```bash
python -m build            # dist/company_cdk-0.2.0-py3-none-any.whl
git tag v0.2.0 && git push origin v0.2.0    # the Release workflow attaches the wheel
```

## Extending

- New config field: add it to `company_cdk/configs/models.py`, then use it in a construct.
- New construct: add a class in `company_cdk/constructs/`, export it in `__init__.py`, wire it into `ServerlessWebAppStack`.
- New standard tag: add it to the `tags` dict in `ServerlessWebAppStack`.
- Another rule pack: register it next to `AwsSolutionsChecks` in `aspects/compliance.py`.

## Layout

```
company_cdk/
  configs/      Pydantic schemas and YAML loader
  constructs/   SecureBucket, LogKey, SecureLambda, ApiGatewayProxy, ServerlessBackend,
                LambdaTriggers, WebDistribution
  aspects/      TaggingAspect, cdk-nag registration
  stacks/       ServerlessWebAppStack
tests/          unit tests and snapshot tests
examples/       web app example, worker example, walkthrough script
scripts/        verify.py (all quality gates in one command)
```

## Known limitations

- No API authorizer or WAF by default.
- S3 and CloudFront access logging are not enabled yet.
- CORS defaults to all origins; set `cors_allowed_origins` for production.
- The API Gateway request validator cannot validate bodies of proxy routes.
- SNS uses the AWS-managed key, so AWS services that publish to the topic (for example S3 event
  notifications) need a customer-managed key instead.
- Staging log retention (30 days) is an assumption; the original spec defines only dev and prod.
- SQS triggers are not included yet.
