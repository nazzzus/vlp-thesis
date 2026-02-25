

# VLP Vehicle Service  
## AWS SAM Deployment (AWS)

---

## 1. Overview

This directory contains the deployment configuration for the **Vehicle Service** of the Vehicle Listing Platform (VLP) using **AWS SAM**.

The service is implemented in **Go (net/http)** and deployed as:

- AWS Lambda (Runtime: `provided.al2023`)
- Architecture: `arm64`
- Memory: 512 MB
- Timeout: 30 seconds
- Region: `eu-central-1`
- API Layer: Amazon API Gateway (REST, Stage: `Prod`)
- Database: External MongoDB (Managed Service)

---

## 2. Prerequisites

- AWS CLI configured (`aws configure`)
- AWS SAM CLI installed (`sam`)
- AWS credentials with permissions for:
  - CloudFormation
  - Lambda
  - API Gateway
  - IAM
  - S3
- Compiled Go binary named `bootstrap` available for Lambda (AL2023, arm64)
- Reachable external MongoDB instance

---

## 3. Environment / Parameters

The SAM template expects the following parameters:

- `MongoUri` (required)
- `MongoDatabase` (default: `vlp`)
- `MongoCollection` (default: `vehicles`)

Recommended: reuse the same values as the Serverless deployment to ensure comparable benchmarking.

### Example (shell variables)

```
export MONGO_URI='mongodb+srv://...'
export MONGO_DB='vlp'
export MONGO_COLLECTION='vehicles'
```

---

## 4. Build / Packaging

The template uses `CodeUri: ./build/`. Ensure the directory `./build/` contains the Lambda bootstrap binary:

- `build/bootstrap`

If a SAM build step is used in your workflow:

```
sam build
```

---

## 5. Deployment

Deploy to AWS (Region: `eu-central-1`) with a fixed stack name:

```
sam deploy \
  --stack-name vlp-vehicle-service-sam-prod \
  --region eu-central-1 \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    MongoUri="$MONGO_URI" \
    MongoDatabase="$MONGO_DB" \
    MongoCollection="$MONGO_COLLECTION"
```

After deployment, the API URL can be retrieved via CloudFormation outputs.

---


## 6. API Endpoints (Stage: Prod)

Base URL (from template output `ApiUrl`):

```
https://q39f8p16va.execute-api.eu-central-1.amazonaws.com/Prod
```

Available routes:

- GET     /healthz
- GET     /readyz
- GET     /vehicles
- POST    /vehicles
- GET     /vehicles/{id}
- DELETE  /vehicles/{id}

---

## 7. Retrieve Outputs

```
aws cloudformation describe-stacks \
  --stack-name vlp-vehicle-service-sam-prod \
  --region eu-central-1 \
  --query "Stacks[0].Outputs" \
  --output table
```

---

## 8. Logs

Lambda logs are available in CloudWatch Logs. Example (list log groups):

```
aws logs describe-log-groups --region eu-central-1 --output table
```

---

## 9. Removal (Cleanup)

Remove the SAM stack:

```
sam delete --stack-name vlp-vehicle-service-sam-prod --region eu-central-1
```

If `sam delete` is not available/desired, delete via CloudFormation:

```
aws cloudformation delete-stack --stack-name vlp-vehicle-service-sam-prod --region eu-central-1
```

---

## 10. Reproducibility Requirements

For valid and comparable performance testing, keep the following parameters constant across deployments:

- AWS region
- Memory allocation
- Timeout configuration
- Architecture (arm64)
- MongoDB connection parameters
- Identical codebase and API contract

Any deviation may invalidate benchmarking results.


## https://q39f8p16va.execute-api.eu-central-1.amazonaws.com/Prod
