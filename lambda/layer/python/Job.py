import json
import re
from job_handler import get_now_time, parseString
from error_handler import MyErrorHandler


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

    def update_job_status(self, new_status):
        self.status = new_status

    def update_start_time(self):
        self.start_time = get_now_time()

    def update_end_time(self):
        self.end_time = get_now_time()

    def update_result_output(self, results):
        self.result_output = {}
        outputs = parseString(self.config_output)
        print("@update_result_output outputs", outputs)
        for output in outputs:
            output_name = output["name"]
            self.result_output[output_name] = results[output_name]
        self.result_output = json.dumps(self.result_output)

    def parse_customer_input(self, stepsInfo):
        pattern = r"{{(.*?)}}"
        matches = re.findall(pattern, self.customer_input)
        config = self.customer_input  # string
        results = matches if matches else []
        print("parse results: ", results)
        for result in results:
            _, job_name, result_name = result.split(".")
            try:
                # result_output = json.loads(stepsInfo[job_name]["result_output"])
                result_output = parseString(stepsInfo[job_name]["result_output"])
                result_variable = result_output[result_name]
                if type(result_variable) == list:
                    print("處理list格式的資料")
                    combine_string = ""
                    for data in result_variable:
                        combine_string += data.replace("\n", "\\n")
                    result_variable = combine_string
            except TypeError as e:
                MyErrorHandler.handle_error("TypeError", f"@parse custom input: {e}")
                result_variable = "undefined"
            except KeyError as e:
                MyErrorHandler.handle_error("KeyError", f"@parse custom input: {e}")
                result_variable = "undefined"
            config = config.replace("{{" + result + "}}", str(result_variable))  # 取代string
        # return json.loads(config)  # 解析成obj
        print("config result", config)
        return parseString(config)

    @staticmethod
    def update_job_instances(connDB, queueObj):
        sql = """
            UPDATE jobs_instances
            SET status=%s, start_time=%s,
                end_time=%s, result_output=%s
            WHERE id=%s
            """

        jobs = queueObj["steps"]
        params = [
            (
                jobs[job_instances]["status"],
                jobs[job_instances]["start_time"],
                jobs[job_instances]["end_time"],
                jobs[job_instances]["result_output"],
                jobs[job_instances]["id"],
            )
            for job_instances in jobs.keys()
        ]
        result = connDB.update(sql, params, many=True)
        job_instances_ids = [(job[4]) for job in params]
        if result == len(jobs.keys()):
            print(f"Normal: job_instances_id: {job_instances_ids} 更新成功")
        else:
            print(f"Error: job_instances_id: {job_instances_ids} 未更新成功")
