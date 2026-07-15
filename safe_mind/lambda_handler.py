from mangum import Mangum

from safe_mind.main import app


asgi_handler = Mangum(app, lifespan="auto")


def handler(event, context):
    job_id = event.get("safe_mind_eval_dataset_job_id") if isinstance(event, dict) else None
    if job_id:
        from safe_mind.api.eval_ui import process_eval_dataset_job

        return process_eval_dataset_job(str(job_id))
    return asgi_handler(event, context)
