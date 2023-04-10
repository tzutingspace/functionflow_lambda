from constructs import Construct
from aws_cdk.aws_lambda_event_sources import SqsEventSource
from aws_cdk import aws_sqs as sqs
from aws_cdk import Duration
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_iam as iam
from aws_cdk import CfnOutput, Stack
from aws_cdk import CfnParameter
import os

from dotenv import load_dotenv
load_dotenv()


class FunctionflowCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 定義參數
        MYSQL_HOST = CfnParameter(
            self, 'MYSQL_HOST',
            type='String',
            description='MYSQL_HOST',
            no_echo=True,  # 配置参数不顯示
        )
        MYSQL_USER = CfnParameter(
            self, 'MYSQL_USER',
            type='String',
            description='MYSQL_USER',
            no_echo=True,  # 配置参数不顯示
        )
        MYSQL_PASSWORD = CfnParameter(
            self, 'MYSQL_PASSWORD',
            type='String',
            description='MYSQL_PASSWORD',
            no_echo=True,  # 配置参数不顯示
        )
        MYSQL_DATABASE = CfnParameter(
            self, 'MYSQL_DATABASE',
            type='String',
            description='MYSQL_DATABASE',
            no_echo=True,  # 配置参数不顯示
        )
        AWS_REGION_NAME = CfnParameter(
            self, 'AWS_REGION_NAME',
            type='String',
            description='AWS_REGION_NAME',
            no_echo=True,  # 配置参数不顯示
        )
        MIN_TIME_INTERVAL = CfnParameter(
            self, 'MIN_TIME_INTERVAL',
            type='String',
            description='sheduler min time to tigger',
            no_echo=True,  # 配置参数不顯示
        )
        OPENAPIKEY = CfnParameter(
            self, 'OPENAPIKEY',
            type='String',
            description='weather OPENAPIKEY',
            no_echo=True,  # 配置参数不顯示
        )
        DISCORDBOTTOKEN = CfnParameter(
            self, 'DISCORDBOTTOKEN',
            type='String',
            description='DISCORD BOT TOKEN',
            no_echo=True,  # 配置参数不顯示
        )
        ENV = CfnParameter(
            self, 'ENV',
            type='String',
            description='ENV',
            no_echo=True,  # 配置参数不顯示
        )
        AWSQUEUEURL = CfnParameter(
            self, 'AWSQUEUEURL',
            type='String',
            description='AWS QUEUE URL',
            no_echo=True,  # 配置参数不顯示
        )

        # 透過角色 ARN 來取得現有的 IAM 角色
        existing_role_arn = f'arn:aws:iam::{os.environ["AWS_ACCOUNT"]}:role/{os.environ["AWS_ROLE"]}'
        existing_role = iam.Role.from_role_arn(
            self, 'ExistingRole', role_arn=existing_role_arn
        )

        # Outputs出欲確認資料
        # CfnOutput(self, "ServiceAccountIamRole", value=existing_role.role_arn)

        # Create a new SQS Queue
        queue = sqs.Queue(self, "jobsQueue", queue_name='jobsQueue')
        get_weather_queue = sqs.Queue(
            self, "getWeatherQueue", queue_name='getWeatherQueue')
        send_message_queue = sqs.Queue(
            self, "sendMessageQueue", queue_name='sendMessageQueue')

        # Defines an AWS Lambda Layer
        lambdaLayer = _lambda.LayerVersion(
            self,
            "lambda-layer",
            code=_lambda.AssetCode("lambda/layer/"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_7,
                                 _lambda.Runtime.PYTHON_3_8,
                                 _lambda.Runtime.PYTHON_3_9],
        )

        # Defines an AWS Lambda resource
        # scheduler
        scheduler = _lambda.Function(
            self, 'scheduler', runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset('lambda/code/scheduler'),
            handler='scheduler.lambda_handler',
            layers=[lambdaLayer],
            role=existing_role,
            environment={
                'AWS_REGION_NAME': AWS_REGION_NAME.value_as_string,
                'MYSQL_HOST': MYSQL_HOST.value_as_string,
                'MYSQL_USER': MYSQL_USER.value_as_string,
                'MYSQL_PASSWORD': MYSQL_PASSWORD.value_as_string,
                'MYSQL_DATABASE': MYSQL_DATABASE.value_as_string,
                'MIN_TIME_INTERVAL': MIN_TIME_INTERVAL.value_as_string,
                'ENV': ENV.value_as_string,
                'AWS_QUEUE_URL': AWSQUEUEURL.value_as_string
            }
        )

        # executer
        executer = _lambda.Function(
            self, 'executer', runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset('lambda/code/executer'),
            handler='executer.lambda_handler',
            layers=[lambdaLayer],
            role=existing_role,
            environment={
                'AWS_REGION_NAME': AWS_REGION_NAME.value_as_string,
                'MYSQL_HOST': MYSQL_HOST.value_as_string,
                'MYSQL_USER': MYSQL_USER.value_as_string,
                'MYSQL_PASSWORD': MYSQL_PASSWORD.value_as_string,
                'MYSQL_DATABASE': MYSQL_DATABASE.value_as_string,
                'ENV': ENV.value_as_string,
                'AWS_QUEUE_URL': AWSQUEUEURL.value_as_string
            }
        )
        event_source = SqsEventSource(queue)
        executer.add_event_source(event_source)

        # get_weather
        get_weather = _lambda.Function(
            self, 'get_weather', runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset('lambda/code/fn/get_weather'),
            handler='get_weather.lambda_handler',
            layers=[lambdaLayer],
            role=existing_role,
            environment={
                'AWS_REGION_NAME': AWS_REGION_NAME.value_as_string,
                'MYSQL_HOST': MYSQL_HOST.value_as_string,
                'MYSQL_USER': MYSQL_USER.value_as_string,
                'MYSQL_PASSWORD': MYSQL_PASSWORD.value_as_string,
                'MYSQL_DATABASE': MYSQL_DATABASE.value_as_string,
                'OPENAPIKEY': OPENAPIKEY.value_as_string,
                'ENV': ENV.value_as_string,
                'AWS_QUEUE_URL': AWSQUEUEURL.value_as_string
            }
        )
        get_weather_event_source = SqsEventSource(get_weather_queue)
        get_weather.add_event_source(get_weather_event_source)

        # send_message
        send_message = _lambda.Function(
            self, 'send_message', runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset('lambda/code/fn/send_message'),
            handler='send_message.lambda_handler',
            layers=[lambdaLayer],
            role=existing_role,
            timeout=Duration.seconds(3600),
            environment={
                'AWS_REGION_NAME': AWS_REGION_NAME.value_as_string,
                'MYSQL_HOST': MYSQL_HOST.value_as_string,
                'MYSQL_USER': MYSQL_USER.value_as_string,
                'MYSQL_PASSWORD': MYSQL_PASSWORD.value_as_string,
                'MYSQL_DATABASE': MYSQL_DATABASE.value_as_string,
                'DISCORDBOTTOKEN': DISCORDBOTTOKEN.value_as_string,
                'ENV': ENV.value_as_string,
                'AWS_QUEUE_URL': AWSQUEUEURL.value_as_string
            }
        )
        send_message_event_source = SqsEventSource(send_message_queue)
        send_message.add_event_source(send_message_event_source)
