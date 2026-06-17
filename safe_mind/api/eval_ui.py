from datetime import UTC, date, datetime, time, timedelta
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from safe_mind.alerts.engine import build_alert_timeline
from safe_mind.alerts.models import AlertTimelineDay
from safe_mind.api.eval_ui_react import EVAL_HTML as REACT_EVAL_HTML
from safe_mind.core.config import settings
from safe_mind.pipeline import process_message
from safe_mind.schemas.ingestion import IngestMessageRequest
from safe_mind.storage.models import StoredSignal
from safe_mind.storage.vector_store import SQLiteVectorStore

router = APIRouter(tags=["eval-ui"])


class EvalRuntimeInfo(BaseModel):
    emotional_filter_provider: str
    emotional_filter_model: str | None = None
    psychological_analyzer_provider: str
    psychological_analyzer_model: str | None = None
    embedding_provider: str | None = None
    embedding_model: str | None = None
    strict_model_eval: bool = True


class EvalRunRequest(BaseModel):
    messages: list[str] = Field(min_length=1)
    persist: bool = False
    create_vector: bool = True
    source_app: str = "eval-ui"
    locale: str | None = "he"
    child_user_id: UUID | None = None
    start_day: date | None = None
    one_message_per_day: bool = False


class EvalRunResponse(BaseModel):
    count: int
    child_user_id: UUID
    runtime: EvalRuntimeInfo
    results: list[dict]


class EvalAlertUsersResponse(BaseModel):
    users: list[UUID]


class EvalAlertTimelineResponse(BaseModel):
    child_user_id: UUID
    start_day: date
    end_day: date
    days: list[AlertTimelineDay]


@router.get("/eval", response_class=HTMLResponse)
def eval_page() -> str:
    return REACT_EVAL_HTML


@router.post("/eval/run", response_model=EvalRunResponse)
def run_eval(payload: EvalRunRequest) -> EvalRunResponse:
    results = []
    child_user_id = payload.child_user_id or uuid4()
    start_day = payload.start_day or datetime.now(UTC).date()
    for index, message in enumerate(payload.messages):
        occurred_at = datetime.now(UTC)
        if payload.one_message_per_day:
            occurred_at = datetime.combine(start_day + timedelta(days=index), time(12), tzinfo=UTC)
        request = IngestMessageRequest(
            event_id=uuid4(),
            child_user_id=child_user_id,
            device_id=uuid4(),
            occurred_at=occurred_at,
            source_type="manual",
            source_app=payload.source_app,
            text=message,
            locale=payload.locale,
        )
        result = process_message(
            request,
            debug=True,
            persist=payload.persist,
            create_vector=payload.create_vector,
            allow_model_fallback=False,
        )
        results.append(
            {
                "event_id": str(request.event_id),
                "status": _status(result.stored_signal),
                "stored_signal": result.stored_signal.model_dump(),
                "logs": [entry.model_dump() for entry in result.logs],
            }
        )

    return EvalRunResponse(
        count=len(results),
        child_user_id=child_user_id,
        runtime=_runtime_info(),
        results=results,
    )


@router.get("/eval/alerts/users", response_model=EvalAlertUsersResponse)
def list_eval_alert_users() -> EvalAlertUsersResponse:
    store = SQLiteVectorStore(settings.vector_db_path)
    store.initialize()
    return EvalAlertUsersResponse(users=store.list_child_user_ids())


@router.get("/eval/alerts/timeline", response_model=EvalAlertTimelineResponse)
def get_eval_alert_timeline(
    child_user_id: UUID,
    start_day: date | None = None,
    days: int = 30,
) -> EvalAlertTimelineResponse:
    store = SQLiteVectorStore(settings.vector_db_path)
    store.initialize()
    records = store.list_signal_vectors_for_child(child_user_id)
    if records:
        latest_day = records[-1].occurred_at.date()
        resolved_days = max(days, 1)
        resolved_start_day = start_day or (latest_day - timedelta(days=resolved_days - 1))
    else:
        resolved_start_day = start_day or datetime.now(UTC).date()
        resolved_days = max(days, 1)
    end_day = resolved_start_day + timedelta(days=resolved_days - 1)
    timeline = build_alert_timeline(
        child_user_id=child_user_id,
        records=records,
        start_day=resolved_start_day,
        end_day=end_day,
        previous_alert_days=store.list_parent_alert_days_for_child(child_user_id),
    )
    return EvalAlertTimelineResponse(
        child_user_id=child_user_id,
        start_day=resolved_start_day,
        end_day=end_day,
        days=timeline,
    )


def _status(stored_signal: StoredSignal) -> Literal["stored", "preview", "no_vector"]:
    if stored_signal.stored:
        return "stored"
    if stored_signal.embedding_model:
        return "preview"
    return "no_vector"


def _runtime_info() -> EvalRuntimeInfo:
    return EvalRuntimeInfo(
        emotional_filter_provider=settings.emotional_filter_provider,
        emotional_filter_model=settings.openai_emotional_filter_model
        if settings.emotional_filter_provider == "openai"
        else None,
        psychological_analyzer_provider=settings.psychological_analyzer_provider,
        psychological_analyzer_model=settings.openai_psychological_analyzer_model
        if settings.psychological_analyzer_provider == "openai"
        else None,
        embedding_provider="openai" if settings.openai_api_key else None,
        embedding_model=settings.openai_embedding_model if settings.openai_api_key else None,
        strict_model_eval=True,
    )


EVAL_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SafeMind Pipeline Eval</title>
  <style>
    :root {
      --bg: #f5f6f8;
      --panel: #ffffff;
      --text: #17202a;
      --muted: #667085;
      --line: #d7dce2;
      --accent: #226f54;
      --danger: #a5282c;
      --code: #101828;
    }
    * { box-sizing: border-box; }
    html, body { height: 100%; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, sans-serif;
      line-height: 1.4;
      overflow: hidden;
    }
    header {
      height: 72px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      padding: 10px 18px;
    }
    h1 {
      font-size: 21px;
      margin: 0 0 4px;
      letter-spacing: 0;
    }
    .sub {
      color: var(--muted);
      font-size: 13px;
    }
    main {
      height: calc(100vh - 72px);
      display: grid;
      grid-template-columns: minmax(300px, 370px) minmax(0, 1fr);
      gap: 12px;
      padding: 12px;
      max-width: 1600px;
      margin: 0 auto;
    }
    .panel,
    .results-wrap {
      min-height: 0;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    .panel {
      padding: 12px;
      overflow: auto;
    }
    .results-wrap {
      padding: 12px;
      overflow: auto;
    }
    label {
      display: block;
      font-weight: 700;
      margin-bottom: 6px;
    }
    .section-title {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin: 2px 0 10px;
    }
    .section-title h2 {
      margin: 0;
      font-size: 16px;
      letter-spacing: 0;
    }
    .help {
      color: var(--muted);
      font-size: 12px;
      margin-top: -4px;
    }
    .guide {
      border: 1px solid #b7dfcf;
      border-radius: 8px;
      background: #f0fbf6;
      color: #164b37;
      padding: 9px;
      font-size: 12px;
      line-height: 1.45;
    }
    .guide strong {
      display: block;
      color: #0f3326;
      margin-bottom: 3px;
    }
    textarea {
      width: 100%;
      min-height: 210px;
      max-height: 42vh;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      font-family: Arial, sans-serif;
      font-size: 14px;
      line-height: 1.5;
      direction: rtl;
    }
    input[type="text"],
    input[type="date"],
    input[type="number"],
    select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 10px;
      font-size: 14px;
      background: #fff;
      color: var(--text);
    }
    .field {
      display: grid;
      gap: 5px;
    }
    .field span {
      color: var(--muted);
      font-size: 11px;
      font-weight: 700;
    }
    .inline-grid {
      display: grid;
      grid-template-columns: 1fr 96px;
      gap: 8px;
    }
    .divider {
      height: 1px;
      background: var(--line);
      margin: 12px 0;
    }
    .controls {
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }
    .control-group {
      display: grid;
      gap: 9px;
    }
    .check {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 400;
      line-height: 1.25;
    }
    .check input {
      width: 18px;
      height: 18px;
      flex: 0 0 auto;
    }
    button {
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: white;
      padding: 10px 14px;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
      width: 100%;
    }
    .secondary-btn {
      background: #344054;
    }
    .ghost-btn {
      background: #ffffff;
      color: var(--text);
      border: 1px solid var(--line);
    }
    button:disabled {
      opacity: 0.55;
      cursor: wait;
    }
    .summary {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 10px;
    }
    .dashboard {
      display: grid;
      gap: 10px;
      margin-bottom: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fbfcfd;
    }
    .dashboard-head {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: flex-start;
    }
    .dashboard h2 {
      margin: 0;
      font-size: 16px;
      letter-spacing: 0;
    }
    .metric-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(130px, 1fr));
      gap: 8px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 8px;
    }
    .metric-label {
      color: var(--muted);
      font-size: 11px;
      font-weight: 700;
      margin-bottom: 3px;
    }
    .metric-value {
      font-size: 20px;
      font-weight: 700;
    }
    .timeline-table-wrap {
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 860px;
      font-size: 12px;
    }
    th,
    td {
      border-bottom: 1px solid var(--line);
      padding: 7px 8px;
      text-align: left;
      white-space: nowrap;
    }
    th {
      position: sticky;
      top: 0;
      background: #f8fafb;
      z-index: 1;
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
    }
    tr:last-child td { border-bottom: 0; }
    .day-baseline { background: #f3f7ff; }
    .day-deviation { background: #fff7ed; }
    .day-push { background: #fff0f1; }
    .badge {
      display: inline-flex;
      align-items: center;
      min-height: 22px;
      border-radius: 999px;
      padding: 2px 8px;
      border: 1px solid var(--line);
      background: #fff;
      font-weight: 700;
      font-size: 11px;
    }
    .badge-ok { color: #226f54; border-color: #b7dfcf; background: #f0fbf6; }
    .badge-warn { color: #945b00; border-color: #f2cf8f; background: #fff8e8; }
    .badge-alert { color: var(--danger); border-color: #efb4b8; background: #fff5f5; }
    .pill {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 9px;
      background: #fff;
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }
    .flow {
      display: grid;
      gap: 12px;
    }
    .flow-arrow {
      color: var(--muted);
      text-align: center;
      font-size: 18px;
      margin: -3px 0;
    }
    .stage {
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: #fff;
    }
    .stage-title {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: center;
      padding: 8px 10px;
      background: #f8fafb;
      border-bottom: 1px solid var(--line);
      font-weight: 700;
      font-size: 13px;
    }
    .stage-body {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 8px;
      padding: 8px;
    }
    .message-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      overflow: hidden;
      min-width: 0;
    }
    .message-card-head {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: center;
      padding: 7px 9px;
      background: #fbfcfd;
      border-bottom: 1px solid var(--line);
      font-size: 12px;
      font-weight: 700;
    }
    .message-card-body {
      display: grid;
      gap: 8px;
      padding: 8px;
    }
    .message-card-body.split {
      grid-template-columns: 1fr 1fr;
    }
    .message-text {
      direction: rtl;
      text-align: right;
      color: var(--text);
      background: #f8fafb;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px;
      font-size: 13px;
    }
    .box-title {
      color: var(--muted);
      font-size: 11px;
      margin-bottom: 4px;
      font-weight: 700;
    }
    pre {
      margin: 0;
      overflow: auto;
      max-height: 260px;
      background: var(--code);
      color: #f2f4f7;
      border-radius: 6px;
      padding: 8px;
      direction: ltr;
      text-align: left;
      font-size: 11px;
      line-height: 1.45;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .empty {
      border: 1px dashed var(--line);
      border-radius: 8px;
      padding: 28px;
      color: var(--muted);
      text-align: center;
      background: #fff;
    }
    .error {
      color: var(--danger);
      margin-top: 8px;
      font-weight: 700;
      font-size: 13px;
      white-space: pre-wrap;
      direction: ltr;
      text-align: left;
    }
    @media (max-width: 900px) {
      body { overflow: auto; }
      main {
        height: auto;
        grid-template-columns: 1fr;
      }
      .message-card-body.split { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>SafeMind Pipeline Eval</h1>
    <div class="sub">Internal stage-by-stage funnel. One line equals one message. Eval runs use the real configured models with no silent heuristic fallback.</div>
  </header>
  <main>
    <section class="panel">
      <div class="controls">
        <div class="control-group">
          <div class="section-title">
            <h2>Alert Dashboard</h2>
          </div>
          <div class="guide">
            <strong>How to monitor</strong>
            Current test user is synthetic but stored in the real local DB. Choose the user, keep Timeline start empty, and load the last 30 days.
          </div>
          <div class="field">
            <span>Known users in local DB</span>
            <select id="knownUsers">
              <option value="">No user selected</option>
            </select>
          </div>
          <div class="field">
            <span>Child user ID</span>
            <input id="childUserId" type="text" placeholder="Paste or select a user ID">
          </div>
          <div class="inline-grid">
            <div class="field">
              <span>Timeline start (optional)</span>
              <input id="startDay" type="date">
            </div>
            <div class="field">
              <span>Days</span>
              <input id="timelineDays" type="number" min="1" max="90" value="30">
            </div>
          </div>
          <button id="timelineBtn" type="button">Load Dashboard</button>
        </div>
        <div class="divider"></div>
        <div class="control-group">
          <div class="section-title">
            <h2>Pipeline Simulation</h2>
          </div>
          <div class="help">Use this to run the real pipeline on test messages and optionally persist them into the local DB.</div>
          <label for="messages">Messages</label>
          <textarea id="messages">אני ממש לחוץ מהמבחן מחר ולא מצליח להירדם
תסביר לי איך פותרים משוואה ריבועית בצורה פשוטה
כולם בכיתה מתעלמים ממני ואני מרגיש לבד כל הזמן</textarea>
          <label class="check">
            <input id="oneMessagePerDay" type="checkbox">
            One message line = next calendar day
          </label>
          <label class="check">
            <input id="createVector" type="checkbox" checked>
            Create real embedding/vector preview
          </label>
          <label class="check">
            <input id="persist" type="checkbox">
            Persist to local DB
          </label>
          <button id="runBtn" class="secondary-btn" type="button">Run Live Pipeline</button>
        </div>
        <div id="error" class="error"></div>
      </div>
    </section>
    <section class="results-wrap">
      <div id="summary" class="summary"></div>
      <div id="dashboard" class="dashboard">
        <div class="dashboard-head">
          <div>
            <h2>Alert Dashboard</h2>
            <div class="sub">A month-level view of the fixed baseline, daily drift, 3-of-5 gate, and push decisions.</div>
          </div>
          <span id="dashboardRange" class="pill">No user loaded</span>
        </div>
        <div id="dashboardBody" class="empty">Persist a simulation or enter a child user ID, then load the dashboard.</div>
      </div>
      <div id="results" class="empty">No run yet.</div>
    </section>
  </main>
  <script>
    const runBtn = document.getElementById("runBtn");
    const timelineBtn = document.getElementById("timelineBtn");
    const messagesInput = document.getElementById("messages");
    const knownUsersSelect = document.getElementById("knownUsers");
    const childUserIdInput = document.getElementById("childUserId");
    const startDayInput = document.getElementById("startDay");
    const timelineDaysInput = document.getElementById("timelineDays");
    const oneMessagePerDayInput = document.getElementById("oneMessagePerDay");
    const createVectorInput = document.getElementById("createVector");
    const persistInput = document.getElementById("persist");
    const resultsEl = document.getElementById("results");
    const summaryEl = document.getElementById("summary");
    const dashboardEl = document.getElementById("dashboardBody");
    const dashboardRangeEl = document.getElementById("dashboardRange");
    const errorEl = document.getElementById("error");
    const seededSyntheticUserId = "55555555-6666-4777-8888-999999999999";

    startDayInput.value = "";

    async function loadKnownUsers(selectedUserId = "") {
      try {
        const response = await fetch("/eval/alerts/users");
        if (!response.ok) return;
        const data = await response.json();
        const current = selectedUserId || childUserIdInput.value.trim() || seededSyntheticUserId;
        knownUsersSelect.innerHTML = `<option value="">No user selected</option>` +
          data.users.map((userId) => `<option value="${escapeHtml(userId)}">${escapeHtml(userId)}</option>`).join("");
        if (current && data.users.includes(current)) {
          knownUsersSelect.value = current;
          childUserIdInput.value = current;
        }
      } catch (_) {
        // The dashboard can still work with a manually pasted user id.
      }
    }

    function pretty(value) {
      return JSON.stringify(value, null, 2);
    }

    function stageLabel(stage) {
      const labels = {
        input: "Raw Messages",
        privacy_redaction: "1. Privacy",
        emotional_filter: "2. Emotional Filter",
        psychological_analyzer: "3. Psychological Analyzer",
        embedding_and_storage: "4. Embedding: Vector + Metadata"
      };
      return labels[stage] || stage;
    }

    function renderSummary(data) {
      const stored = data.results.filter((item) => item.stored_signal.stored).length;
      const preview = data.results.filter((item) => item.status === "preview").length;
      const noVector = data.results.filter((item) => item.status === "no_vector").length;
      const runtime = data.runtime || {};
      summaryEl.innerHTML = [
        ["messages", data.count],
        ["child", data.child_user_id],
        ["stored", stored],
        ["preview", preview],
        ["no vector", noVector],
        ["filter model", runtime.emotional_filter_model || runtime.emotional_filter_provider || "n/a"],
        ["analyzer model", runtime.psychological_analyzer_model || runtime.psychological_analyzer_provider || "n/a"],
        ["embedding model", runtime.embedding_model || runtime.embedding_provider || "n/a"],
      ].map(([label, value]) => `<span class="pill">${label}: ${value}</span>`).join("");
    }

    function renderDashboard(data) {
      childUserIdInput.value = data.child_user_id;
      knownUsersSelect.value = data.child_user_id;
      dashboardRangeEl.textContent = `${data.start_day} to ${data.end_day}`;
      if (!data.days.length) {
        dashboardEl.className = "empty";
        dashboardEl.textContent = "No timeline days.";
        return;
      }
      dashboardEl.className = "";
      const baselineDays = data.days.filter((day) => day.phase === "baseline").length;
      const monitoringDays = data.days.filter((day) => day.phase === "monitoring").length;
      const deviationDays = data.days.filter((day) => day.is_deviation).length;
      const pushDays = data.days.filter((day) => day.should_send_push).length;
      const latestWithBaseline = [...data.days].reverse().find((day) => day.baseline_score !== null);
      const firstPushDay = data.days.find((day) => day.should_send_push);
      const baselineRange = baselineRangeText(data.days);
      dashboardEl.innerHTML = `
        <div class="guide">
          <strong>What you are seeing</strong>
          Baseline period: ${escapeHtml(baselineRange)}. First push in this view: ${escapeHtml(firstPushDay ? firstPushDay.day : "none")}. A push means the 3-of-5 deviation gate was met.
        </div>
        <div class="metric-grid">
          ${metric("Baseline days in view", baselineDays)}
          ${metric("Monitoring days", monitoringDays)}
          ${metric("Deviation days", deviationDays)}
          ${metric("Push decisions", pushDays)}
        </div>
        <div class="metric-grid">
          ${metric("Fixed baseline", formatNumber(latestWithBaseline?.baseline_score))}
          ${metric("Latest score", formatNumber(lastValue(data.days, "daily_score")))}
          ${metric("Latest delta", formatSigned(lastValue(data.days, "delta")))}
          ${metric("Latest 3/5 count", lastValue(data.days, "deviations_in_window") ?? "0")}
        </div>
        <div class="timeline-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Day</th>
                <th>Phase</th>
                <th>Msgs</th>
                <th>Daily</th>
                <th>Baseline</th>
                <th>Delta</th>
                <th>Deviation</th>
                <th>3/5</th>
                <th>Push</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              ${data.days.map(renderTimelineRow).join("")}
            </tbody>
          </table>
        </div>
      `;
    }

    function renderTimelineRow(day) {
      const cls = day.should_send_push ? "day-push" : day.is_deviation ? "day-deviation" : day.phase === "baseline" ? "day-baseline" : "";
      return `
        <tr class="${cls}">
          <td>${escapeHtml(day.day)}</td>
          <td>${phaseBadge(day.phase)}</td>
          <td>${day.message_count}</td>
          <td>${formatNumber(day.daily_score)}</td>
          <td>${formatNumber(day.baseline_score)}</td>
          <td>${formatSigned(day.delta)}</td>
          <td>${day.is_deviation ? badge("yes", "warn") : badge("no", "ok")}</td>
          <td>${day.deviations_in_window}</td>
          <td>${day.should_send_push ? badge("send", "alert") : badge("hold", "ok")}</td>
          <td>${escapeHtml(day.reason)}</td>
        </tr>
      `;
    }

    function metric(label, value) {
      return `<div class="metric"><div class="metric-label">${escapeHtml(label)}</div><div class="metric-value">${escapeHtml(value ?? "n/a")}</div></div>`;
    }

    function baselineRangeText(days) {
      const baselineDays = days.filter((day) => day.phase === "baseline");
      if (!baselineDays.length) return "not visible in current date range";
      return `${baselineDays[0].day} to ${baselineDays[baselineDays.length - 1].day}`;
    }

    function phaseBadge(phase) {
      if (phase === "baseline") return badge("baseline", "ok");
      if (phase === "monitoring") return badge("monitoring", "warn");
      return badge("pre-baseline", "");
    }

    function badge(text, tone) {
      const cls = tone ? ` badge-${tone}` : "";
      return `<span class="badge${cls}">${escapeHtml(text)}</span>`;
    }

    function formatNumber(value) {
      if (value === null || value === undefined) return "n/a";
      return Number(value).toFixed(3);
    }

    function formatSigned(value) {
      if (value === null || value === undefined) return "n/a";
      const number = Number(value);
      return `${number >= 0 ? "+" : ""}${number.toFixed(3)}`;
    }

    function lastValue(days, key) {
      const item = [...days].reverse().find((day) => day[key] !== null && day[key] !== undefined);
      return item ? item[key] : null;
    }

    function renderResults(data) {
      if (!data.results.length) {
        resultsEl.className = "empty";
        resultsEl.textContent = "No results.";
        return;
      }
      resultsEl.className = "";
      const stages = ["input", "privacy_redaction", "emotional_filter", "psychological_analyzer", "embedding_and_storage"];
      resultsEl.innerHTML = `<div class="flow">${stages.map((stage) => renderStage(data, stage)).join('<div class="flow-arrow">v</div>')}</div>`;
    }

    function renderStage(data, stage) {
      const cards = data.results
        .map((result, index) => ({ result, index, log: result.logs.find((entry) => entry.stage === stage) }))
        .filter((item) => item.log);
      const count = cards.length;
      return `
        <section class="stage">
          <div class="stage-title">
            <span>${stageLabel(stage)}</span>
            <span class="pill">${count} message${count === 1 ? "" : "s"}</span>
          </div>
          <div class="stage-body">
            ${cards.length ? cards.map((item) => renderStageCard(stage, item)).join("") : `<div class="empty">No messages reached this stage.</div>`}
          </div>
        </section>
      `;
    }

    function renderStageCard(stage, item) {
      const { result, index, log } = item;
      const title = `Message ${index + 1}`;
      if (stage === "input") {
        return messageCard(title, result.status, `<div class="message-text">${escapeHtml(log.input.text || "")}</div>`);
      }
      if (stage === "privacy_redaction") {
        return messageCard(title, privacyStatus(log.output.privacy), `
          <div>
            <div class="box-title">Redacted text</div>
            <div class="message-text">${escapeHtml(log.output.redacted_text || "")}</div>
          </div>
          <div>
            <div class="box-title">Privacy result</div>
            <pre>${escapeHtml(pretty(log.output.privacy))}</pre>
          </div>
        `);
      }
      if (stage === "emotional_filter") {
        if (log.output.error) {
          return messageCard(title, "model error", `
            <div>
              <div class="box-title">Configured runtime</div>
              <pre>${escapeHtml(pretty({
                provider: log.output.configured_provider,
                model: log.output.configured_model
              }))}</pre>
            </div>
            <div>
              <div class="box-title">Error</div>
              <pre>${escapeHtml(pretty(log.output.error))}</pre>
            </div>
          `);
        }
        return messageCard(title, log.output.is_emotionally_relevant ? "passed" : "stopped", `
          <div>
            <div class="box-title">Decision</div>
            <pre>${escapeHtml(pretty({
              passed: log.output.is_emotionally_relevant,
              confidence: log.output.confidence,
              categories: log.output.categories,
              risk_hint: log.output.risk_hint,
              provider: log.output.provider,
              configured_model: log.output.configured_model
            }))}</pre>
          </div>
        `);
      }
      if (stage === "psychological_analyzer") {
        if (log.output.error) {
          return messageCard(title, "model error", `
            <div>
              <div class="box-title">Configured runtime</div>
              <pre>${escapeHtml(pretty({
                provider: log.output.configured_provider,
                model: log.output.configured_model
              }))}</pre>
            </div>
            <div>
              <div class="box-title">Error</div>
              <pre>${escapeHtml(pretty(log.output.error))}</pre>
            </div>
          `);
        }
        return messageCard(title, "analyzed", `
          <div>
            <div class="box-title">Signal features</div>
            <pre>${escapeHtml(pretty(log.output.signal_features))}</pre>
          </div>
          <div>
            <div class="box-title">Temporary summary for embedding</div>
            <pre>${escapeHtml(pretty(log.output.summary_for_embedding))}</pre>
          </div>
          <div>
            <div class="box-title">Configured runtime</div>
            <pre>${escapeHtml(pretty({
              provider: log.output.configured_provider,
              model: log.output.configured_model
            }))}</pre>
          </div>
        `);
      }
      if (stage === "embedding_and_storage") {
        if (log.output.error) {
          return messageCard(title, "embedding error", `
            <div>
              <div class="box-title">Configured runtime</div>
              <pre>${escapeHtml(pretty({
                provider: log.output.configured_provider,
                model: log.output.configured_model
              }))}</pre>
            </div>
            <div>
              <div class="box-title">Error</div>
              <pre>${escapeHtml(pretty(log.output.error))}</pre>
            </div>
          `);
        }
        const vectorRecord = log.output.vector_record || {};
        return messageCard(title, log.output.stored ? "stored" : "preview", `
          <div class="message-card-body split">
            <div>
              <div class="box-title">Vector DB</div>
              <pre>${escapeHtml(pretty({
                stored: log.output.stored,
                stored_text: log.output.stored_text,
                vector_id: log.output.vector_id,
                vector_json: vectorRecord.vector_json
              }))}</pre>
            </div>
            <div>
              <div class="box-title">Metadata</div>
              <pre>${escapeHtml(pretty(vectorRecord.metadata || null))}</pre>
            </div>
            <div>
              <div class="box-title">Configured runtime</div>
              <pre>${escapeHtml(pretty({
                provider: log.output.configured_provider,
                model: log.output.configured_model
              }))}</pre>
            </div>
          </div>
        `, true);
      }
      return messageCard(title, result.status, `<pre>${escapeHtml(pretty(log.output))}</pre>`);
    }

    function messageCard(title, status, body, bodyAlreadyWrapped = false) {
      return `
        <article class="message-card">
          <div class="message-card-head">
            <span>${escapeHtml(title)}</span>
            <span class="pill">${escapeHtml(status)}</span>
          </div>
          ${bodyAlreadyWrapped ? body : `<div class="message-card-body">${body}</div>`}
        </article>
      `;
    }

    function privacyStatus(privacy) {
      if (!privacy || !privacy.pii_detected) return "clean";
      return `${privacy.redaction_count} redacted`;
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    async function runEval() {
      errorEl.textContent = "";
      const messages = messagesInput.value
        .split(/\\r?\\n/)
        .map((line) => line.trim())
        .filter(Boolean);
      if (!messages.length) {
        errorEl.textContent = "Add at least one message.";
        return;
      }
      runBtn.disabled = true;
      runBtn.textContent = "Running...";
      try {
        const response = await fetch("/eval/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages,
            create_vector: createVectorInput.checked,
            persist: persistInput.checked,
            child_user_id: childUserIdInput.value.trim() || null,
            start_day: startDayInput.value || null,
            one_message_per_day: oneMessagePerDayInput.checked,
            source_app: "eval-ui",
            locale: "he"
          })
        });
        if (!response.ok) {
          throw new Error(await response.text());
        }
        const data = await response.json();
        childUserIdInput.value = data.child_user_id;
        await loadKnownUsers(data.child_user_id);
        renderSummary(data);
        renderResults(data);
        if (persistInput.checked) {
          await loadTimeline();
        }
      } catch (error) {
        errorEl.textContent = error.message;
      } finally {
        runBtn.disabled = false;
        runBtn.textContent = "Run Live Pipeline";
      }
    }

    async function loadTimeline() {
      errorEl.textContent = "";
      const childUserId = childUserIdInput.value.trim();
      if (!childUserId) {
        errorEl.textContent = "Enter a child user ID or run a persisted simulation first.";
        return;
      }
      timelineBtn.disabled = true;
      timelineBtn.textContent = "Loading...";
      try {
        const params = new URLSearchParams({
          child_user_id: childUserId,
          days: String(timelineDaysInput.value || 30)
        });
        if (startDayInput.value) {
          params.set("start_day", startDayInput.value);
        }
        const response = await fetch(`/eval/alerts/timeline?${params.toString()}`);
        if (!response.ok) {
          throw new Error(await response.text());
        }
        const data = await response.json();
        renderDashboard(data);
      } catch (error) {
        errorEl.textContent = error.message;
      } finally {
        timelineBtn.disabled = false;
        timelineBtn.textContent = "Load Dashboard";
      }
    }

    runBtn.addEventListener("click", runEval);
    timelineBtn.addEventListener("click", loadTimeline);
    knownUsersSelect.addEventListener("change", () => {
      childUserIdInput.value = knownUsersSelect.value;
      startDayInput.value = "";
    });
    loadKnownUsers();
  </script>
</body>
</html>
"""
