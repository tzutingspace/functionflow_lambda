# FunctionFlow
<div>
  <img alt="GitHub" src="https://img.shields.io/github/license/tzutingspace/functionflow_lambda">
  <img src="https://img.shields.io/github/languages/count/tzutingspace/functionflow_lambda">
  <img src="https://img.shields.io/github/languages/top/tzutingspace/functionflow_lambda">
  <img alt="GitHub last commit" src="https://img.shields.io/github/last-commit/tzutingspace/functionflow_lambda">
  <img alt="GitHub watchers" src="https://img.shields.io/github/watchers/tzutingspace/functionflow_lambda?style=social">
</div>
<br>


## Description
FunctionFlow is an integration platform that empowers users to freely combine various jobs as a workflow, while offering the flexibility to select the execution time through scheduled trigger service, automate and customize with ease.

FunctionFlow mainly consists of two parts. One is the frontend interface and backend server for users to create, edit, and manually trigger workflows. The other major part is that each workflow [job is executed using AWS Lambda](https://github.com/tzutingspace/functionflow_lambda).

This projects contains two repositories:

1. [Backend server and frontend web pages ](https://github.com/tzutingspace/functionflow)
2. [All Lambda code and the SQS and Lambda deployments done through CDK (this repo)](https://github.com/tzutingspace/functionflow_lambda)

## Repo Structure and its Functionality
- functionflow_cdk
  - This directory is used for deploying Lambdas and SQS with AWS CDK.
- lambda/layer/python
  - The lambda/layer/python directory is used to store shared classes or functions that are used across multiple Lambdas.
- lambda/code/scheduler
  - The lambda/code/scheduler directory checks the database for workflows that need to be executed using EventBridge to schedule AWS Lambda functions.
- lambda/code/executer
  - The lambda/code/executer directory is responsible for verifying the job details and assigning tasks by placing them in the corresponding SQS queues.
- lambda/fn
  - The lambda/fn directory contains all the job functionalities provided to the users
  
## Contact 
- Name: Tzuting Huang  
- Email: tzutingh2@gmail.com