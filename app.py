#!/usr/bin/env python3
import os

import aws_cdk as cdk

from functionflow_cdk.functionflow_cdk_stack import FunctionflowCdkStack


app = cdk.App()
FunctionflowCdkStack(
    app,
    "FunctionflowCdkStack",
)

app.synth()
