import json
import os

import requests
from Job import Job
from job_handler import parseString
from QueueObj import QueueObj


def get_weather(city, elementName):
    url = "https://opendata.cwb.gov.tw/api/v1/rest/datastore/F-C0032-001"
    headers = {"user-agent": "Mozilla/5.0"}
    params = {
        "Authorization": os.getenv("OPEN_API_KEY"),
        "format": "JSON",
        "locationName": city,
        "sort": "time",
        "limit": 1,
        "offset": 0,
        "elementName": elementName,
    }
    res = requests.get(url, params=params, headers=headers)

    if res.status_code != 200 or res.headers["Content-Type"] != "application/json;charset=utf-8":
        print("取得天氣資料發生錯誤", res.status_code)
        return False
    data = res.json()
    if len(data["records"]["location"]) == 0:
        print("此筆天氣資料為空", data["records"])
        return False
    weather_element_value = data["records"]["location"][0]["weatherElement"][0]
    return weather_element_value


def parse_weather_temp(weather_status):
    return {"temperature": int(weather_status["time"][0]["parameter"]["parameterName"])}


def lambda_handler(event, context):
    print("START EVENT", event)
    # 每個function 都要做的事
    body = json.loads(event["Records"][0]["body"])
    print(f"來源內容{body}")
    queue_obj = QueueObj(None, body)
    current_job = Job(queue_obj.steps[queue_obj.step_now])
    current_job.update_start_time()  # 更新開始時間
    customer_input = current_job.parse_customer_input(queue_obj.steps)

    # get_weather 獨特做的事
    city = customer_input["city"]
    condition = customer_input["condition"]
    # temperature = customer_input["temperature"]
    weather_status = get_weather(city, condition)
    if not weather_status:
        job_status = "failed"
        results_output = {}
        for output in parseString(current_job.config_output):
            results_output[output["name"]] = "Error"
    else:
        job_status = "success"
        results_output = parse_weather_temp(weather_status)

    # 每個function 都要做的事
    current_job.update_job_status(job_status)
    current_job.update_result_output(results_output)
    current_job.update_end_time()

    queue_obj.update_job_status(current_job)
    queue_obj.put_to_sqs()

    return {"lambda msg": results_output}
