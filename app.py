#!/usr/bin/env python3
import os
from aws_cdk import App
from cdk.pipeline_stack import PipelineStack

app = App()
app_name = app.node.try_get_context("globals")["appName"]
PipelineStack(app, f"{app_name}-PipelineStack")

app.synth()
