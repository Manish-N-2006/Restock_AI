# ReStockAI AWS SAM Local Serverless Integration

This directory contains the infrastructure definition for executing the deterministic ReStockAI backend services via an **AWS SAM Local** Lambda workflow.

## Purpose

The goal of this layer is to demonstrate the **AWS Build It** serverless workflow locally. 
It creates a second execution path into the existing ReStockAI Python services (Risk, Demand, Decision, Logistics), alongside the existing FastAPI application, but executed as an AWS Lambda function triggered by an API gateway event.

## Architecture

```
Manager → Local SAM API → Lambda Handler → Existing ReStockAI Services → SQLite
```
The SAM Lambda function does not replicate business logic. It securely imports the existing backend logic (`backend.app.services.*`) directly.

## Prerequisites

To run this locally, you must install:
1. [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
2. [Docker Desktop](https://www.docker.com/products/docker-desktop) (required for SAM local container emulation)

## Local Execution Guide

### 1. Build the SAM Application
From the root of the repository, build the SAM container image using the `template.yaml`.
```bash
sam build -t infrastructure/sam/template.yaml
```

### 2. Invoke Lambda Locally
You can invoke the Lambda function directly using the sample event.
```bash
sam local invoke ReStockAIAnalysisFunction -e infrastructure/sam/events/analyze.json
```

### 3. Start the Local API
To test the API gateway emulation locally:
```bash
sam local start-api -t infrastructure/sam/template.yaml
```
Then, in a separate terminal window, send a POST request to the endpoint:
```bash
curl -X POST "http://127.0.0.1:3000/sam/analyze" \
     -H "Content-Type: application/json" \
     -d '{"sku_id": "YOG-001", "source_store_id": "STORE_A"}'
```

*(Note for Windows PowerShell users, use `Invoke-RestMethod` or proper string escaping for the JSON payload).*

## Notes
- **No AWS Cloud Deployment**: This is intended purely for local demonstration. Do not run `sam deploy`.
- **Database Context**: SAM mounts the repository root (`CodeUri: ../../`), meaning the local `restock.db` SQLite database is accessible to the container environment at the expected path.
