import json
from datetime import datetime, timedelta, timezone


# Function
def get_now_time():
    dt0 = datetime.utcnow().replace(tzinfo=timezone.utc)
    return dt0.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")


def parseString(json_string):
    json_string = json_string.replace("\u00A0", " ")  # 替換非斷空格為正確的空格
    json_string = json_string.replace("“", '"')  # 替換其他可能的特殊引號為標準雙引號
    json_string = json_string.replace("”", '"')
    return json.loads(json_string)
