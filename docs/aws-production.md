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
  -> WhatsApp alert via local app user DB
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
  -> WhatsApp alert via local app user DB
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
- OpenAI API key for `gpt-4o-mini`.
- Meta WhatsApp access token, phone number ID, approved parent-alert template, approved auth-code template, and template language.

Current model decision: keep OpenAI `gpt-4o-mini` for production. Bedrock support
exists in code only as an optional future provider and is not used by the current
Lambda templates.

Current pilot note, 2026-07-09: local WhatsApp sending works through Meta. The approved templates currently configured are `safe_mind_parent_alert / APPROVED / he / MARKETING` and `safe_mind_auth_code / APPROVED / he / AUTHENTICATION`.

## Required Secrets

Create these in AWS Secrets Manager:

```text
safe-mind/prod/mongodb-uri
safe-mind/prod/openai-api-key
safe-mind/prod/eval-auth-password
safe-mind/prod/integration-api-token
safe-mind/prod/whatsapp-access-token
safe-mind/prod/whatsapp-phone-number-id
safe-mind/prod/whatsapp-template-name
safe-mind/prod/whatsapp-template-language
safe-mind/prod/whatsapp-verification-template-name
safe-mind/prod/whatsapp-verification-template-language
```

The ECS task definitions in `deploy/aws/` reference these names.

## Required Environment Variables

Non-secret task environment:

```text
SAFE_MIND_ENV=production
SAFE_MIND_SIGNAL_STORE_PROVIDER=mongodb
SAFE_MIND_MONGODB_DATABASE=safe_mind
SAFE_MIND_EMOTIONAL_FILTER_PROVIDER=openai
SAFE_MIND_OPENAI_EMOTIONAL_FILTER_MODEL=gpt-4o-mini
SAFE_MIND_PSYCHOLOGICAL_ANALYZER_PROVIDER=openai
SAFE_MIND_OPENAI_PSYCHOLOGICAL_ANALYZER_MODEL=gpt-4o-mini
SAFE_MIND_ENABLE_EMBEDDINGS=false
SAFE_MIND_ENABLE_EVAL_UI=true
SAFE_MIND_PERSIST_SIGNALS=true
SAFE_MIND_EVAL_AUTH_USERNAME=safemind
```

Secret-backed task environment:

```text
SAFE_MIND_MONGODB_URI
OPENAI_API_KEY
SAFE_MIND_EVAL_AUTH_PASSWORD
SAFE_MIND_INTEGRATION_API_TOKEN
SAFE_MIND_WHATSAPP_ACCESS_TOKEN
SAFE_MIND_WHATSAPP_PHONE_NUMBER_ID
SAFE_MIND_WHATSAPP_TEMPLATE_NAME
SAFE_MIND_WHATSAPP_TEMPLATE_LANGUAGE
SAFE_MIND_WHATSAPP_VERIFICATION_TEMPLATE_NAME
SAFE_MIND_WHATSAPP_VERIFICATION_TEMPLATE_LANGUAGE
```

The app now fails closed in production if any required secret is missing. The API Lambda exposes the internal Eval dashboard for the team and requires Basic Auth.

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
- `deploy/aws/bedrock-invoke-policy.json`: optional IAM policy snippet if Bedrock is enabled later.
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

## Current Step-By-Step Deployment Handoff

The user is learning AWS and wants to proceed one completed step at a time. As of 2026-07-12, the first API Lambda deployment is live behind API Gateway HTTP API.

Completed:

- Docker Desktop is installed/open.
- AWS CLI v2 is installed locally.
- Root AWS Console login works.
- Root MFA was completed.
- AWS CLI profile `safe-mind-deploy` is configured in `us-east-1`.
- IAM user `safe-mind-deploy` exists for deployment CLI access.
- ECR repository `safe-mind-api` exists:
  `415019015823.dkr.ecr.us-east-1.amazonaws.com/safe-mind-api`.
- Docker image was built from `Dockerfile.lambda`, rebuilt as `linux/amd64` with `--provenance=false`, pushed as `latest`, and verified as `application/vnd.docker.distribution.manifest.v2+json`.
- IAM role `safe-mind-lambda-role` exists.
- Lambda function `safe-mind-api` exists with `1024 MB` memory and `900 seconds` timeout.
- Production Lambda env vars were added directly on the Lambda. Explicit non-secret values are intentionally minimal:
  - `SAFE_MIND_ENV=production`
  - `SAFE_MIND_SIGNAL_STORE_PROVIDER=mongodb`
  - `SAFE_MIND_ENABLE_EVAL_UI=true`
  - `SAFE_MIND_EVAL_AUTH_USERNAME=safemind`
  - `SAFE_MIND_WHATSAPP_TEMPLATE_NAME=safe_mind_parent_alert`
- Production Lambda secret env vars are:
  - `SAFE_MIND_MONGODB_URI`
  - `OPENAI_API_KEY`
  - `SAFE_MIND_EVAL_AUTH_PASSWORD`
  - `SAFE_MIND_INTEGRATION_API_TOKEN`
  - `SAFE_MIND_WHATSAPP_ACCESS_TOKEN`
  - `SAFE_MIND_WHATSAPP_PHONE_NUMBER_ID`
- Lambda test events and public URL checks passed:
  - `GET /health/live` returned `200`.
  - `GET /health/ready` returned `200` with MongoDB storage `ok`.
- A Lambda Function URL was created and worked for health checks, but it remapped `WWW-Authenticate` to `x-amzn-Remapped-www-authenticate`; browser login prompts for `/eval` did not open reliably.
- API Gateway HTTP API was created and is the public production API base URL:
  `https://qi86pazbij.execute-api.us-east-1.amazonaws.com`.
- `/eval` is enabled for the team and protected by Basic Auth. PowerShell auth testing with the configured eval password returned `200`.
- Bedrock was discussed and rejected as the active model path because the user
  wants to keep the exact existing model, OpenAI `gpt-4o-mini`.
- Large Eval datasets now run as async jobs. The Eval HTTP request stores a job
  in MongoDB and the API Lambda invokes itself asynchronously to process the
  messages, so the UI can poll progress instead of waiting on one long request.
  The actual `safe-mind-api` execution role
  `safe-mind-api-role-do9hkzoc` must allow `lambda:InvokeFunction` on the
  `safe-mind-api` function. The policy document is stored at
  `deploy/aws/lambda-self-invoke-policy.json`.

Current deploy status, 2026-07-16:

- AWS production is live behind API Gateway HTTP API.
- The latest code adds numeric per-message score history to daily signal records
  and displays it compactly in Eval day details.
- Redeployed to `safe-mind-api` Lambda on 2026-07-16.
- ECR/Lambda image digest: `sha256:242de3f2a8e9a63068ad06be55eb80954f14d82798adf8be2486c5c74f127e65`.
- Local verification before redeploy: `74 passed`.
- Production verification after redeploy:
  - `/health/live` returned `ok`.
  - `/health/ready` returned `env=production`, `signal_store_provider=mongodb`, and `storage=ok`.

Current deploy status, 2026-07-19:

- Redeployed to `safe-mind-api` Lambda with Eval simulator message text display
  for per-message score history and Excel export, including in-cell line breaks
  for `M1`, `M2`, and later entries.
- ECR/Lambda image digest: `sha256:887734e5eb614cff23473525127dd83d0c4c73bf8f988b8b970775964fae77af`.
- Local verification before redeploy: `76 passed`.
- Production verification after redeploy:
  - `/health/live` returned `status=ok`.
  - `/health/ready` returned `env=production`, `signal_store_provider=mongodb`, and `storage=ok`.
  - unauthenticated `GET /eval` returned `401`.
  - authenticated Eval page included `Eval message text history` and `mso-data-placement:same-cell` for Excel in-cell line breaks.
  - unauthenticated `GET /eval` returned `401`.

## Redeploy Existing Production Lambda

Use this after local changes are ready to go live:

```powershell
aws ecr get-login-password --region us-east-1 --profile safe-mind-deploy `
  | docker login --username AWS --password-stdin 415019015823.dkr.ecr.us-east-1.amazonaws.com

docker buildx build --platform linux/amd64 --provenance=false `
  -f Dockerfile.lambda `
  -t safe-mind-api:latest .

docker tag safe-mind-api:latest 415019015823.dkr.ecr.us-east-1.amazonaws.com/safe-mind-api:latest
docker push 415019015823.dkr.ecr.us-east-1.amazonaws.com/safe-mind-api:latest

aws lambda update-function-code `
  --function-name safe-mind-api `
  --image-uri 415019015823.dkr.ecr.us-east-1.amazonaws.com/safe-mind-api:latest `
  --region us-east-1 `
  --profile safe-mind-deploy
```

Verify after deployment:

```powershell
curl https://qi86pazbij.execute-api.us-east-1.amazonaws.com/health/live
curl https://qi86pazbij.execute-api.us-east-1.amazonaws.com/health/ready
```

If Dataset Simulation returns `Could not start async Eval job`, add self-invoke
permission to the Lambda role:

```powershell
aws iam put-role-policy `
  --role-name safe-mind-api-role-do9hkzoc `
  --policy-name safe-mind-api-self-invoke `
  --policy-document file://deploy/aws/lambda-self-invoke-policy.json `
  --region us-east-1 `
  --profile safe-mind-deploy
```

Next step:

1. Send the frontend engineer the API base URL:
   `https://qi86pazbij.execute-api.us-east-1.amazonaws.com`.
2. Do not send `SAFE_MIND_INTEGRATION_API_TOKEN` to the Android frontend. The Android app must call `/v1/auth/start`, then `/v1/auth/verify`, store the returned per-user token, and use that token for `/v1/me` and `/v1/app/messages`.
3. Verify the API Gateway URL with the Android/frontend flow:
   - `POST /v1/auth/start`
   - `POST /v1/auth/verify`
   - `GET /v1/me`
   - `POST /v1/app/messages`
4. Later, create the `safe-mind-finalizer` Lambda from the same image, override its image command to `safe_mind.lambda_finalizer.handler`, and schedule it with EventBridge.
5. Reduce `safe-mind-deploy` permissions from broad `AdministratorAccess` after the first deployment is stable.

Token distinction:

- Android/frontend user token: generated by `POST /v1/auth/verify`, stored on the device, and sent as `Authorization: Bearer <token>` to `/v1/me` and `/v1/app/messages`.
- `SAFE_MIND_INTEGRATION_API_TOKEN`: production secret for the legacy/internal backend-to-backend endpoint `POST /v1/integrations/next/messages`; not for client-side Android code.

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
13. Run a frontend-style registration/login test through `/v1/auth/start` and `/v1/auth/verify`.
14. Send a test message batch through `/v1/app/messages` with the returned token and matching `deviceId`.
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
- Whether `/eval` should later be restricted by VPN/IP allowlist/API Gateway policy in addition to Basic Auth.
- Exact finalizer timezone. The code currently finalizes the previous UTC day by default.
- Production WhatsApp template approval and final template language code.
- Secret rotation before production if any development token was shared outside a secret manager.
