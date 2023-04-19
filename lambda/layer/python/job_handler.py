import json
import os
import re
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError
from dateutil.relativedelta import relativedelta
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


# # 專屬於job >> 寫到job class
# def get_job_info_and_init(body):
#     job_name = body["step_now"]
#     job_info = body["steps"][job_name]
#     job_info["start_time"] = get_now_time()
#     return job_info


# # 專屬於job >> 寫到job class
# def update_job_info(job_info, results_output):
#     job_info["end_time"] = get_now_time()
#     job_info["result_output"] = {}
#     config_outputs = parseString(job_info["config_output"])
#     for output in config_outputs:
#         out_put_name = output["name"]
#         job_info["result_output"][out_put_name] = results_output[out_put_name]
#     return job_info


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


# # 專屬於queue >> 寫到QueueObj class
# def update_body(body, job_info):
#     job_name = body["step_now"]
#     body["steps"][job_name] = job_info
#     return body


class Job:
    def __init__(self, job_info) -> None:
        self.id = job_info.get("id")
        self.name = job_info.get("name")
        self.status = job_info.get("status", "waiting")  # init 的時候預設是waiting
        self.sequence = job_info.get("sequence")

        self.start_time = job_info.get("start_time")
        self.end_time = job_info.get("end_time")

        self.customer_input = job_info.get("customer_input")
        self.config_output = job_info.get("config_output")

        self.depends_job_instance_id = job_info.get("depends_job_instance_id")
        self.result_output = job_info.get("result_output")

        self.depends_job_id = job_info.get("depends_job_id")  ## FIXME: 待確認是否需要留存
        self.function_name = job_info.get("function_name")

    def create_job_instance(self, wf_instance_id, depends_job_instance_id, connDB):
        self.depends_job_instance_id = depends_job_instance_id
        sql = """
            INSERT INTO 
                jobs_instances
                    (workflow_instance_id, name, status, sequence, customer_input, 
                    config_output, depends_job_instance_id, function_name)
                VALUES
                    (%s, %s, %s, %s, %s, 
                    %s, %s, %s)
            """
        params = (
            wf_instance_id,
            self.name,
            self.status,
            self.sequence,
            self.customer_input,
            self.config_output,
            depends_job_instance_id,
            self.function_name,
        )
        insertId = connDB.insert(sql, params)
        self.id = insertId
        return insertId

    def update_start_time(self):
        self.start_time = get_now_time()

    def update_end_time(self):
        self.end_time = get_now_time()

    def update_result_output(self, results):
        self.result_output = {}
        outputs = parseString(self.template_output)
        for output in outputs:
            output_name = output["name"]
            self.result_output[output_name] = results[output_name]


class Workflow:
    def __init__(self, workflow_Info):
        self.id = workflow_Info.get("id")
        self.name = workflow_Info.get("name")
        self.trigger_type = workflow_Info.get("trigger_type")
        self.next_execute_time = workflow_Info.get("next_execute_time")
        self.schedule_interval = workflow_Info.get("schedule_interval")
        self.trigger_interval_seconds = workflow_Info.get("trigger_interval_seconds")
        self.status = workflow_Info.get("status", "queued")  # init的時候為queued
        self.execution_time = workflow_Info.get("execution_time", get_now_time())  # init的時候為當下時間
        self.wf_instance_id = workflow_Info.get("wf_instance_id")
        self.schedule_interval = workflow_Info.get("schedule_interval")
        self.manual_trigger = workflow_Info.get("manual_trigger", "f")  # default為"f"
        self.end_time = workflow_Info.get("end_time")

    def update_workflow_status(self, status):
        self.status = status

    def update_manual_trigger(self, ismanual_trigger):
        self.manual_trigger = ismanual_trigger

    def calculate_next_execute_time(self):
        # 假設都是此 workflow trigger_type schedule 的情況下
        if self.schedule_interval == "custom":
            interval = timedelta(seconds=int(self.trigger_interval_seconds))
        elif self.schedule_interval == "hourly":
            interval = timedelta(hours=1)
        elif self.schedule_interval == "daily":
            interval = timedelta(days=1)
        elif self.schedule_interval == "weekly":
            interval = timedelta(days=7)
        elif self.schedule_interval == "monthly":
            interval = relativedelta(months=1)

        next_time = self.next_execute_time + interval
        next_time = next_time.strftime("%Y-%m-%d %H:%M:%S")
        self.next_execute_time = next_time
        return next_time

    def update_db_workflow_next_execute_time(self, connDB):
        sql = "UPDATE workflows SET next_execute_time = %s WHERE id = %s"
        result = connDB.update(sql, (self.next_execute_time, (self.id)))
        if result == 1:
            print(f"Normal: workflow_id={self.id} next_execute更新成功")
        else:
            print(f"Error: workflow_id={self.id} next_execute更新未成功")

    def create_wf_instance(self, connDB):
        sql = """INSERT INTO workflows_instances
                    (workflow_id, `status`, trigger_type, execution_time, manual_trigger, end_time)
                VALUES
                    (%s, %s, %s, %s, %s, %s)
            """
        params = (
            self.id,
            self.status,
            self.trigger_type,
            self.execution_time,
            self.manual_trigger,
            self.end_time,
        )
        insertId = connDB.insert(sql, params)
        self.wf_instance_id = insertId

    def get_jobs(self, connDB):
        sql = """ SELECT
                    jobs.id,
                    jobs.name,
                    jobs.sequence,
                    jobs.depends_job_id,
                    jobs.customer_input,
                    `functions`.template_output as config_output,
                    `functions`.name as function_name
                FROM `jobs`
                    INNER JOIN `functions` ON jobs.function_id = `functions`.id
                WHERE workflow_id = %s
                ORDER BY sequence
            """
        jobs_detail = connDB.queryall(sql, (self.id))
        return jobs_detail


class QueueObj:
    def __init__(self, target_queue, queue_Info) -> None:
        self.target_queue = queue_Info.get("target_queue", target_queue)
        self.ready_execute_job = queue_Info.get("ready_execute_job", [])
        self.workflow = queue_Info.get("workflow", {})
        self.steps = queue_Info.get("steps", {})
        self.step_now = queue_Info.get("step_now", None)

    def init_workflow(self, workflow_instance):
        self.workflow = workflow_instance

    def add_step(self, job_instance):
        job_name = job_instance.get("name")
        self.ready_execute_job.append(job_name)
        self.steps[job_name] = job_instance

    def change_step(self, job_instance):
        self.step_now = job_instance.get("name")

    def put_to_sqs(self):
        print(f"預計加入sqs的內容: {json.dumps(vars(self))}")

        if os.environ["ENV"] == "TEST":
            response = "SAM LOCAL TESTing"
            return response

        client = boto3.client("sqs", region_name=os.environ["AWS_REGION_NAME"])
        try:
            response = client.send_message(
                QueueUrl=f'{os.environ["AWS_QUEUE_URL"]}/{self.target_queue}',
                MessageBody=json.dumps(vars(self)),
            )
            print("put_to_sqs Response: ", response)
        except ClientError:
            response = ClientError
        finally:
            return response

    def printQueue(self):
        print("目前queue狀況", vars(self))
