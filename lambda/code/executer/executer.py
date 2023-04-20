import json
from QueueObj import QueueObj


# 主要邏輯
def lambda_handler(event, context):
    print("START EVENT", event)
    body = json.loads(event["Records"][0]["body"])
    print(f"來源內容{body}")
    queue_obj = QueueObj(None, body)
    result = queue_obj.do_next_action()

    return result
