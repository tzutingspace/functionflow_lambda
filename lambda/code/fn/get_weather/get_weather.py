import json
import os

import requests
from job_handler import (get_job_info_and_init, update_body, update_job_info)
from put_to_sqs import put_to_sqs


def get_weather(city, elementName):
    url = 'https://opendata.cwb.gov.tw/api/v1/rest/datastore/F-C0032-001'
    headers = {'user-agent': 'Mozilla/5.0'}
    params = {
        'Authorization': os.getenv("OPENAPIKEY"),
        'format': 'JSON',
        'locationName': city,
        'sort': 'time',
        'limit': 1,
        'offset': 0,
        'elementName': elementName
    }
    response = requests.get(url, params=params, headers=headers)
    if response.status_code != 200 or response.headers['Content-Type'] != 'application/json;charset=utf-8':
        print('取得天氣資料發生錯誤', response.status_code)
        return False
    data = response.json()
    if len(data['records']['location']) == 0:
        print('此筆天氣資料為空', data['records'])
        return False
    weather_element_value = data["records"]["location"][0]["weatherElement"][0]
    return weather_element_value


def parse_weather_temp(weatherstatus):
    return {"temperature": int(weatherstatus["time"][0]["parameter"]["parameterName"])}


def check_condition_temp(forecasttemp, job_config_input):
    condition, setting_temp = job_config_input["condition"], int(
        job_config_input["temperature"])
    if (condition == 'MinT' and forecasttemp <= setting_temp) or (condition == 'MaxT' and forecasttemp >= setting_temp):
        print(
            f"通知用戶, 條件: {condition}, 目前溫度: {forecasttemp}, 提醒溫度: {setting_temp}")
        return True
    else:
        print(
            f"不符合條件, 條件: {condition}, 目前溫度: {forecasttemp}, 提醒溫度: {setting_temp}")
        return False


def lambda_handler(event, context):
    body = json.loads(event["Records"][0]["body"])
    job_info = get_job_info_and_init(body)
    job_config_input = json.loads(job_info["config_input"])

    # lambda 獨特性
    city = job_config_input["city"]
    elementName = job_config_input["condition"]
    weatherstatus = get_weather(city, elementName)
    if not weatherstatus:
        job_info['status'] = 'Failed'
        results_output = {"temperature": "Error"}
    else:
        results_output = parse_weather_temp(weatherstatus)
        threshold_result = check_condition_temp(
            results_output["temperature"], job_config_input)
        job_info["status"] = "success" if threshold_result else "unfulfilled"

    job_info = update_job_info(job_info, results_output)
    body = update_body(body, job_info)
    put_to_sqs(body, 'jobsQueue')
    return {"msg": "Finish"}
