from datetime import datetime, timezone, timedelta
import json

# 每個lambda都可以共用


def get_now_time():
    dt0 = datetime.utcnow().replace(tzinfo=timezone.utc)
    return dt0.astimezone(
        timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')


def get_job_info_and_init(body):
    job_name = body["step_now"]
    job_info = body["steps"][job_name]
    job_info["start_time"] = get_now_time()
    return job_info


def update_job_info(job_info, results_output):
    job_info["end_time"] = get_now_time()
    job_info["result_output"] = {}
    config_outputs = json.loads(job_info["config_output"])
    for output in config_outputs:
        out_put_name = output["name"]
        job_info["result_output"][out_put_name] = results_output[out_put_name]
    return job_info


def update_body(body, job_info):
    job_name = body["step_now"]
    body["steps"][job_name] = job_info
    return body
