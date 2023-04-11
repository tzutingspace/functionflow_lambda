import os
import json
import boto3
from botocore.exceptions import ClientError


def put_to_sqs(job, queuename):
    print(f"預計加入sqs的內容: {json.dumps(job)}")

    if os.environ["ENV"] == "TEST":
        response = "SAM LOCAL TESTing"
        return response

    client = boto3.client("sqs", region_name=os.environ["AWS_REGION_NAME"])
    try:
        response = client.send_message(
            QueueUrl=f'{os.environ["AWS_QUEUE_URL"]}/{queuename}', MessageBody=json.dumps(job)
        )
        print("put_to_sqs Response: ", response)
    except ClientError:
        response = ClientError
    finally:
        return response
