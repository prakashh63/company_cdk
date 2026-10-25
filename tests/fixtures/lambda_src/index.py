from typing import Any


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    return {"statusCode": 200, "body": "ok"}
