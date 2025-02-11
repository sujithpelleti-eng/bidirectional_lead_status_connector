![](https://img.shields.io/badge/Python-v3.10-blue?style=plastic&logo=python)  
![](https://img.shields.io/badge/Docker-v20.10-orange?style=plastic&logo=docker)  
![](https://img.shields.io/badge/Localstack-v0.13.2-green?style=plastic&logo=amazonaws)

Quick Links: [AWS CLI](https://aws.amazon.com/cli/) | [Docker Desktop](https://www.docker.com/products/docker-desktop/)

# Bidirectional Lead Status Connector

This repository contains the code for a system that facilitates the integration of lead status updates from external systems (e.g., Yardi) into internal databases and vice versa. It supports data fetching, processing, and posting updates dynamically, with a focus on extensibility and configurability.

---

## Table of Contents

- [Overview](#overview)
- [Repo Structure](#repo-structure)
- [Setup](#setup)
- [Usage](#usage)
---

## Overview

The Bidirectional Lead Status Connector is designed to:

- Fetch data from external systems.
- Store Raw data in S3
- Process the data as per the expected schema 
- Store the transformed data in RDS.
- Post processed data to APIs Asynchronously.
- Manage retries and error handling efficiently.

---

## Repo Structure

```
├── common/                                ----- 📦
│   ├── __init__.py
│   ├── models.py
│   ├── postgres_connector.py
│   ├── s3_utils.py
│   ├── utils.py
├── config/                                ----- 🔧
│   ├── __init__.py
│   ├── .env
│   └── .env.example
├── connectors/                            ----- 💻
│   ├── __init__.py
│   ├── base_rest_connector.py
│   ├── base_soap_connector.py
│   └── yardi_connector.py
├── destinations/                          ----- 📦
│   ├── __init__.py
│   ├── base_destination.py
│   ├── rds_destination.py
│   └── s3_destination.py
├── parsers/                               ----- 🔄
│   ├── base_parser.py
│   ├── yardi_parser.py
├── scripts/                               ----- 📜
├── ddl/                                   ----- 🗄️
│   └── DDL.sql
├── .dockerignore                          ----- 🐳
├── .flake8                                ----- 🧹
├── .gitignore                             ----- :octocat:
├── .pre-commit-config.yaml                ----- 🛠️
├── async_status_update.py                 ----- ⚙️
├── docker-compose.yml                     ----- 🐳
├── Dockerfile                             ----- 🐳
├── main.py                                ----- 🚀
├── orchestrator.py                        ----- 🔄
├── README.md                              ----- 📄
├── requirements.in                        ----- 📋
├── requirements.txt                       ----- 📋
```
## Setup

### Prerequisites

1. **Docker & Docker Compose**:  
   Install Docker from [Docker Desktop](https://www.docker.com/products/docker-desktop).
2. **AWS CLI**:  
   Install AWS CLI from [AWS CLI](https://aws.amazon.com/cli/).
3. **Postgres**:  
   Ensure Postgres is running inside Docker (part of the repo).

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-repo/bidirectional_lead_status_connector.git
cd bidirectional_lead_status_connector
```
### Step 2: Create the .env file under config with the below values
```bash
# Database Configuration
RDS_DB_HOST=localhost
RDS_DB_PORT=5432
RDS_DB_USER=postgres
RDS_DB_PASSWORD=postgres
RDS_DB_NAME=postgres

# Python Path
PYTHONPATH=:/Users/sujithpelleti/Desktop/Work/Codebase/bidirectional_lead_status_connector

# AWS Configuration
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=dummy
AWS_SECRET_ACCESS_KEY=dummy
AWS_SESSION_TOKEN=dummy
AWS_S3_ENDPOINT_URL=http://localhost:4566
```
### Step 3:Start Postgres, and Localstack with `docker compose`
   ```bash
   docker compose --env-file config/.env up -d
   ```
   - You can alternately use `docker compose --env-file config/.env create` to build the container and then `docker compose --env-file config/.env start` to run the services
      - `docker compose  --env-file config/.env stop` will stop the container
   - You do not need Postgres installed locally, you can connect to this one with an IDE or by installing Postgres locally to use the command line 
   - If you encounter warnings or errors, check your version of `compose`. Versions prior to 2 (i.e. v1.29.x) do not have the same environment variable behaviors

### Step 4: Connect to the Postgres using DBeaver or another client and create the schema using below command
```bash
CREATE SCHEMA provider_integration;
```
### Step 5: Create the table and run insert commands from models.py file from the repo
### Step 6: Create the S3 Bucket using the below commands in local stack
```bash
# Create the bucket
aws --endpoint-url=http://localhost:4566 s3 mb s3://yardi-bucket

#Verify the bucket
aws --endpoint-url=http://localhost:4566 s3 ls
```

## Usage

### Running the Orchestrator
Use the following command to run the orchestrator:

```bash
python main.py --action orchestrator --schedule 'Daily EOD' --partner_id '8fd80722-b076-4341-baf2-b25cef736651' --system Yardi --full-refresh
```
### Command Options

Below are the configurable options for executing tasks:

- **`--action`**  
  Specify the action to perform. Options:  
  - `orchestrator`: Fetch and process data.  
  - `post_status_updates`: Post status updates to an external system.  
  **Example**: `--action orchestrator`

- **`--schedule`**  
  Filter by schedule (e.g., 'Daily EOD').  
  **Example**: `--schedule 'Daily EOD'`

- **`--system`**  
  Specify the system (e.g., Yardi).  
  **Example**: `--system Yardi`

- **`--partner_id`**  
  Filter by partner ID.  
  **Example**: `--partner_id '8fd80722-b076-4341-baf2-b25cef736651'`

- **`--from-date`**  
  Start date for fetching data (format: YYYY-MM-DD).  
  **Example**: `--from-date 2024-01-01`

- **`--to-date`**  
  End date for fetching data (format: YYYY-MM-DD).  
  **Example**: `--to-date 2024-12-31`

- **`--full-refresh`**  
  Fetch data for the past year, ignoring date filters.  
  **Example**: `--full-refresh`

### Usage Examples

#### Running Status Update Posting 
To post status updates, use the following command:
```bash
python main.py --action post_status_updates
```

### Stopping Containers
```bash
docker-compose down
```
### Rebuilding Containers
```bash
docker-compose up --build
```
