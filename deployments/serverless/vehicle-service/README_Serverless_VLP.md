# VLP Vehicle Service  
## Serverless Framework Deployment (AWS)

---

## 1. Overview

This directory contains the deployment configuration for the **Vehicle Service** of the Vehicle Listing Platform (VLP) using the **Serverless Framework** on AWS.

The service is implemented in **Go (net/http)** and deployed as:

- AWS Lambda (Runtime: provided.al2023)
- Architecture: arm64
- Memory: 512 MB
- Timeout: 30 seconds
- Region: eu-central-1
- API Layer: Amazon API Gateway (REST, Stage: prod)
- Database: External MongoDB (Managed Service)

---

## 2. Prerequisites

- Node.js installed
- Serverless Framework v3 (`sls`)
- AWS CLI configured (`aws configure`)
- AWS credentials with permissions for:
  - CloudFormation
  - Lambda
  - API Gateway
  - IAM
  - S3
- Compiled Go binary named `bootstrap` (located in this directory)
- Reachable external MongoDB instance

---

## 3. Environment Configuration

Create a `.env` file in this directory:

MONGO_URI=mongodb+srv://<your-uri>  
MONGO_DB=vlp  
MONGO_COLLECTION=vehicles  

The `.env` file is loaded automatically via `useDotenv: true`.

Do not commit `.env` to version control.

---

## 4. Deployment

Deploy to AWS (Stage: prod, Region: eu-central-1):

sls deploy --stage prod --region eu-central-1

---

## 5. API Endpoints (Stage: prod)

Base URL:

https://x9j41qq8u8.execute-api.eu-central-1.amazonaws.com/prod

Available routes:

- GET     /healthz
- GET     /readyz
- GET     /vehicles
- POST    /vehicles
- GET     /vehicles/{id}
- DELETE  /vehicles/{id}

---

## 6. Logs

View CloudWatch logs:

sls logs -f api --stage prod --region eu-central-1

---

## 7. Removal (Cleanup)

Remove the deployment and all associated resources:

sls remove --stage prod --region eu-central-1

---

## 8. Reproducibility Requirements

For valid and comparable performance testing, the following parameters must remain constant:

- AWS region (eu-central-1)
- Memory allocation (512 MB)
- Timeout configuration (30 seconds)
- Architecture (arm64)
- MongoDB connection parameters
- Identical codebase and build flags

Any deviation may invalidate benchmarking results.
