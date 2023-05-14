import os

from aws_cdk import CfnParameter, Duration, Stack, aws_events, aws_events_targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_sqs as sqs
from aws_cdk.aws_lambda_event_sources import SqsEventSource
from constructs import Construct
from dotenv import load_dotenv

# from aws_cdk import CfnOutput
load_dotenv()


class FunctionflowCdkStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 定義參數
        MYSQL_HOST = CfnParameter(
            self,
            "MYSQL_HOST",
            type="String",
            description="MYSQL_HOST",
            no_echo=True,  # 配置参数不顯示
        )
        MYSQL_USER = CfnParameter(
            self,
            "MYSQL_USER",
            type="String",
            description="MYSQL_USER",
            no_echo=True,  # 配置参数不顯示
        )
        MYSQL_PASSWORD = CfnParameter(
            self,
            "MYSQL_PASSWORD",
            type="String",
            description="MYSQL_PASSWORD",
            no_echo=True,  # 配置参数不顯示
        )
        MYSQL_DATABASE = CfnParameter(
            self,
            "MYSQL_DATABASE",
            type="String",
            description="MYSQL_DATABASE",
            no_echo=True,  # 配置参数不顯示
        )
        AWS_REGION_NAME = CfnParameter(
            self,
            "AWS_REGION_NAME",
            type="String",
            description="AWS_REGION_NAME",
            no_echo=True,  # 配置参数不顯示
        )
        MIN_TIME_INTERVAL = CfnParameter(
            self,
            "MIN_TIME_INTERVAL",
            type="String",
            description="scheduler min time to trigger",
            no_echo=True,  # 配置参数不顯示
        )
        OPEN_API_KEY = CfnParameter(
            self,
            "OPEN_API_KEY",
            type="String",
            description="weather OPEN_API_KEY",
            no_echo=True,  # 配置参数不顯示
        )
        DISCORD_BOT_TOKEN = CfnParameter(
            self,
            "DISCORD_BOT_TOKEN",
            type="String",
            description="DISCORD BOT TOKEN",
            no_echo=True,  # 配置参数不顯示
        )
        ENV = CfnParameter(
            self,
            "ENV",
            type="String",
            description="ENV",
            no_echo=True,  # 配置参数不顯示
        )
        AWS_QUEUE_URL = CfnParameter(
            self,
            "AWS_QUEUE_URL",
            type="String",
            description="AWS QUEUE URL",
            no_echo=True,  # 配置参数不顯示
        )
        MAILER_SEND_API_KEY = CfnParameter(
            self,
            "MAILER_SEND_API_KEY",
            type="String",
            description="MAILER_SEND_API_KEY",
            no_echo=True,  # 配置参数不顯示
        )

        # 透過角色 ARN 來取得現有的 IAM 角色
        existing_role_arn = (
            f'arn:aws:iam::{os.environ["AWS_ACCOUNT"]}:role/{os.environ["AWS_ROLE"]}'
        )
        existing_role = iam.Role.from_role_arn(self, "ExistingRole", role_arn=existing_role_arn)

        # Outputs出欲確認資料
        # CfnOutput(self, "ServiceAccountIamRole", value=existing_role.role_arn)

        # Dead_letter_queue
        dlq = sqs.Queue(
            self,
            "myDeadLetterQueue",
            queue_name="myDeadLetterQueue",
        )

        # Defines an AWS Lambda Layer
        lambdaLayer = _lambda.LayerVersion(
            self,
            "lambda-layer",
            code=_lambda.AssetCode("lambda/layer/"),
            compatible_runtimes=[
                _lambda.Runtime.PYTHON_3_7,
                _lambda.Runtime.PYTHON_3_8,
                _lambda.Runtime.PYTHON_3_9,
            ],
        )

        # Defines an AWS Lambda resource
        # scheduler
        scheduler = _lambda.Function(
            self,
            "scheduler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/code/scheduler"),
            handler="scheduler.lambda_handler",
            layers=[lambdaLayer],
            role=existing_role,
            timeout=Duration.seconds(900),  # 15min
            environment={
                "AWS_REGION_NAME": AWS_REGION_NAME.value_as_string,
                "MYSQL_HOST": MYSQL_HOST.value_as_string,
                "MYSQL_USER": MYSQL_USER.value_as_string,
                "MYSQL_PASSWORD": MYSQL_PASSWORD.value_as_string,
                "MYSQL_DATABASE": MYSQL_DATABASE.value_as_string,
                "MIN_TIME_INTERVAL": MIN_TIME_INTERVAL.value_as_string,
                "ENV": ENV.value_as_string,
                "AWS_QUEUE_URL": AWS_QUEUE_URL.value_as_string,
            },
        )

        # eventBridge
        aws_events.Rule(
            self,
            "ScheduleRule",
            schedule=aws_events.Schedule.rate(Duration.minutes(60)),
            targets=[aws_events_targets.LambdaFunction(handler=scheduler)],
        )

        # executer lambda
        executer = _lambda.Function(
            self,
            "executer",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/code/executer"),
            handler="executer.lambda_handler",
            layers=[lambdaLayer],
            role=existing_role,
            timeout=Duration.seconds(900),  # 15min
            environment={
                "AWS_REGION_NAME": AWS_REGION_NAME.value_as_string,
                "MYSQL_HOST": MYSQL_HOST.value_as_string,
                "MYSQL_USER": MYSQL_USER.value_as_string,
                "MYSQL_PASSWORD": MYSQL_PASSWORD.value_as_string,
                "MYSQL_DATABASE": MYSQL_DATABASE.value_as_string,
                "ENV": ENV.value_as_string,
                "AWS_QUEUE_URL": AWS_QUEUE_URL.value_as_string,
            },
        )

        jobs_queue = sqs.Queue(
            self,
            "jobsQueue",
            queue_name="jobsQueue",
            visibility_timeout=Duration.seconds(960),  # 16min,
            receive_message_wait_time=Duration.seconds(20),
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=1, queue=dlq),
        )

        event_source = SqsEventSource(jobs_queue, batch_size=1)
        executer.add_event_source(event_source)

        # manual_executer
        manual_executer = _lambda.Function(
            self,
            "manual_executer",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/code/executer"),
            handler="executer.lambda_handler",
            layers=[lambdaLayer],
            role=existing_role,
            timeout=Duration.seconds(900),  # 15min
            environment={
                "AWS_REGION_NAME": AWS_REGION_NAME.value_as_string,
                "MYSQL_HOST": MYSQL_HOST.value_as_string,
                "MYSQL_USER": MYSQL_USER.value_as_string,
                "MYSQL_PASSWORD": MYSQL_PASSWORD.value_as_string,
                "MYSQL_DATABASE": MYSQL_DATABASE.value_as_string,
                "ENV": ENV.value_as_string,
                "AWS_QUEUE_URL": AWS_QUEUE_URL.value_as_string,
            },
        )

        manualTriggerQueue = sqs.Queue(
            self,
            "manualTriggerQueue",
            queue_name="manualTriggerQueue",
            visibility_timeout=Duration.seconds(960),  # 16min,
            receive_message_wait_time=Duration.seconds(20),
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=1, queue=dlq),
        )

        manual_trigger_event_source = SqsEventSource(manualTriggerQueue, batch_size=1)
        manual_executer.add_event_source(manual_trigger_event_source)

        # get_weather
        get_weather = _lambda.Function(
            self,
            "get_weather",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/code/fn/get_weather"),
            handler="get_weather.lambda_handler",
            layers=[lambdaLayer],
            role=existing_role,
            timeout=Duration.seconds(900),  # 15min
            environment={
                "AWS_REGION_NAME": AWS_REGION_NAME.value_as_string,
                "MYSQL_HOST": MYSQL_HOST.value_as_string,
                "MYSQL_USER": MYSQL_USER.value_as_string,
                "MYSQL_PASSWORD": MYSQL_PASSWORD.value_as_string,
                "MYSQL_DATABASE": MYSQL_DATABASE.value_as_string,
                "OPEN_API_KEY": OPEN_API_KEY.value_as_string,
                "ENV": ENV.value_as_string,
                "AWS_QUEUE_URL": AWS_QUEUE_URL.value_as_string,
            },
        )

        get_weather_queue = sqs.Queue(
            self,
            "getWeatherQueue",
            queue_name="getWeatherQueue",
            visibility_timeout=Duration.seconds(960),  # 16min,
            receive_message_wait_time=Duration.seconds(20),
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=1, queue=dlq),
        )

        get_weather_event_source = SqsEventSource(get_weather_queue, batch_size=1)
        get_weather.add_event_source(get_weather_event_source)

        # send_message
        send_message = _lambda.Function(
            self,
            "send_message",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/code/fn/send_message"),
            handler="send_message.lambda_handler",
            layers=[lambdaLayer],
            role=existing_role,
            timeout=Duration.seconds(900),  # 15min
            environment={
                "AWS_REGION_NAME": AWS_REGION_NAME.value_as_string,
                "MYSQL_HOST": MYSQL_HOST.value_as_string,
                "MYSQL_USER": MYSQL_USER.value_as_string,
                "MYSQL_PASSWORD": MYSQL_PASSWORD.value_as_string,
                "MYSQL_DATABASE": MYSQL_DATABASE.value_as_string,
                "DISCORD_BOT_TOKEN": DISCORD_BOT_TOKEN.value_as_string,
                "ENV": ENV.value_as_string,
                "AWS_QUEUE_URL": AWS_QUEUE_URL.value_as_string,
            },
        )

        send_message_queue = sqs.Queue(
            self,
            "sendMessageToDiscord",
            queue_name="sendMessageToDiscordQueue",
            visibility_timeout=Duration.seconds(960),  # 16min,
            receive_message_wait_time=Duration.seconds(20),
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=1, queue=dlq),
        )

        send_message_event_source = SqsEventSource(send_message_queue, batch_size=1)
        send_message.add_event_source(send_message_event_source)

        # send_message
        send_email = _lambda.Function(
            self,
            "send_email",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/code/fn/send_email"),
            handler="send_email.lambda_handler",
            layers=[lambdaLayer],
            role=existing_role,
            timeout=Duration.seconds(900),  # 15min
            environment={
                "AWS_REGION_NAME": AWS_REGION_NAME.value_as_string,
                "MYSQL_HOST": MYSQL_HOST.value_as_string,
                "MYSQL_USER": MYSQL_USER.value_as_string,
                "MYSQL_PASSWORD": MYSQL_PASSWORD.value_as_string,
                "MYSQL_DATABASE": MYSQL_DATABASE.value_as_string,
                "ENV": ENV.value_as_string,
                "AWS_QUEUE_URL": AWS_QUEUE_URL.value_as_string,
                "MAILER_SEND_API_KEY": MAILER_SEND_API_KEY.value_as_string,
            },
        )

        send_email_queue = sqs.Queue(
            self,
            "sendEmail",
            queue_name="sendEmailQueue",
            visibility_timeout=Duration.seconds(960),  # 16min,
            receive_message_wait_time=Duration.seconds(20),
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=1, queue=dlq),
        )

        send_email_event_source = SqsEventSource(send_email_queue, batch_size=1)
        send_email.add_event_source(send_email_event_source)

        # filter
        filter_lambda = _lambda.Function(
            self,
            "filter",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/code/fn/filter"),
            handler="filter.lambda_handler",
            layers=[lambdaLayer],
            role=existing_role,
            timeout=Duration.seconds(900),  # 15min
            environment={
                "AWS_REGION_NAME": AWS_REGION_NAME.value_as_string,
                "MYSQL_HOST": MYSQL_HOST.value_as_string,
                "MYSQL_USER": MYSQL_USER.value_as_string,
                "MYSQL_PASSWORD": MYSQL_PASSWORD.value_as_string,
                "MYSQL_DATABASE": MYSQL_DATABASE.value_as_string,
                "ENV": ENV.value_as_string,
                "AWS_QUEUE_URL": AWS_QUEUE_URL.value_as_string,
            },
        )

        filter_queue = sqs.Queue(
            self,
            "filterQueue",
            queue_name="filterQueue",
            visibility_timeout=Duration.seconds(960),  # 16min,
            receive_message_wait_time=Duration.seconds(20),
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=1, queue=dlq),
        )

        filter_event_source = SqsEventSource(filter_queue, batch_size=1)
        filter_lambda.add_event_source(filter_event_source)

        # ptt_scrape
        ptt_scrape_lambda = _lambda.Function(
            self,
            "ptt_scrape",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/code/fn/ptt_scrape"),
            handler="ptt_scrape.lambda_handler",
            layers=[lambdaLayer],
            role=existing_role,
            timeout=Duration.seconds(900),  # 15min
            environment={
                "AWS_REGION_NAME": AWS_REGION_NAME.value_as_string,
                "MYSQL_HOST": MYSQL_HOST.value_as_string,
                "MYSQL_USER": MYSQL_USER.value_as_string,
                "MYSQL_PASSWORD": MYSQL_PASSWORD.value_as_string,
                "MYSQL_DATABASE": MYSQL_DATABASE.value_as_string,
                "ENV": ENV.value_as_string,
                "AWS_QUEUE_URL": AWS_QUEUE_URL.value_as_string,
            },
        )

        ptt_scrape_queue = sqs.Queue(
            self,
            "pttScrapeQueue",
            queue_name="pttScrapeQueue",
            visibility_timeout=Duration.seconds(960),  # 16min,
            receive_message_wait_time=Duration.seconds(20),
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=1, queue=dlq),
        )

        ptt_scrape_event_source = SqsEventSource(ptt_scrape_queue, batch_size=1)
        ptt_scrape_lambda.add_event_source(ptt_scrape_event_source)

        # aws_blog_scrape
        aws_blog_scrape_lambda = _lambda.Function(
            self,
            "aws_blog_scrape",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/code/fn/aws_blog_scrape"),
            handler="aws_blog_scrape.lambda_handler",
            layers=[lambdaLayer],
            role=existing_role,
            timeout=Duration.seconds(900),  # 15min
            environment={
                "AWS_REGION_NAME": AWS_REGION_NAME.value_as_string,
                "MYSQL_HOST": MYSQL_HOST.value_as_string,
                "MYSQL_USER": MYSQL_USER.value_as_string,
                "MYSQL_PASSWORD": MYSQL_PASSWORD.value_as_string,
                "MYSQL_DATABASE": MYSQL_DATABASE.value_as_string,
                "ENV": ENV.value_as_string,
                "AWS_QUEUE_URL": AWS_QUEUE_URL.value_as_string,
            },
        )

        aws_blog_scrape_queue = sqs.Queue(
            self,
            "awsBlogScrapeQueue",
            queue_name="awsBlogScrapeQueue",
            visibility_timeout=Duration.seconds(960),  # 16min,
            receive_message_wait_time=Duration.seconds(20),
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=1, queue=dlq),
        )

        aws_blog_scrape_event_source = SqsEventSource(aws_blog_scrape_queue, batch_size=1)
        aws_blog_scrape_lambda.add_event_source(aws_blog_scrape_event_source)
