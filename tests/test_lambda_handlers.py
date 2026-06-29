from datetime import date

import safe_mind.lambda_finalizer as lambda_finalizer


def test_lambda_finalizer_uses_event_time_and_sends_alerts(monkeypatch) -> None:
    calls = []

    class Summary:
        def model_dump(self, *, mode: str) -> dict:
            calls.append(("model_dump", mode))
            return {"target_day": "2026-08-20", "alerts_to_send": 1}

    def fake_run_daily_finalization(*, target_day, run_at, send_alerts):
        calls.append((target_day, run_at.isoformat(), send_alerts))
        return Summary()

    monkeypatch.setattr(lambda_finalizer, "run_daily_finalization", fake_run_daily_finalization)

    result = lambda_finalizer.handler({"time": "2026-08-21T00:05:00Z"}, object())

    assert result == {"target_day": "2026-08-20", "alerts_to_send": 1}
    assert calls[0] == (None, "2026-08-21T00:05:00+00:00", True)
    assert calls[1] == ("model_dump", "json")


def test_lambda_finalizer_accepts_explicit_target_day(monkeypatch) -> None:
    calls = []

    class Summary:
        def model_dump(self, *, mode: str) -> dict:
            return {"target_day": "2026-08-15"}

    def fake_run_daily_finalization(*, target_day, run_at, send_alerts):
        calls.append((target_day, run_at, send_alerts))
        return Summary()

    monkeypatch.setattr(lambda_finalizer, "run_daily_finalization", fake_run_daily_finalization)

    result = lambda_finalizer.handler({"target_day": "2026-08-15", "send_alerts": False}, object())

    assert result == {"target_day": "2026-08-15"}
    assert calls == [(date(2026, 8, 15), None, False)]
