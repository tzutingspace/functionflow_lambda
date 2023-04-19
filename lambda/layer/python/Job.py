from job_handler import get_now_time
from job_handler import parseString

# import json


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

        self.depends_job_id = job_info.get("depends_job_id")  # FIXME: 待確認是否需要留存
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

    @staticmethod
    def updata_job_instances(connDB, queueObj):
        sql = """
            UPDATE jobs_instances
            SET status=%s, start_time=%s,
                end_time=%s, result_output=%s
            WHERE id=%s
            """

        jobs = queueObj["steps"]
        params = [
            (
                jobs[jobi]["status"],
                jobs[jobi]["start_time"],
                jobs[jobi]["end_time"],
                jobs[jobi]["result_output"],
                jobs[jobi]["id"],
            )
            for jobi in jobs.keys()
        ]
        result = connDB.update(sql, params, many=True)
        job_instances_ids = [(job[4]) for job in params]
        if result == len(jobs.keys()):
            print(f"Normal: job_instances_id: {job_instances_ids} 更新成功")
        else:
            print(f"Error: job_instances_id: {job_instances_ids} 未更新成功")
