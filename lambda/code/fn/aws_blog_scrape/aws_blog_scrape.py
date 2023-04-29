import datetime
import json
import re

import requests
from bs4 import BeautifulSoup

from error_handler import MyErrorHandler
from Job import Job
from job_handler import parseString
from QueueObj import QueueObj


def get_aws_blog(user_input_num):
    url = "https://aws.amazon.com/tw/blogs/aws/"
    res = requests.get(url)

    if res.status_code != 200:
        print("頁面請求失敗")
        return False

    soup = BeautifulSoup(res.content, "html.parser")
    date_regex = r"on\s+(\d{1,2}\s+[A-Z]{3}\s+\d{4})"
    # user_input_num = 7
    now = datetime.datetime.now()
    now_N_ago = now - datetime.timedelta(days=user_input_num)  # 计算N天前的日期 文章日期為使用者輸入的區間

    main_content = soup.find("main", id="aws-page-content-main")
    try:
        post_list = main_content.find_all("article", class_="blog-post")
    except AttributeError as e:
        print("抓取main_content失敗導致find_all article失敗")
        MyErrorHandler.handle_error("AttributeError", f"@get_aws_blog function {e}")
        return False

    result_obj_list = []
    for post in post_list:
        try:
            footer = post.find("footer").text.strip()
        except AttributeError as e:
            print("抓取 footer 失敗導致 get text 失敗")
            MyErrorHandler.handle_error("AttributeError", f"@get_aws_blog function {e}")
            return False
        footer = re.sub(r"\n\s+", "", footer)
        match_date = re.search(date_regex, footer)
        if not match_date:
            continue
        post_date_str = match_date.group(1)
        post_date = datetime.datetime.strptime(post_date_str, "%d %b %Y")

        result_obj = {}
        if now_N_ago <= post_date <= now:
            # 日期
            # print("Date:", post_date_str)

            # Title
            # print("Title: ", post.find("h2").text)
            try:
                title = post.find("h2").get_text(strip=True)
            except AttributeError as e:
                print("抓取 title 失敗導致 get text 失敗")
                MyErrorHandler.handle_error("AttributeError", f"@get_aws_blog function {e}")
                return False

            # URL
            # print("URL: ", post.find("a").get("href"))
            try:
                url = post.find("a").get("href").strip()
            except AttributeError as e:
                print("抓取 url 失敗導致 get text 失敗")
                MyErrorHandler.handle_error("AttributeError", f"@get_aws_blog function {e}")
                return False

            # section
            # print("Section:", post.find("section").text.strip())

            try:
                section = post.find("section").get_text(strip=True)
                section = section.replace("\u00A0", " ")
                section = section.replace("\xa0", " ")
            except AttributeError as e:
                print("抓取 section 失敗導致 get text 失敗")
                MyErrorHandler.handle_error("AttributeError", f"@get_aws_blog function {e}")
                return False

            # 組成一個字串
            result_obj = {"Date": post_date_str, "Title": title, "URL": url, "Section": section}
            result_obj_list.append(result_obj)

    return result_obj_list


def lambda_handler(event, context):
    # 每個 function 都要做的事
    body = json.loads(event["Records"][0]["body"])
    print(f"來源內容{body}")
    queue_obj = QueueObj(None, body)
    current_job = Job(queue_obj.steps[queue_obj.step_now])
    current_job.update_start_time()  # 更新開始時間
    customer_input = current_job.parse_customer_input(queue_obj.steps)

    # aws_blog_scrape 獨特做的事
    user_input_num = int(customer_input["interval"])

    result_obj_list = get_aws_blog(user_input_num)

    # get data 異常
    if not result_obj_list:
        job_status = "failed"
        results_output = {}
        for output in parseString(current_job.config_output):
            results_output[output["name"]] = "Error"
            # 此 function 回覆 list

    if len(result_obj_list) == 0:
        job_status = "unfulfilled"
        results_output = {}
        for output in parseString(current_job.config_output):
            results_output[output["name"]] = "undefined"
    else:
        job_status = "success"
        results_output = {"result_list": result_obj_list}

    # 每個 function 都要做的事
    current_job.update_job_status(job_status)
    current_job.update_result_output(results_output)
    current_job.update_end_time()

    queue_obj.update_job_status(current_job)
    queue_obj.put_to_sqs()

    return {"lambda msg": results_output}
