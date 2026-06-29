import json
import os
from urllib.request import Request, urlopen


def _load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)


def main() -> None:
    _load_dotenv()
    token = os.environ.get("SAFE_MIND_WHATSAPP_ACCESS_TOKEN")
    graph_version = os.environ.get("SAFE_MIND_WHATSAPP_GRAPH_API_VERSION", "v23.0")
    waba_id = os.environ.get("SAFE_MIND_WHATSAPP_BUSINESS_ACCOUNT_ID") or "401869746351023"
    if not token:
        raise SystemExit("Missing SAFE_MIND_WHATSAPP_ACCESS_TOKEN")

    url = (
        f"https://graph.facebook.com/{graph_version}/{waba_id}/message_templates"
        "?fields=name,status,language,category"
    )
    request = Request(url, headers={"Authorization": f"Bearer {token}"})
    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))

    templates = payload.get("data", [])
    print(f"TEMPLATE_COUNT={len(templates)}")
    for template in templates:
        print(
            " / ".join(
                str(template.get(field, ""))
                for field in ("name", "status", "language", "category")
            )
        )


if __name__ == "__main__":
    main()
