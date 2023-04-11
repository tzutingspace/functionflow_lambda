import json
import os

import requests
from job_handler import (
    get_job_info_and_init,
    parseString,
    replace_customize_variables,
    update_body,
    update_job_info,
)
from put_to_sqs import put_to_sqs


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


def lambda_handler(event, content):
    print(f"event{event}")
    body = json.loads(event["Records"][0]["body"])
    job_info = get_job_info_and_init(body)
    job_config_input = parseString(job_info["config_input"])

    # lambda 獨特
    user_channel_ID = job_config_input["channel"]
    user_message = job_config_input["message"]
    send_message = replace_customize_variables(user_message, body)
    send_result = send_discord_message(user_channel_ID, send_message)
    if not send_result:
        job_info["status"] = "Failed"
        results_output = {"success": False}
    else:
        job_info["status"] = "success"
        results_output = {"success": True}

    job_info = update_job_info(job_info, results_output)
    body = update_body(body, job_info)
    put_to_sqs(body, "jobsQueue")
    return {"msg": "Finish"}
