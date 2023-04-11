class MyErrorHandler:
    def __init__(self):
        self.error_log = []

    def handle_error(self, error_type, error_msg):
        error = {"type": error_type, "msg": error_msg}
        self.error_log.append(error)
        print(f"錯誤類型: {error_type}，錯誤訊息: {error_msg}")

    # def get_error_log(self):
    #     return self.error_log
