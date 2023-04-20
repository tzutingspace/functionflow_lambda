# import logging


class MyErrorHandler:
    error_log = []

    @classmethod
    def handle_error(cls, error_type, error_msg):
        error = {"type": error_type, "msg": error_msg}
        cls.error_log.append(error)
        print(f"錯誤類型: {error_type}，錯誤訊息: {error_msg}")
