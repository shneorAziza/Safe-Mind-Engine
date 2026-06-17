from openai import OpenAI

from safe_mind.core.config import settings


def main() -> None:
    print(
        {
            "configured_provider": settings.emotional_filter_provider,
            "has_api_key": bool(settings.openai_api_key),
            "model": settings.openai_emotional_filter_model,
        }
    )

    client = OpenAI(api_key=settings.openai_api_key)
    try:
        response = client.chat.completions.create(
            model=settings.openai_emotional_filter_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Return JSON only."},
                {"role": "user", "content": 'Return {"ok": true}'},
            ],
        )
        print({"ok": True, "content": response.choices[0].message.content})
    except Exception as exc:
        print({"ok": False, "error_type": type(exc).__name__, "error": str(exc)[:800]})


if __name__ == "__main__":
    main()
