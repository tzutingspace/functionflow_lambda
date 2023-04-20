import os

import json

import requests
from Job import Job
from QueueObj import QueueObj


def send_discord_message(user_channel_ID, user_message):
    url = f"https://discord.com/api/channels/{user_channel_ID}/messages"
    headers = {"Authorization": os.environ["DISCORDBOTTOKEN"]}
    data_json = {"content": user_message}
    res = requests.post(url, json=data_json, headers=headers)
    if res.status_code != 200:
        print(f"Error: While creating a Discord message in the {user_channel_ID} channel.")
        print(f"Error Message: {res.json()}")
        return False
    else:
        print("成功送出Message")
        return True


def lambda_handler(event, context):
    # 每個function 都要做的事
    body = json.loads(event["Records"][0]["body"])
    print(f"來源內容{body}")
    queue_obj = QueueObj(None, body)
    current_job = Job(queue_obj.steps[queue_obj.step_now])
    current_job.update_start_time()  # 更新開始時間
    customer_input = current_job.parse_customer_input(queue_obj.steps)

    # lambda 獨特性
    user_channel_ID = customer_input["channel"]
    user_message = customer_input["message"]
    send_result = send_discord_message(user_channel_ID, user_message)
    if not send_result:
        job_status = "failed"
        results_output = {"success": False}
    else:
        job_status = "success"
        results_output = {"success": True}

    # 每個function 都要做的事
    current_job.update_job_status(job_status)
    current_job.update_result_output(results_output)
    current_job.update_end_time()
    queue_obj.update_job_status(current_job)
    queue_obj.put_to_sqs()
    {"lambda msg": results_output}
