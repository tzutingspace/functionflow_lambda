from datetime import datetime, timezone, timedelta
import json
import re
from error_handler import MyErrorHandler

# 每個lambda都可以共用


def get_now_time():
    dt0 = datetime.utcnow().replace(tzinfo=timezone.utc)
    return dt0.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")


def get_job_info_and_init(body):
    job_name = body["step_now"]
    job_info = body["steps"][job_name]
    job_info["start_time"] = get_now_time()
    return job_info


def update_job_info(job_info, results_output):
    job_info["end_time"] = get_now_time()
    job_info["result_output"] = {}
    config_outputs = parseString(job_info["config_output"])
    for output in config_outputs:
        out_put_name = output["name"]
        job_info["result_output"][out_put_name] = results_output[out_put_name]
    return job_info


def update_body(body, job_info):
    job_name = body["step_now"]
    body["steps"][job_name] = job_info
    return body


def parseString(json_string):
    json_string = json_string.replace("\u00A0", " ")  # 替換非斷空格為正確的空格
    json_string = json_string.replace("“", '"')  # 替換其他可能的特殊引號為標準雙引號
    json_string = json_string.replace("”", '"')
    return json.loads(json_string)


def replace_customize_variables(config, body):
    pattern = r"{{(.*?)}}"
    matches = re.findall(pattern, config)
    results = matches if matches else []
    # print("results", results)
    for result in results:
        _, job_name, result_name = result.split(".")
        try:
            # print(body["steps"], job_name, result_name)
            result_output = body["steps"][job_name]["result_output"]
            result_variable = result_output[result_name]
        except KeyError as e:
            MyErrorHandler().handle_error("KeyError", str(e))
            result_variable = "undefined"
        # print(result_variable)
        config = config.replace("{{" + result + "}}", str(result_variable))
    return config
