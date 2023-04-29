import datetime
import json
import re
import time

import requests
from bs4 import BeautifulSoup


from Job import Job
from job_handler import parseString
from QueueObj import QueueObj


# 抓取所有 ptt 的 data
def get_ptt_data(url, keyword, custom_interval):
    print("預計抓取url:", url)

    cookie = {"over18": "1"}
    res = requests.get(url, cookies=cookie)
    # 請求失敗
    if res.status_code != 200:
        return False
    soup = BeautifulSoup(res.content, "html.parser")

    # 使用者設定區間
    today = datetime.datetime.now().date()
    is_over_setting_day = False
    title_list = []
    url_list = []
    day_list = []

    print("抓取當下日期", today)
    while not is_over_setting_day:
        blocks = soup.find_all("div", class_="r-ent")
        if len(blocks) == 0:
            print("找不到任何文章block..., 請確認class是否變動")
            return False
        try:
            post_month, post_day = blocks[0].find("div", class_="date").text.split("/")
            check_date = datetime.datetime(today.year, int(post_month), int(post_day)).date()
        except AttributeError:
            print("沒有抓到class_=date div text")
            return False
        except ValueError:
            print("post_month, post_day 非數字", post_month, post_day)
            return False

        # 不確認是否當月,
        if today - check_date > datetime.timedelta(days=custom_interval):
            is_over_setting_day = True

        print("post_day", check_date)
        # 找所有blocks
        for block in blocks:
            if block.find("a") != None:
                try:
                    post_month, post_day = block.find("div", class_="date").text.split("/")
                    check_date = datetime.datetime(
                        today.year, int(post_month), int(post_day)
                    ).date()
                except AttributeError:
                    print("沒有抓到class_=date div text")
                    return False
                except ValueError:
                    print("post_month, post_day 非數字", post_month, post_day)
                    return False
                if today - check_date <= datetime.timedelta(days=custom_interval):
                    try:
                        title_list.append(block.find("a").text)
                        url_list.append(block.find("a").get("href"))
                        day_list.append(block.find("div", class_="date").text)
                    except AttributeError:
                        print("抓取單篇 title, url, day 出現錯誤")
                        return False
        # 確認上一頁
        try:
            page = soup.find(id="action-bar-container")
            url_get = page.find("a", class_="btn wide", string=re.compile("上頁$")).get("href")
            url_prev = "https://www.ptt.cc" + str(url_get)
            print("上一頁url", url_prev)
        except AttributeError:
            print("取得上一頁的資料出現錯誤, 沒取到資料, AttributeError")
            return False

        res = requests.get(url_prev, cookies=cookie)
        if res.status_code != 200:
            print("請求上一頁, 非200回應")
            return False
        soup = BeautifulSoup(res.content, "html.parser")
        time.sleep(1)

    result_obj_list = []
    regex = re.compile(keyword)
    for index, title in enumerate(title_list):
        if re.search(regex, title) != None:
            try:
                result = {"title": title, "url": "https://www.ptt.cc" + url_list[index]}
                result_obj_list.append(result)
            except TypeError:
                print("抓取資料有空值, 無法組合")
                return False

    return result_obj_list


def lambda_handler(event, context):
    # 每個 function 都要做的事
    body = json.loads(event["Records"][0]["body"])
    print(f"來源內容{body}")
    queue_obj = QueueObj(None, body)
    current_job = Job(queue_obj.steps[queue_obj.step_now])
    current_job.update_start_time()  # 更新開始時間
    customer_input = current_job.parse_customer_input(queue_obj.steps)

    # ptt_scrape 獨特做的事
    user_target_board = customer_input["target_board"]
    keyword = customer_input["keyword"]
    custom_interval = int(customer_input["interval"])
    url = f"https://www.ptt.cc/bbs/{user_target_board}/index.html"

    result_obj_list = get_ptt_data(url, keyword, custom_interval)

    # get data 異常
    if not result_obj_list:
        job_status = "failed"
        results_output = {}
        for output in parseString(current_job.config_output):
            results_output[output["name"]] = "Error"
            # 此 function 回覆 list
        # FIXME: 需要回覆相同格式嗎？
        results_output = [results_output]

    if len(result_obj_list) == 0:
        job_status = "unfulfilled"
        results_output = {}
        for output in parseString(current_job.config_output):
            results_output[output["name"]] = "undefined"
        # FIXME: 需要回覆相同格式嗎？
        results_output = [results_output]
    else:
        job_status = "success"
        results_output = result_obj_list

    # 每個 function 都要做的事
    current_job.update_job_status(job_status)
    current_job.update_result_output(results_output)
    current_job.update_end_time()

    queue_obj.update_job_status(current_job)
    queue_obj.put_to_sqs()

    return {"lambda msg": results_output}
