import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen


TEMPLATE_NAME = "safe_mind_auth_code"
TEMPLATE_LANGUAGE = "he"


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
    waba_id = os.environ.get("SAFE_MIND_WHATSAPP_BUSINESS_ACCOUNT_ID")
    if not token:
        raise SystemExit("Missing SAFE_MIND_WHATSAPP_ACCESS_TOKEN")
    if not waba_id:
        raise SystemExit("Missing SAFE_MIND_WHATSAPP_BUSINESS_ACCOUNT_ID")

    payload = {
        "name": os.environ.get("SAFE_MIND_WHATSAPP_VERIFICATION_TEMPLATE_NAME", TEMPLATE_NAME),
        "category": "AUTHENTICATION",
        "language": os.environ.get("SAFE_MIND_WHATSAPP_VERIFICATION_TEMPLATE_LANGUAGE", TEMPLATE_LANGUAGE),
        "components": [
            {
                "type": "BODY",
                "add_security_recommendation": True,
            },
            {
                "type": "FOOTER",
                "code_expiration_minutes": 10,
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "OTP",
                        "otp_type": "COPY_CODE",
                    }
                ],
            },
        ],
    }
    request = Request(
        f"https://graph.facebook.com/{graph_version}/{waba_id}/message_templates",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            print(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {detail}") from exc


if __name__ == "__main__":
    main()
