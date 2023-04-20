import json

from error_handler import MyErrorHandler
from Job import Job
from job_handler import parseString
from QueueObj import QueueObj


def greater_than(initial_value, second_value):
    return initial_value > second_value


def less_than(initial_value, second_value):
    return initial_value < second_value


def equal(initial_value, second_value):
    return initial_value == second_value


# 將每個 condition 對應到一個函式
conditions = {
    "greater_than": greater_than,
    "less_than": less_than,
    "equal": equal,
}


def lambda_handler(event, context):
    # 每個function 都要做的事
    print("START EVENT", event)
    body = json.loads(event["Records"][0]["body"])
    print(f"來源內容{body}")
    queue_obj = QueueObj(None, body)
    current_job = Job(queue_obj.steps[queue_obj.step_now])
    current_job.update_start_time()  # 更新開始時間
    customer_input = current_job.parse_customer_input(queue_obj.steps)

    # filter 要做的事情
    # 使用對應的函式進行條件判斷
    try:
        condition = customer_input["condition"]
        initial_value = int(customer_input["initial_value"])
        second_value = int(customer_input["Second_value"])
        result = conditions.get(condition, lambda x, y: False)(initial_value, second_value)
        print(f"本次filter情況 {initial_value} {condition} {second_value}")
    except ValueError as e:
        MyErrorHandler.handle_error("ValueError", f"@filter function {e}")
        result = "Error"
    except KeyError as e:
        MyErrorHandler.handle_error("KeyError", f"@filter function {e}")
        result = "Error"

    if result == "Error":
        job_status = "failed"
        results_output = {}
        for output in parseString(current_job.config_output):
            results_output[output["name"]] = "Error"
    else:
        job_status = "success" if result else "unfulfilled"
        results_output = {"success": result}

    # 每個function 都要做的事
    current_job.update_job_status(job_status)
    current_job.update_result_output(results_output)
    current_job.update_end_time()

    queue_obj.update_job_status(current_job)
    queue_obj.put_to_sqs()

    return {"lambda msg": results_output}
