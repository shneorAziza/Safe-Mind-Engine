import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from pydantic import BaseModel

from safe_mind.core.config import settings
from safe_mind.core.metrics import metrics, timer


class ParentContact(BaseModel):
    uid: str
    parent_phone: str


class ParentContactResult(BaseModel):
    found: bool
    skipped: bool = False
    contact: ParentContact | None = None
    status_code: int | None = None
    error: str | None = None


def fetch_parent_contact(
    *,
    uid: str,
    url_template: str | None = None,
    token: str | None = None,
) -> ParentContactResult:
    resolved_template = url_template if url_template is not None else settings.parent_contact_url_template
    resolved_token = token if token is not None else settings.parent_contact_token
    if not resolved_template:
        metrics.increment("parent_contact.skipped")
        return ParentContactResult(found=False, skipped=True, error="parent_contact_url_not_configured")

    url = resolved_template.format(uid=quote(uid, safe=""))
    headers = {"Accept": "application/json"}
    if resolved_token:
        headers["Authorization"] = f"Bearer {resolved_token}"

    request = Request(url, headers=headers, method="GET")
    metrics.increment("parent_contact.requests.total")
    try:
        with timer("parent_contact.duration"):
            with urlopen(request, timeout=15) as response:
                status_code = int(response.status)
                payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        metrics.increment("parent_contact.failed")
        return ParentContactResult(found=False, status_code=exc.code, error=str(exc))
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        metrics.increment("parent_contact.failed")
        return ParentContactResult(found=False, error=str(exc))

    parent_phone = payload.get("parentPhone")
    if status_code >= 400 or not isinstance(parent_phone, str) or not parent_phone.strip():
        metrics.increment("parent_contact.failed")
        return ParentContactResult(
            found=False,
            status_code=status_code,
            error="parent_phone_missing",
        )

    metrics.increment("parent_contact.found")
    return ParentContactResult(
        found=True,
        status_code=status_code,
        contact=ParentContact(uid=uid, parent_phone=parent_phone.strip()),
    )
