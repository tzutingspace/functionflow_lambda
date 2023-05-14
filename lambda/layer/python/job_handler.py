import json
from datetime import datetime, timezone


# Function
def get_now_time():
    dt0 = datetime.utcnow().replace(tzinfo=timezone.utc)
    return dt0.strftime("%Y-%m-%d %H:%M:%S")


def parseString(json_string):
    print("將 string 轉成 物件")
    print("parseString 來源:", json_string)
    print("parseString 來源 type : ", type(json_string))
    json_string = json_string.replace("\u00A0", " ")  # 替換非斷空格為正確的空格
    json_string = json_string.replace("\xa0", " ")  # 替換非斷空格為正確的空格
    json_string = json_string.replace("“", '"')  # 替換其他可能的特殊引號為標準雙引號
    json_string = json_string.replace("”", '"')

    print("parseString 結果...", json_string)
    return json.loads(json_string)
