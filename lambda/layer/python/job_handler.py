import json
import re
from datetime import datetime, timedelta, timezone

from error_handler import MyErrorHandler


# Function
def get_now_time():
    dt0 = datetime.utcnow().replace(tzinfo=timezone.utc)
    return dt0.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")


def parseString(json_string):
    json_string = json_string.replace("\u00A0", " ")  # 替換非斷空格為正確的空格
    json_string = json_string.replace("“", '"')  # 替換其他可能的特殊引號為標準雙引號
    json_string = json_string.replace("”", '"')
    return json.loads(json_string)


# 屬於一個queue的 ??
# FIXME:????? 要寫在哪裡
# 如果有客製化的時候要解析？ custom input??
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
