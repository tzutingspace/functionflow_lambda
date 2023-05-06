import os

import json

from Job import Job
from QueueObj import QueueObj


from mailersend import emails


def send_email(username, useremail, subject, content):
    mailer = emails.NewEmail(os.getenv("MAILERSEND_API_KEY"))
    # define an empty dict to populate with mail values
    mail_body = {}
    mail_from = {
        "name": "functionflow",
        "email": "functionflow@tingproject.link",
    }

    recipients = [
        {
            "name": username,
            "email": useremail,
        }
    ]

    mailer.set_mail_from(mail_from, mail_body)
    mailer.set_mail_to(recipients, mail_body)
    mailer.set_subject(subject, mail_body)
    mailer.set_plaintext_content(content, mail_body)

    # using print() will also return status code and data
    res = mailer.send(mail_body)
    if res != "202\n":
        print(
            f"Error: sending email. Username: {username}, Email: {useremail}, \
              Subject: {subject}, Content:{content}"
        )
        print(f"Error Message: {res}")
        return False
    else:
        print("成功送出Email")
        return True


def lambda_handler(event, context):
    # 每個function 都要做的事
    body = json.loads(event["Records"][0]["body"])
    print(f"來源內容{body}")
    queue_obj = QueueObj(None, body)
    current_job = Job(queue_obj.steps[queue_obj.step_now])
    current_job.update_start_time()  # 更新開始時間
    customer_input = current_job.parse_customer_input(queue_obj.steps)

    # lambda 獨特性
    username = customer_input["username"]
    user_email = customer_input["email"]
    subject = customer_input["subject"]
    content = customer_input["content"]
    send_result = send_email(username, user_email, subject, content)
    if not send_result:
        job_status = "failed"
        results_output = {"success": False}
    else:
        job_status = "success"
        results_output = {"success": True}

    # 每個function 都要做的事
    current_job.update_job_status(job_status)
    current_job.update_result_output(results_output)
    current_job.update_end_time()
    queue_obj.update_job_status(current_job)
    queue_obj.put_to_sqs()
    return {"lambda msg": results_output}
