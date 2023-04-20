import json
import os

import boto3
from botocore.exceptions import ClientError
from database import Database
from Job import Job
from Workflow import Workflow


class QueueObj:
    def __init__(self, target_queue, queue_Info) -> None:
        self.target_queue = queue_Info.get("target_queue", target_queue)
        self.ready_execute_job = queue_Info.get("ready_execute_job", [])
        self.workflow = queue_Info.get("workflow", {})
        self.steps = queue_Info.get("steps", {})
        self.step_now = queue_Info.get("step_now", None)
        self.socket_id = queue_Info.get("socket_id", None)

    def init_workflow(self, workflow_instance):
        self.workflow = workflow_instance

    def add_step(self, job_instance):
        job_name = job_instance.get("name")
        self.ready_execute_job.append(job_name)
        self.steps[job_name] = job_instance

    def pop_current_step(self):
        self.ready_execute_job.remove(self.step_now)

    def change_step(self, job_instance):
        self.step_now = job_instance.get("name")

    def update_job_status(self, job_instance):
        self.steps[self.step_now] = vars(job_instance)

    def put_to_sqs(self, queue_name=None):
        print(f"預計加入sqs的內容: {json.dumps(vars(self))}")

        if os.environ["ENV"] == "TEST":
            response = "SAM LOCAL TESTing"
            return response

        if not queue_name:
            queue_name = self.target_queue

        client = boto3.client("sqs", region_name=os.environ["AWS_REGION_NAME"])
        try:
            response = client.send_message(
                QueueUrl=f'{os.environ["AWS_QUEUE_URL"]}/{queue_name}',
                MessageBody=json.dumps(vars(self)),
            )
            print("put_to_sqs Response: ", response)
        except ClientError:
            response = ClientError
        finally:
            return response

    def do_next_action(self):
        print("do_next_action")
        current_job_details = self.steps[self.step_now]
        return getattr(self, current_job_details["status"] + "_action")()

    def waiting_action(self):
        queue_name = self.steps[self.step_now]["function_name"] + "Queue"
        self.put_to_sqs(queue_name)
        return {"lambda msg": "此 wfi 第一個 job, 已放進放進SQS"}

    def failed_action(self):
        # 先移除當下job
        self.pop_current_step()
        for job in self.ready_execute_job:
            self.steps[job]["status"] = "upstream_failed"
            self.workflow["status"] = "failed"
        self.no_next_queue_action()
        return {"lambda msg": "此 workflow instance failed"}

    def unfulfilled_action(self):
        # 先移除當下job
        self.pop_current_step()
        for job in self.ready_execute_job:
            self.steps[job]["status"] = "upstream_unfulfilled"
            self.workflow["status"] = "finished"
        self.no_next_queue_action()
        return {"lambda msg": "此 workflow instance finished (upstream_unfulfilled)"}

    def success_action(self):
        # 先移除當下job
        self.pop_current_step()
        standby_job = []
        # 確認下一步是哪一個
        for job in self.ready_execute_job:
            if self.steps[job]["sequence"] == (int(self.steps[self.step_now]["sequence"]) + 1):
                standby_job.append(self.steps[job]["name"])

        # next_job == 1 -> SQS
        if len(standby_job) == 1:
            next_job_name = standby_job[0]
            self.change_step({"name": next_job_name})
            self.step_now = standby_job[0]
            sqs_name = self.steps[next_job_name]["function_name"] + "Queue"
            self.put_to_sqs(sqs_name)
            return {"lambda msg": f"下一個工作, 已放進 {sqs_name} SQS"}

        # next_job == 0 -> 結束workflow
        elif len(standby_job) == 0:
            self.workflow["status"] = "finished"
            self.no_next_queue_action()
            return {"lambda msg": "此 workflow instance finished."}
        # TODO:next_job > 1 -> 判斷要放哪一個job 進SQS
        else:
            print("next jobs > 1 , 請處理")
            return {"lambda msg": "next jobs > 1 , 請處理"}

    def no_next_queue_action(self):
        # 更新 workflow instance 狀態
        print("@no_next_queue_action QueueObj workflow:", self.workflow)
        connDB = Database()
        Workflow.update_workflow_instance(connDB, self.workflow)
        # 更新 jobs 本次紀錄
        Job.updata_job_instances(connDB, vars(self))
        connDB.close()
        print("更新資料庫...")
        if self.workflow["manual_trigger"] == "t":
            print("!!!!! 通知使用者")

    def printQueue(self):
        print("目前queue狀況", vars(self))
