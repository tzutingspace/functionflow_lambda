import pymysql
import os

from error_handler import MyErrorHandler

# from get_secret import get_secret
db_settings = {
    "host": os.environ["MYSQL_HOST"],
    "port": 3306,
    "user": os.environ["MYSQL_USER"],
    "password": os.environ["MYSQL_PASSWORD"],
    "db": os.environ["MYSQL_DATABASE"],
}


class Database:
    def __init__(self):
        self.connection = pymysql.connect(**db_settings)

    def queryall(self, sql, params=None):
        with self.connection.cursor() as cursor:
            try:
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                result = [
                    dict((cursor.description[i][0], value) for i, value in enumerate(row))
                    for row in cursor.fetchall()
                ]
            except Exception as e:
                MyErrorHandler().handle_error("Unexpected Error:", str(e))
                result = "ERROR"
        return result

    def insert(self, sql, params=None):
        with self.connection.cursor() as cursor:
            try:
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                self.connection.commit()
                result = cursor.lastrowid
            except Exception as e:
                MyErrorHandler().handle_error("Unexpected Error:", str(e))
                result = "ERROR"
            return result

    def update(self, sql, params=None, many=None):
        with self.connection.cursor() as cursor:
            print("sql:", sql, "params:", params)
            try:
                if params:
                    if many:
                        cursor.executemany(sql, params)
                    else:
                        cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                result = cursor.rowcount
                self.connection.commit()
            except Exception as e:
                MyErrorHandler().handle_error("Unexpected Error:", str(e))
                result = "ERROR"
        return result

    def close(self):
        self.connection.close()


if __name__ == "__main__":
    connection = Database().connection
    with connection.cursor() as cursor:
        # 找出本次符合條件的 workflow
        sql = " SELECT * FROM workflows"
        cursor.execute(sql)
        # 取得所有資料
        result = [
            dict((cursor.description[i][0], value) for i, value in enumerate(row))
            for row in cursor.fetchall()
        ]
    connection.close()
    print("測試database連線：", result)
