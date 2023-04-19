import os
from datetime import datetime, timedelta, timezone

from database import Database
from Job import Job
from QueueObj import QueueObj
from Workflow import Workflow


def lambda_handler(event, context):
    # 抓取本次Scheduler區間
    dt0 = datetime.utcnow().replace(tzinfo=timezone.utc)
    current_date_and_time = dt0.astimezone(timezone(timedelta(hours=8)))
    time_interval = timedelta(minutes=int(os.environ["MIN_TIME_INTERVAL"]))
    end_date_and_time = current_date_and_time + time_interval

    print(f"本次Scheuler預計抓取區間 {current_date_and_time} ~ {end_date_and_time}")

    db = Database()

    sql = """SELECT
            id,
            name,
            trigger_type,
            next_execute_time,
            schedule_interval,
            trigger_interval_seconds
            FROM workflows
            WHERE
                status = "active"
                AND trigger_type = "scheduled"
                AND next_execute_time >= %(current_date_and_time)s
                AND next_execute_time <= %(end_date_and_time)s
            """
    params = {
        "current_date_and_time": current_date_and_time,
        "end_date_and_time": end_date_and_time,
    }

    workflows = db.queryall(sql, params)
    print(f"本次預計跑的 workflow 有 {len(workflows)} 筆")

    for workflow in workflows:
        queue_obj = QueueObj("jobsQueue", {})
        # init workflow instance
        workflow_obj = Workflow(workflow)
        workflow_obj.calculate_next_execute_time()
        workflow_obj.update_db_workflow_next_execute_time(db)
        workflow_obj.create_wf_instance(db)

        # 將資訊放進Queue_obj中
        queue_obj.init_workflow(vars(workflow_obj))

        # 取得該筆 workflow 所有的jobs
        jobs_detail = workflow_obj.get_jobs_from_db(db)
        prev_job_instance_id = None

        print(f">>該 workflow 有 {len(jobs_detail)} 筆Job")
        # create job instances sequentially
        for job_detail in jobs_detail:
            job = Job(job_detail)

            # 第一個JOB
            if job.sequence == 1:
                queue_obj.change_step(vars(job))

            # 建立job instance
            prev_job_instance_id = job.create_job_instance(
                workflow_obj.wf_instance_id, prev_job_instance_id, db
            )

            # 將資料寫到queue_obj
            print(f">>>> 建立job_instances{vars(job)}")
            queue_obj.add_step(vars(job))

        # 將此queueObj 丟到SQS
        queue_obj.put_to_sqs()

    db.close()

    return {"lambda msg": "Sceduler Success"}
