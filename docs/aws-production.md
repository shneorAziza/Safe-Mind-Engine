# AWS Production Runbook

This runbook prepares SafeMind for a first production deployment on AWS.

## Recommended AWS Architecture

Preferred first option if the requirement is "AWS Lambda":

```text
Internet
  -> Lambda Function URL or API Gateway HTTP API
  -> Lambda container image
  -> safe_mind.lambda_handler.handler
  -> MongoDB Atlas
  -> OpenAI API

EventBridge Scheduler
  -> Lambda safe-mind-finalizer
  -> safe_mind.lambda_finalizer.handler
  -> WhatsApp alert via parent contact lookup
```

Alternative if you later want a constantly warm web service:

```text
Internet
  -> Application Load Balancer
  -> ECS service on Fargate
  -> SafeMind FastAPI container
  -> MongoDB Atlas
  -> OpenAI API

EventBridge Scheduler
  -> ECS RunTask
  -> python scripts/finalize_previous_day.py --send-alerts
  -> WhatsApp alert via parent contact lookup
```

Why Lambda can work here:

- No server management.
- No load balancer is required if using a Lambda Function URL.
- The daily finalizer maps naturally to EventBridge Scheduler.
- Container image packaging keeps the app close to the ECS setup.

Why ECS/Fargate may still be better later:

- Fewer cold-start surprises for a user-facing dashboard/API.
- Standard HTTP health checks through an Application Load Balancer.
- Easier long-lived connection behavior if the product grows.

## Production Prerequisites

AWS:

- AWS account with MFA enabled on the root user.
- IAM admin user or IAM Identity Center user for day-to-day work.
- AWS CLI installed locally.
- Docker Desktop installed locally.
- One AWS region selected, for example `us-east-1` or a region close to users.

External services:

- MongoDB Atlas connection string.
- OpenAI API key.
- Firebase/Next backend parent contact lookup URL and shared internal token.
- Meta WhatsApp access token, phone number ID, approved template name, and template language.

Current pilot note, 2026-06-30: local WhatsApp sending works through Meta. The approved template currently configured is `safe_mind_parent_alert / APPROVED / he / MARKETING`.

## Required Secrets

Create these in AWS Secrets Manager:

```text
safe-mind/prod/mongodb-uri
safe-mind/prod/openai-api-key
safe-mind/prod/eval-auth-password
safe-mind/prod/integration-api-token
safe-mind/prod/parent-contact-url-template
safe-mind/prod/parent-contact-token
safe-mind/prod/whatsapp-access-token
safe-mind/prod/whatsapp-phone-number-id
safe-mind/prod/whatsapp-template-name
safe-mind/prod/whatsapp-template-language
```

The ECS task definitions in `deploy/aws/` reference these names.

## Required Environment Variables

Non-secret task environment:

```text
SAFE_MIND_ENV=production
SAFE_MIND_SIGNAL_STORE_PROVIDER=mongodb
SAFE_MIND_MONGODB_DATABASE=safe_mind
SAFE_MIND_PSYCHOLOGICAL_ANALYZER_PROVIDER=openai
SAFE_MIND_OPENAI_PSYCHOLOGICAL_ANALYZER_MODEL=gpt-4o-mini
SAFE_MIND_ENABLE_EMBEDDINGS=false
SAFE_MIND_PERSIST_SIGNALS=true
SAFE_MIND_EVAL_AUTH_USERNAME=safemind
```

Secret-backed task environment:

```text
SAFE_MIND_MONGODB_URI
OPENAI_API_KEY
SAFE_MIND_EVAL_AUTH_PASSWORD
SAFE_MIND_INTEGRATION_API_TOKEN
SAFE_MIND_PARENT_CONTACT_URL_TEMPLATE
SAFE_MIND_PARENT_CONTACT_TOKEN
SAFE_MIND_WHATSAPP_ACCESS_TOKEN
SAFE_MIND_WHATSAPP_PHONE_NUMBER_ID
SAFE_MIND_WHATSAPP_TEMPLATE_NAME
SAFE_MIND_WHATSAPP_TEMPLATE_LANGUAGE
```

The app now fails closed in production if any required secret is missing.

## Local Production Smoke Test

Create `.env.production` from `.env.production.example`, then run:

```powershell
docker compose -f docker-compose.production-smoke.yml up --build
```

Check:

```text
http://127.0.0.1:8000/health/live
http://127.0.0.1:8000/health/ready
```

The ready check needs MongoDB network access and valid secrets.

## Lambda Deployment Files

- `Dockerfile.lambda`: Lambda-compatible container image.
- `safe_mind/lambda_handler.py`: FastAPI adapter for Lambda/API Gateway/Function URL.
- `safe_mind/lambda_finalizer.py`: EventBridge-friendly finalizer handler.
- `deploy/aws/lambda-api-function.template.json`: API Lambda template.
- `deploy/aws/lambda-finalizer-function.template.json`: finalizer Lambda template.

The same image can run both functions. For the finalizer function, override the
image command to:

```text
safe_mind.lambda_finalizer.handler
```

## First AWS Lambda Deployment Steps

We will do these together if Lambda is the required target:

1. Choose AWS region.
2. Create an ECR repository named `safe-mind-api`.
3. Build the Lambda image:
   ```powershell
   docker buildx build --platform linux/amd64 --provenance=false -f Dockerfile.lambda -t safe-mind-api:lambda .
   ```
4. Push the image to ECR.
5. Create Secrets Manager secrets or inject encrypted environment variables.
6. Create IAM role `safe-mind-lambda-role`.
7. Create Lambda function `safe-mind-api` from the container image.
8. Configure environment variables and secrets.
9. Create a Lambda Function URL or API Gateway HTTP API.
10. Verify `/health/live`, `/health/ready`, and Basic Auth on `/eval`.
11. Create Lambda function `safe-mind-finalizer` from the same image.
12. Override its image command to `safe_mind.lambda_finalizer.handler`.
13. Create an EventBridge schedule for daily finalization.

## First AWS ECS Deployment Steps

Use these if we choose ECS/Fargate instead of Lambda:

1. Choose AWS region.
2. Create an ECR repository named `safe-mind-api`.
3. Build and push the Docker image to ECR.
4. Create CloudWatch log groups:
   - `/ecs/safe-mind-api`
   - `/ecs/safe-mind-finalizer`
5. Create Secrets Manager secrets.
6. Create IAM roles:
   - `safe-mind-ecs-task-execution-role`
   - `safe-mind-ecs-task-role`
7. Create ECS cluster.
8. Register API task definition.
9. Create ECS service on Fargate behind an Application Load Balancer.
10. Verify:
    - `/health/live`
    - `/health/ready`
    - `/eval` requires Basic Auth
11. Register finalizer task definition.
12. Create EventBridge Scheduler rule for the finalizer.
13. Send a test ingestion request from the Firebase/Next backend.
14. Confirm `users/{uid}` in Firestore contains a test `parentPhone`.
15. Run the finalizer with `--send-alerts` and confirm it creates alert decisions and WhatsApp sends.

## Cost Controls For The First Week

- Start with one ECS task.
- Use small Fargate sizing: API `0.5 vCPU / 1 GB`, finalizer `0.25 vCPU / 0.5 GB`.
- Keep CloudWatch log retention short during pilot, for example 14 days.
- Set an AWS Budget alert before creating the load balancer.
- Do not create NAT Gateways unless we explicitly choose a private-subnet architecture.

## Open Decisions Before Deploy

- Domain name and TLS certificate.
- AWS region.
- Whether MongoDB Atlas allows all AWS outbound IPs or we use a tighter network setup.
- Whether the internal `/eval` dashboard should be exposed publicly behind Basic Auth or restricted further.
- Exact finalizer timezone. The code currently finalizes the previous UTC day by default.
- Production WhatsApp template approval and final template language code.
- Secret rotation before production if any development token was shared outside a secret manager.
