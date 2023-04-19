from datetime import timedelta

from dateutil.relativedelta import relativedelta
from job_handler import get_now_time


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

    def get_jobs_from_db(self, connDB):
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

    @staticmethod
    def update_workflow_instance(connDB, workflowInfo):
        print("Is a workflow staticmethod")
        print(workflowInfo)
        sql = """
            UPDATE workflows_instances
            SET status = %s, execution_time=%s, end_time=%s WHERE id=%s
            """
        result = connDB.update(
            sql,
            (
                workflowInfo["status"],
                workflowInfo["execution_time"],
                get_now_time(),
                workflowInfo["wf_instance_id"],
            ),
        )

        if result == 0:
            print(f"Error: workflow_instance id={workflowInfo['wf_instance_id']} 更新未成功")
        elif result == 1:
            print(f"Normal: workflow_instance id={workflowInfo['wf_instance_id']} 更新成功")
        else:
            print("Error: DB")
