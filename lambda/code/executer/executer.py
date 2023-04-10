import datetime
import json
import os
from datetime import datetime, timedelta, timezone

import pymysql
from database import Database
from job_handler import get_now_time
from put_to_sqs import put_to_sqs


def update_workflow_instance(body):
    connDB = Database()
    sql = f'UPDATE workflows_instances SET status = %s, start_time=%s, end_time=%s WHERE id = %s'
    id = body["workflow"]["wf_instance_id"]
    status = body["workflow"]["status"]
    start_time = body["workflow"]["execution_time"]
    end_time = get_now_time()
    result = connDB.update(sql, (status, start_time, end_time, id))
    if result == 0:
        print(f'未更新成功， 請確認workflow_instance id = {id} 狀況')
    connDB.close()
    return result


def update_workflow_next_execute_time(body):
    # 防止job執行的期間，更動workflow設定，至RDS重新獲取資料
    connDB = Database()
    sql = f"SELECT id, next_execute_time, trigger_interval_seconds FROM workflows WHERE id = %s"
    workflow_details = connDB.queryall(sql, (body["workflow"]["id"]))[0]
    # 處理下次時間
    interval = timedelta(seconds=int(
        workflow_details["trigger_interval_seconds"]))
    execute_time = workflow_details["next_execute_time"]
    next_time = (execute_time + interval).strftime('%Y-%m-%d %H:%M:%S')
    sql = f"UPDATE workflows SET next_execute_time = %s WHERE id = %s"
    result = connDB.update(sql, (next_time, (body["workflow"]["id"])))
    if result == 0:
        print(f'未更新成功， 請確認workflow id = {body["workflow"]["id"]} 狀況')
    connDB.close()
    return result


def update_job_instances(body):
    connDB = Database()
    sql = f"UPDATE jobs_instances SET status=%s, start_time=%s, \
                end_time=%s, result_input=%s, result_output=%s WHERE id=%s"

    jobs = body["steps"]
    params = [(jobs[jobi]["status"], jobs[jobi]["start_time"], jobs[jobi]["end_time"],
               jobs[jobi]["result_input"], jobs[jobi]["result_output"], jobs[jobi]["id"]) for jobi in jobs.keys()]
    result = connDB.update(sql, params, many=True)
    if result != len(body["steps"].keys()):
        print(f'未全部更新成功， 請確認job id = {[(job[5]) for job in params]} 狀況')
    connDB.close()
    return result

# 主要邏輯


def lambda_handler(event, context):
    print('Start EVENT', event)
    body = json.loads(event["Records"][0]["body"])
    current_job_name = body["step_now"]
    current_job_details = body["steps"][current_job_name]

    # current Job == waiting 表示剛進到executer >> 直接分配job
    if current_job_details["status"] == "waiting":
        body["workflow"]["start_time"] = get_now_time()
        put_to_sqs(body, current_job_details["function_name"])
        print(f'第一個job, 已放進放進SQS')
        return {"msg": "第一個job, 已放進放進SQS"}

    # current Job == success 表示剛完成上一個作業 >> 確認是否有下一個工作 >> 紀綠 >> 變更
    body["ready_execute_job"].remove(current_job_name)
    if current_job_details["status"] == "success":
        standby_job = []
        for job in body["ready_execute_job"]:
            if body["steps"][job]["sequence"] == (int(current_job_details["sequence"]) + 1):
                standby_job.append(body["steps"][job]["name"])

        # next_job == 1 -> SQS
        if len(standby_job) == 1:
            next_job_name = standby_job[0]
            body["step_now"] = standby_job[0]
            print(f"下一個工作, 已放進放進SQS")
            put_to_sqs(body, body["steps"][next_job_name]["function_name"])
            return {"msg": "下一個工作, 已放進放進SQS"}
        elif len(standby_job) == 0:
            body["workflow"]["status"] = "finished"
            print(f"完成所有jobs")
        # TODO:next_job > 1 -> 判斷要放哪一個job 進SQS
        else:
            print(f'next jobs > 1 , 請處理')

    # failed... 表示job 發生錯誤 >> 更新 waiting 的job 都要更新為upstream_failed
    elif current_job_details["status"] == "failed":
        for job in body["ready_execute_job"]:
            body["steps"][job]["status"] = "upstream_failed"
            body["workflow"]["status"] = "failed"
    # unfulfilled... 表示job 發生未達設定標準 >> 下面的job 都要更新為upstream_unfulfilled
    elif current_job_details["status"] == "unfulfilled":
        for job in body["ready_execute_job"]:
            body["steps"][job]["status"] = "upstream_unfulfilled"
            body["workflow"]["status"] = "finished"
    else:
        print(f'job_instances出現未設定的狀態 , 請處理')
    # 依據body中內容，更新DB資料
    # 更新 workflow instance 狀態
    update_workflow_instance(body)
    # 更新 workflow 下次時間
    update_workflow_next_execute_time(body)
    # 更新 jobs 本次紀錄
    update_job_instances(body)
    print("workflow已結束")
    return {"msg": "workflow已結束"}
