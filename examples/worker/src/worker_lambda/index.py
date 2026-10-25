import json


def handler(event, context):
    # Runs for EventBridge schedules, EventBridge events and SNS messages.
    print(json.dumps(event))
    return {"processed": True}
