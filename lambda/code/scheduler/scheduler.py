from put_to_sqs import put_to_sqs
from database import Database
import os
from datetime import datetime, timezone, timedelta
import json
import pymysql
from botocore.exceptions import ClientError
import boto3


def lambda_handler(event, context):
    dt0 = datetime.utcnow().replace(tzinfo=timezone.utc)
    current_date_and_time = dt0.astimezone(timezone(timedelta(hours=8)))
    time_interval = timedelta(
        minutes=int(os.environ["MIN_TIME_INTERVAL"]))
    end_date_and_time = current_date_and_time + time_interval

    print(f'本次預計抓取區間 {current_date_and_time} ~ {end_date_and_time}')

    # 寫到 queue和  workflows_instances
    connection = Database().connection

    with connection.cursor() as cursor:
        # 找出本次符合條件的 workflow
        sql = f'SELECT id, name, trigger_type, next_execute_time FROM workflows WHERE status = "active" AND \
        next_execute_time >= %(current_date_and_time)s AND next_execute_time <= %(end_date_and_time)s'
        cursor.execute(sql, {"current_date_and_time": current_date_and_time,
                             "end_date_and_time": end_date_and_time})
        # 取得所有資料
        work_flows = [dict((cursor.description[i][0], value)
                           for i, value in enumerate(row)) for row in cursor.fetchall()]

        print(f'本次預計跑的 workflow 有 {len(work_flows)} 筆')

    for work_flow in work_flows:
        QUEUE_OBJ = {}
        with connection.cursor() as cursor:
            # Init workflow instances info
            work_flow["next_execute_time"] = work_flow["next_execute_time"].strftime(
                '%Y-%m-%d %H:%M:%S')
            work_flow["status"] = "queued"
            work_flow["execution_time"] = current_date_and_time.strftime(
                '%Y-%m-%d %H:%M:%S')

            # 建立 workflows_instances
            sql = f'INSERT INTO workflows_instances(workflows_id, `status`, trigger_type, execution_time, external_trigger)\
                        VALUES(%(id)s, %(status)s, %(trigger_type)s, %(execution_time)s, "f")'
            cursor.execute(sql, work_flow)
            work_flow["wf_instance_id"] = cursor.lastrowid
            print(f'>>建立work_flow_instances {work_flow}')
            connection.commit()

            # ## 取得該筆 workflow 所有的jobs
            sql = f'SELECT jobs.id, jobs.name, jobs.sequence, jobs.depends_job_id, jobs.config_input, jobs.config_output,\
                    jobs.next_job_number, `functions`.name as function_name, `functions`.id as function_id \
                    FROM `jobs` INNER JOIN `functions` ON jobs.function_id = `functions`.id WHERE workflow_id = %(id)s ORDER BY sequence'
            cursor.execute(sql, work_flow)

            job_details = [dict((cursor.description[i][0], value)
                                for i, value in enumerate(row)) for row in cursor.fetchall()]

            print(f'>>該 workflow 有 {len(job_details)} 筆Job')
        with connection.cursor() as cursor:
            QUEUE_OBJ['steps'] = {}
            job_instance_id = None
            # 建立 jobs_instances
            for job in job_details:
                print(f'>>>> 建立job_instances{job}')
                job['status'] = 'waiting'
                job['depends_job_instance_id'] = job_instance_id
                if job['sequence'] == 1:
                    QUEUE_OBJ['step_now'] = job['name']
                sql = f"INSERT INTO jobs_instances (workflow_instance_id, name, status, \
                    sequence, funciton_id, config_input, config_output, next_job_number, depends_job_instance_id) \
                    VALUES ({work_flow['wf_instance_id']}, %(name)s, %(status)s,  %(sequence)s, %(function_id)s, %(config_input)s, %(config_output)s, \
                    %(next_job_number)s, %(depends_job_instance_id)s)"
                cursor.execute(sql, job)
                job_name = job['name']
                QUEUE_OBJ['steps'][job_name] = job
                job_instance_id = cursor.lastrowid
            connection.commit()
        # 加入queue中
        res = put_to_sqs(QUEUE_OBJ, 'jobsQueue')
        # print(f'workflows_instances_id={work_flow["wf_instance_id"]}, 已加入SQS')

    connection.close()
    return 'success'
