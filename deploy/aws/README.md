# SafeMind AWS Production Prep

This folder contains templates for the first AWS production deployment.

If the deployment target is Lambda, use:

- Amazon ECR stores the SafeMind Lambda container image.
- AWS Lambda runs the FastAPI API through `safe_mind.lambda_handler.handler`.
- Lambda Function URL or API Gateway exposes HTTPS traffic.
- EventBridge Scheduler invokes `safe_mind.lambda_finalizer.handler`.
- AWS Secrets Manager stores runtime secrets.
- MongoDB Atlas remains the production signal database.

The ECS/Fargate alternative remains available:

- Amazon ECR stores the SafeMind container image.
- Amazon ECS on AWS Fargate runs the FastAPI API container.
- An Application Load Balancer exposes HTTPS traffic to ECS.
- AWS Secrets Manager stores runtime secrets.
- Amazon CloudWatch Logs receives API and finalizer logs.
- Amazon EventBridge Scheduler runs the daily finalizer as a separate ECS task.
- MongoDB Atlas remains the production signal database.

These files are templates. Replace:

- `<account-id>`
- `<region>`
- `<image-tag>`
- role ARNs
- subnet/security-group values when creating the ECS service and scheduler target

Do not commit filled secret values.

## Files

- `ecs-task-definition.api.json`: long-running API task definition.
- `ecs-task-definition.finalizer.json`: one-shot daily finalization task definition.
- `lambda-api-function.template.json`: Lambda API function template.
- `lambda-finalizer-function.template.json`: Lambda finalizer function template.

## Daily Finalizer

The finalizer task runs:

```text
python scripts/finalize_previous_day.py --send-alerts
```

Schedule it for `00:05` in the timezone you want to treat as the closed-day boundary.
The current backend computes the previous day in UTC unless `--run-at` or `--target-day`
is explicitly provided.
