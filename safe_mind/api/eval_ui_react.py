EVAL_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SafeMind Pipeline Eval</title>
  <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <style>
    :root {
      --bg: #eef2f5;
      --surface: #ffffff;
      --surface-soft: #f8fafb;
      --ink: #18212f;
      --muted: #667085;
      --line: #d8dee6;
      --accent: #16745f;
      --accent-strong: #0d5c4a;
      --warn: #a76000;
      --danger: #b4232a;
      --code: #111827;
      --shadow: 0 18px 45px rgba(24, 33, 47, 0.08);
    }
    * { box-sizing: border-box; }
    html, body, #root { min-height: 100%; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }
    button, input, select, textarea { font: inherit; }
    button {
      border: 0;
      border-radius: 8px;
      background: var(--accent);
      color: #fff;
      min-height: 40px;
      padding: 0 14px;
      font-weight: 750;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      white-space: nowrap;
    }
    button:hover { background: var(--accent-strong); }
    button:disabled { opacity: 0.55; cursor: wait; }
    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--ink);
      outline: none;
    }
    input, select { height: 38px; padding: 0 10px; }
    textarea {
      min-height: 176px;
      max-height: 38vh;
      resize: vertical;
      padding: 11px;
      direction: rtl;
      text-align: right;
    }
    input:focus, select:focus, textarea:focus {
      border-color: rgba(22, 116, 95, 0.8);
      box-shadow: 0 0 0 3px rgba(22, 116, 95, 0.12);
    }
    .app-shell {
      min-height: 100vh;
      display: grid;
      grid-template-rows: auto 1fr;
    }
    .topbar {
      background: rgba(255, 255, 255, 0.94);
      border-bottom: 1px solid var(--line);
      backdrop-filter: blur(14px);
      position: sticky;
      top: 0;
      z-index: 5;
    }
    .topbar-inner {
      max-width: 1680px;
      margin: 0 auto;
      padding: 14px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }
    .brand-mark {
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: #143d35;
      color: #d7f7e9;
      display: grid;
      place-items: center;
      font-weight: 850;
      flex: 0 0 auto;
    }
    h1, h2, h3, p { margin: 0; }
    h1 { font-size: 20px; letter-spacing: 0; }
    h2 { font-size: 15px; letter-spacing: 0; }
    h3 { font-size: 13px; letter-spacing: 0; }
    .subtle { color: var(--muted); font-size: 13px; }
    .layout {
      width: 100%;
      max-width: 1680px;
      margin: 0 auto;
      padding: 14px;
      display: grid;
      grid-template-columns: minmax(330px, 390px) minmax(0, 1fr);
      gap: 14px;
      min-height: calc(100vh - 65px);
    }
    .sidebar, .workspace {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      min-width: 0;
    }
    .sidebar {
      align-self: start;
      position: sticky;
      top: 80px;
      max-height: calc(100vh - 94px);
      overflow: auto;
    }
    .sidebar-section {
      padding: 14px;
      display: grid;
      gap: 10px;
    }
    .sidebar-section + .sidebar-section { border-top: 1px solid var(--line); }
    .section-head {
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 10px;
    }
    .field { display: grid; gap: 5px; }
    .field label, .label {
      color: #344054;
      font-size: 12px;
      font-weight: 760;
    }
    .grid-2 {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 90px;
      gap: 8px;
    }
    .switch-list { display: grid; gap: 6px; }
    .switch {
      display: flex;
      align-items: center;
      gap: 9px;
      min-height: 34px;
      color: #344054;
      font-size: 13px;
      font-weight: 650;
    }
    .switch input {
      width: 18px;
      height: 18px;
      accent-color: var(--accent);
      flex: 0 0 auto;
    }
    .hint {
      border: 1px solid #b8dacd;
      background: #f1fbf7;
      color: #164b3b;
      border-radius: 8px;
      padding: 10px;
      font-size: 12px;
    }
    .hint strong { display: block; margin-bottom: 2px; color: #0e372d; }
    .error {
      margin: 0 14px 14px;
      border: 1px solid #efb4b8;
      background: #fff5f5;
      color: var(--danger);
      border-radius: 8px;
      padding: 10px;
      font-size: 12px;
      direction: ltr;
      white-space: pre-wrap;
    }
    .workspace {
      min-height: 0;
      overflow: hidden;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
    }
    .workspace-head {
      padding: 14px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      background: var(--surface-soft);
    }
    .tabs {
      display: inline-grid;
      grid-auto-flow: column;
      gap: 3px;
      padding: 3px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }
    .tab {
      border: 0;
      background: transparent;
      color: var(--muted);
      min-height: 32px;
      padding: 0 12px;
      border-radius: 6px;
      font-size: 13px;
    }
    .tab:hover { background: #eef2f5; color: var(--ink); }
    .tab-active, .tab-active:hover { background: var(--ink); color: #fff; }
    .content {
      min-height: 0;
      overflow: auto;
      padding: 14px;
      display: grid;
      align-content: start;
      gap: 14px;
    }
    .pill-row { display: flex; flex-wrap: wrap; gap: 7px; }
    .pill, .badge {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: #fff;
      color: #475467;
      padding: 2px 8px;
      font-size: 12px;
      font-weight: 720;
      white-space: nowrap;
    }
    .badge-ok { color: #16745f; border-color: #b8dacd; background: #f1fbf7; }
    .badge-warn { color: var(--warn); border-color: #efcf8f; background: #fff8e8; }
    .badge-alert { color: var(--danger); border-color: #efb4b8; background: #fff5f5; }
    .metric-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 10px;
    }
    .metric, .stage, .message-card, .empty {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }
    .metric { padding: 11px; min-height: 74px; }
    .metric-label {
      color: var(--muted);
      font-size: 11px;
      font-weight: 780;
      margin-bottom: 5px;
    }
    .metric-value {
      font-size: 21px;
      font-weight: 820;
      word-break: break-word;
    }
    .metric-value .score-list { margin-top: 2px; }
    .score-list {
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
      align-items: center;
    }
    .score-chip {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #f8fafb;
      padding: 2px 7px;
      color: #102033;
      font-size: 12px;
      font-weight: 760;
      white-space: nowrap;
    }
    .panel-block {
      display: grid;
      gap: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface-soft);
      padding: 12px;
    }
    .timeline-wrap {
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: #fff;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      table-layout: fixed;
    }
    th, td {
      padding: 8px 9px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      white-space: normal;
    }
    th {
      position: sticky;
      top: 0;
      z-index: 1;
      background: #f8fafb;
      color: var(--muted);
      text-transform: uppercase;
      font-size: 11px;
      letter-spacing: 0;
    }
    tr:last-child td { border-bottom: 0; }
    tbody tr:not(.detail-row) {
      cursor: pointer;
      transition: background-color 120ms ease, box-shadow 120ms ease;
    }
    tbody tr:not(.detail-row):hover { box-shadow: inset 3px 0 0 var(--accent); }
    .row-selected { box-shadow: inset 3px 0 0 var(--accent); }
    .row-baseline { background: #edf6ff; }
    .row-deviation { background: #fff7ed; }
    .row-push { background: #fff0f1; }
    .detail-row { background: #fbfcfd; }
    .detail-cell {
      padding: 0;
      border-bottom: 1px solid var(--line);
    }
    .detail-panel {
      background: #fbfcfd;
      padding: 12px;
      display: grid;
      gap: 10px;
    }
    .detail-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      flex-wrap: wrap;
    }
    .detail-head h3 {
      margin: 0;
      font-size: 15px;
    }
    .detail-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }
    .detail-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 10px;
      min-width: 0;
    }
    .detail-value {
      color: #102033;
      font-size: 13px;
      line-height: 1.45;
      overflow-wrap: anywhere;
    }
    .flow { display: grid; gap: 10px; }
    .stage-head {
      padding: 9px 11px;
      border-bottom: 1px solid var(--line);
      background: var(--surface-soft);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }
    .stage-body {
      padding: 10px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 10px;
    }
    .message-card { overflow: hidden; min-width: 0; }
    .message-card-head {
      padding: 8px 10px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfd;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    .message-card-body { padding: 10px; display: grid; gap: 9px; }
    .split { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .message-text {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f8fafb;
      padding: 9px;
      direction: rtl;
      text-align: right;
      font-size: 13px;
    }
    .box-title {
      color: var(--muted);
      font-size: 11px;
      font-weight: 780;
      margin-bottom: 5px;
    }
    pre {
      margin: 0;
      overflow: auto;
      max-height: 270px;
      background: var(--code);
      color: #f3f7fb;
      border-radius: 8px;
      padding: 10px;
      font-family: "Cascadia Code", Consolas, monospace;
      font-size: 11px;
      line-height: 1.45;
      white-space: pre-wrap;
      word-break: break-word;
      direction: ltr;
      text-align: left;
    }
    .empty {
      padding: 28px;
      color: var(--muted);
      text-align: center;
      border-style: dashed;
    }
    @media (max-width: 1050px) {
      .layout { grid-template-columns: 1fr; }
      .sidebar { position: static; max-height: none; }
    }
    @media (max-width: 720px) {
      .topbar-inner, .workspace-head { align-items: stretch; flex-direction: column; }
      .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .detail-grid { grid-template-columns: 1fr; }
      .split, .grid-2 { grid-template-columns: 1fr; }
      .tabs { grid-auto-flow: row; }
    }
  </style>
</head>
<body>
  <div id="root"></div>
  <script>
    const h = React.createElement;
    const { useEffect, useState } = React;
    const seededSyntheticUserId = "55555555-6666-4777-8888-999999999999";
    const sampleMessages = [
      "I feel overwhelmed by tomorrow's exam and cannot sleep.",
      "Can you explain quadratic equations in a simple way?",
      "Everyone in class ignores me and I feel alone all the time."
    ].join("\\n");
    const stages = [
      "input",
      "privacy_redaction",
      "psychological_analyzer",
      "signal_storage"
    ];
    const stageLabels = {
      input: "Raw Messages",
      privacy_redaction: "1. Privacy",
      psychological_analyzer: "2. Psychological Analyzer",
      signal_storage: "3. Signal JSON + Baseline"
    };

    function App() {
      const [knownUsers, setKnownUsers] = useState([]);
      const [childUserId, setChildUserId] = useState("");
      const [startDay, setStartDay] = useState("");
      const [timelineDays, setTimelineDays] = useState(30);
      const [messages, setMessages] = useState(sampleMessages);
      const [oneMessagePerDay, setOneMessagePerDay] = useState(false);
      const [createVector, setCreateVector] = useState(false);
      const [persist, setPersist] = useState(false);
      const [activeView, setActiveView] = useState("dashboard");
      const [runData, setRunData] = useState(null);
      const [timelineData, setTimelineData] = useState(null);
      const [error, setError] = useState("");
      const [loadingRun, setLoadingRun] = useState(false);
      const [loadingTimeline, setLoadingTimeline] = useState(false);

      useEffect(() => {
        loadKnownUsers();
      }, []);

      async function loadKnownUsers(selectedUserId = "") {
        try {
          const response = await fetch("/eval/alerts/users");
          if (!response.ok) return;
          const data = await response.json();
          setKnownUsers(data.users || []);
          const current = selectedUserId || childUserId || seededSyntheticUserId;
          if (current && (data.users || []).includes(current)) {
            setChildUserId(current);
          }
        } catch (_) {
          return;
        }
      }

      async function loadTimeline(nextChildUserId = childUserId) {
        setError("");
        const resolvedChildUserId = String(nextChildUserId || "").trim();
        if (!resolvedChildUserId) {
          setError("Enter a child user ID or run a persisted simulation first.");
          return;
        }
        setLoadingTimeline(true);
        try {
          const params = new URLSearchParams({
            child_user_id: resolvedChildUserId,
            days: String(timelineDays || 30)
          });
          if (startDay) params.set("start_day", startDay);
          const response = await fetch(`/eval/alerts/timeline?${params.toString()}`);
          if (!response.ok) throw new Error(await response.text());
          const data = await response.json();
          setTimelineData(data);
          setChildUserId(data.child_user_id);
          setActiveView("dashboard");
        } catch (err) {
          setError(err.message);
        } finally {
          setLoadingTimeline(false);
        }
      }

      async function runEval() {
        setError("");
        const lines = messages.split(/\\r?\\n/).map((line) => line.trim()).filter(Boolean);
        if (!lines.length) {
          setError("Add at least one message.");
          return;
        }
        setLoadingRun(true);
        try {
          const response = await fetch("/eval/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              messages: lines,
              create_vector: createVector,
              persist,
              child_user_id: childUserId.trim() || null,
              start_day: startDay || null,
              one_message_per_day: oneMessagePerDay,
              source_app: "eval-ui",
              locale: "he"
            })
          });
          if (!response.ok) throw new Error(await response.text());
          const data = await response.json();
          setRunData(data);
          setChildUserId(data.child_user_id);
          setActiveView("pipeline");
          await loadKnownUsers(data.child_user_id);
          if (persist) await loadTimeline(data.child_user_id);
        } catch (err) {
          setError(err.message);
        } finally {
          setLoadingRun(false);
        }
      }

      return h("div", { className: "app-shell" },
        h("header", { className: "topbar" },
          h("div", { className: "topbar-inner" },
            h("div", { className: "brand" },
              h("div", { className: "brand-mark" }, "SM"),
              h("div", null,
                h("h1", null, "SafeMind Pipeline Eval"),
                h("p", { className: "subtle" },
                  "Internal stage-by-stage funnel. One line equals one message. Eval runs use the real configured models with no silent heuristic fallback."
                )
              )
            ),
            h("div", { className: "pill-row" },
              h(Pill, { label: "local internal tool" }),
              h(Pill, { label: "React dashboard" })
            )
          )
        ),
        h("main", { className: "layout" },
          h("aside", { className: "sidebar" },
            h(DashboardControls, {
              knownUsers, childUserId, setChildUserId, startDay, setStartDay,
              timelineDays, setTimelineDays, loadingTimeline, loadTimeline
            }),
            h(PipelineControls, {
              messages, setMessages, oneMessagePerDay, setOneMessagePerDay,
              createVector, setCreateVector, persist, setPersist, loadingRun, runEval
            }),
            error ? h("div", { className: "error" }, error) : null
          ),
          h("section", { className: "workspace" },
            h("div", { className: "workspace-head" },
              h("div", null,
                h("h2", null, activeView === "dashboard" ? "Alert Dashboard" : "Pipeline Run"),
                h("p", { className: "subtle" }, "Fixed baseline, daily drift, gate decisions, and message-level pipeline inspection.")
              ),
              h("div", { className: "tabs" },
                h(TabButton, { active: activeView === "dashboard", onClick: () => setActiveView("dashboard") }, "Dashboard"),
                h(TabButton, { active: activeView === "pipeline", onClick: () => setActiveView("pipeline") }, "Pipeline")
              )
            ),
            h("div", { className: "content" },
              activeView === "dashboard"
                ? h(AlertDashboard, { data: timelineData })
                : h(PipelineResults, { data: runData })
            )
          )
        )
      );
    }

    function DashboardControls(props) {
      return h("div", { className: "sidebar-section" },
        h("div", { className: "section-head" },
          h("div", null,
            h("h2", null, "Alert Dashboard"),
            h("p", { className: "subtle" }, "Load the last 30 days for any stored child user.")
          )
        ),
        h("div", { className: "hint" },
          h("strong", null, "How to monitor"),
          "Current test user is synthetic but stored in the real local DB. Choose the user, keep Timeline start empty, and load the last 30 days."
        ),
        h(Field, { label: "Known users in local DB" },
          h("select", {
            value: props.childUserId,
            onChange: (event) => {
              props.setChildUserId(event.target.value);
              props.setStartDay("");
            }
          },
            h("option", { value: "" }, "No user selected"),
            props.knownUsers.map((userId) => h("option", { key: userId, value: userId }, userId))
          )
        ),
        h(Field, { label: "Child user ID" },
          h("input", {
            type: "text",
            value: props.childUserId,
            placeholder: "Paste or select a user ID",
            onChange: (event) => props.setChildUserId(event.target.value)
          })
        ),
        h("div", { className: "grid-2" },
          h(Field, { label: "Timeline start" },
            h("input", {
              type: "date",
              value: props.startDay,
              onChange: (event) => props.setStartDay(event.target.value)
            })
          ),
          h(Field, { label: "Days" },
            h("input", {
              type: "number",
              min: "1",
              max: "90",
              value: props.timelineDays,
              onChange: (event) => props.setTimelineDays(Number(event.target.value))
            })
          )
        ),
        h("button", { type: "button", disabled: props.loadingTimeline, onClick: () => props.loadTimeline() },
          props.loadingTimeline ? "Loading..." : "Load Dashboard"
        )
      );
    }

    function PipelineControls(props) {
      return h("div", { className: "sidebar-section" },
        h("div", { className: "section-head" },
          h("div", null,
            h("h2", null, "Pipeline Simulation"),
            h("p", { className: "subtle" }, "Run the real configured pipeline on local test messages.")
          )
        ),
        h(Field, { label: "Messages" },
          h("textarea", {
            value: props.messages,
            onChange: (event) => props.setMessages(event.target.value)
          })
        ),
        h("div", { className: "switch-list" },
          h(Switch, {
            checked: props.oneMessagePerDay,
            onChange: props.setOneMessagePerDay,
            label: "One message line = next calendar day"
          }),
          h(Switch, {
            checked: props.createVector,
            onChange: props.setCreateVector,
            label: "Request embedding preview if explicitly enabled"
          }),
          h(Switch, {
            checked: props.persist,
            onChange: props.setPersist,
            label: "Persist to local DB"
          })
        ),
        h("button", { type: "button", disabled: props.loadingRun, onClick: props.runEval },
          props.loadingRun ? "Running..." : "Run Live Pipeline"
        )
      );
    }

    function AlertDashboard({ data }) {
      if (!data) {
        return h("div", { className: "empty" }, "Persist a simulation or enter a child user ID, then load the dashboard.");
      }
      if (!data.days || !data.days.length) {
        return h("div", { className: "empty" }, "No timeline days.");
      }
      const baselineDays = data.days.filter((day) => day.phase === "baseline").length;
      const monitoringDays = data.days.filter((day) => day.phase === "monitoring").length;
      const deviationDays = data.days.filter((day) => day.is_deviation).length;
      const pushDays = data.days.filter((day) => day.should_send_push).length;
      const latestWithBaseline = [...data.days].reverse().find((day) => day.baseline_scores);
      const firstPushDay = data.days.find((day) => day.should_send_push);

      return h(React.Fragment, null,
        h("div", { className: "pill-row" },
          h(Pill, { label: `${data.start_day} to ${data.end_day}` }),
          h(Pill, { label: data.child_user_id })
        ),
        h("div", { className: "panel-block" },
          h("div", { className: "hint" },
            h("strong", null, "What you are seeing"),
            `Baseline period: ${baselineRangeText(data.days)}. First push in this view: ${firstPushDay ? firstPushDay.day : "none"}. A push means 3 metrics each reached a 3-day deviation streak.`
          ),
          h("div", { className: "metric-grid" },
            h(Metric, { label: "Baseline days", value: baselineDays }),
            h(Metric, { label: "Monitoring days", value: monitoringDays }),
            h(Metric, { label: "Deviation days", value: deviationDays }),
            h(Metric, { label: "Push decisions", value: pushDays })
          ),
          h("div", { className: "metric-grid" },
            h(Metric, { label: "Fixed baseline", value: h(ScoreList, { scores: latestWithBaseline?.baseline_scores }) }),
            h(Metric, { label: "Latest metrics", value: h(ScoreList, { scores: lastValue(data.days, "scores") }) }),
            h(Metric, { label: "Latest max metric streak", value: lastValue(data.days, "deviations_in_window") ?? "0" })
          )
        ),
        h(TimelineTable, { key: `${data.child_user_id}-${data.start_day}-${data.end_day}`, days: data.days })
      );
    }

    function TimelineTable({ days }) {
      const [selectedDay, setSelectedDay] = useState(days.find((day) => day.should_send_push) || days.find((day) => day.is_deviation) || days[0]);
      const selectedKey = selectedDay ? selectedDay.day : null;
      return h("div", { className: "timeline-wrap" },
        h("table", null,
          h("thead", null,
            h("tr", null,
              ["Day", "Phase", "Msgs", "Deviation", "Streak", "Push"]
                .map((head) => h("th", { key: head }, head))
            )
          ),
          h("tbody", null, days.flatMap((day) => {
            const selected = day.day === selectedKey;
            const row = h(TimelineRow, {
              key: `${day.day}-row`,
              day,
              selected,
              onSelect: () => setSelectedDay(day)
            });
            if (!selected) return [row];
            return [
              row,
              h("tr", { key: `${day.day}-detail`, className: "detail-row" },
                h("td", { className: "detail-cell", colSpan: 6 },
                  h(DayDetailPanel, { day })
                )
              )
            ];
          }))
        )
      );
    }

    function TimelineRow({ day, selected, onSelect }) {
      const toneClass = day.should_send_push
        ? "row-push"
        : day.is_deviation
          ? "row-deviation"
          : day.phase === "baseline"
            ? "row-baseline"
            : "";
      const className = `${toneClass}${selected ? " row-selected" : ""}`.trim();
      return h("tr", { className, onClick: onSelect, tabIndex: 0, onKeyDown: (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect();
        }
      }},
        h("td", null, day.day),
        h("td", null, h(PhaseBadge, { phase: day.phase })),
        h("td", null, day.message_count),
        h("td", null, day.is_deviation ? h(Badge, { tone: "warn" }, "yes") : h(Badge, { tone: "ok" }, "no")),
        h("td", null, day.deviations_in_window),
        h("td", null, day.should_send_push ? h(Badge, { tone: "alert" }, "send") : h(Badge, { tone: "ok" }, "hold"))
      );
    }

    function DayDetailPanel({ day }) {
      return h("section", { className: "detail-panel" },
        h("div", { className: "detail-head" },
          h("h3", null, `Day detail: ${day.day}`),
          h("div", { className: "pill-row" },
            h(PhaseBadge, { phase: day.phase }),
            day.is_deviation ? h(Badge, { tone: "warn" }, "deviation") : h(Badge, { tone: "ok" }, "no deviation"),
            day.should_send_push ? h(Badge, { tone: "alert" }, "push sent") : h(Badge, { tone: "ok" }, "no push")
          )
        ),
        h("div", { className: "detail-grid" },
          h(DetailCard, { title: "Daily metrics" }, h(ScoreList, { scores: day.scores })),
          h(DetailCard, { title: "Baseline metrics" }, h(ScoreList, { scores: day.baseline_scores })),
          h(DetailCard, { title: "Decision" },
            h("div", { className: "detail-value" }, `Messages: ${day.message_count}`),
            h("div", { className: "detail-value" }, `Max metric streak: ${day.deviations_in_window}`),
            h("div", { className: "detail-value" }, day.reason || "n/a")
          )
        )
      );
    }

    function DetailCard({ title, children }) {
      return h("div", { className: "detail-card" },
        h("div", { className: "box-title" }, title),
        children
      );
    }

    function PipelineResults({ data }) {
      if (!data) return h("div", { className: "empty" }, "No run yet.");
      const stored = data.results.filter((item) => item.stored_signal.stored).length;
      const preview = data.results.filter((item) => item.status === "preview").length;
      const noVector = data.results.filter((item) => item.status === "no_vector").length;
      const runtime = data.runtime || {};

      return h(React.Fragment, null,
        h("div", { className: "pill-row" },
          h(Pill, { label: `messages: ${data.count}` }),
          h(Pill, { label: `child: ${data.child_user_id}` }),
          h(Pill, { label: `stored: ${stored}` }),
          h(Pill, { label: `preview: ${preview}` }),
          h(Pill, { label: `no vector: ${noVector}` }),
          h(Pill, { label: `analyzer model: ${runtime.psychological_analyzer_model || runtime.psychological_analyzer_provider || "n/a"}` }),
          h(Pill, { label: `embedding model: ${runtime.embedding_model || runtime.embedding_provider || "disabled"}` })
        ),
        h("div", { className: "flow" }, stages.map((stage) => h(Stage, { key: stage, stage, results: data.results })))
      );
    }

    function Stage({ stage, results }) {
      const cards = results
        .map((result, index) => ({ result, index, log: result.logs.find((entry) => entry.stage === stage) }))
        .filter((item) => item.log);
      return h("section", { className: "stage" },
        h("div", { className: "stage-head" },
          h("h3", null, stageLabels[stage] || stage),
          h(Pill, { label: `${cards.length} message${cards.length === 1 ? "" : "s"}` })
        ),
        h("div", { className: "stage-body" },
          cards.length
            ? cards.map((item) => h(StageCard, { key: `${stage}-${item.index}`, stage, item }))
            : h("div", { className: "empty" }, "No messages reached this stage.")
        )
      );
    }

    function StageCard({ stage, item }) {
      const { result, index, log } = item;
      const title = `Message ${index + 1}`;
      if (stage === "input") {
        return h(MessageCard, { title, status: result.status },
          h("div", { className: "message-text" }, log.input.text || "")
        );
      }
      if (stage === "privacy_redaction") {
        return h(MessageCard, { title, status: privacyStatus(log.output.privacy) },
          h(LabeledBlock, { title: "Redacted text" }, h("div", { className: "message-text" }, log.output.redacted_text || "")),
          h(JsonBlock, { title: "Privacy result", value: log.output.privacy })
        );
      }
      if (stage === "psychological_analyzer") {
        if (log.output.error) return h(ModelErrorCard, { title, status: "model error", output: log.output });
        return h(MessageCard, { title, status: "analyzed" },
          h(JsonBlock, { title: "Signal features", value: log.output.signal_features }),
          h(JsonBlock, { title: "Configured runtime", value: {
            provider: log.output.configured_provider,
            model: log.output.configured_model
          }})
        );
      }
      if (stage === "signal_storage") {
        const signalRecord = log.output.signal_record || {};
        return h(MessageCard, { title, status: log.output.stored ? "stored" : "preview" },
          h(JsonBlock, { title: "Stored analysis", value: log.output.signal_features }),
          h(JsonBlock, { title: "Storage", value: {
            stored: log.output.stored,
            stored_text: log.output.stored_text,
            signal_id: log.output.signal_id || signalRecord.signal_id,
            storage_kind: log.output.storage_kind
          }}),
          h(JsonBlock, { title: "Alert decision", value: log.output.alert_decision })
        );
      }
      if (stage === "embedding_and_storage") {
        if (log.output.error) return h(ModelErrorCard, { title, status: "embedding error", output: log.output });
        const vectorRecord = log.output.vector_record || {};
        return h(MessageCard, { title, status: log.output.stored ? "stored" : "preview", split: true },
          h(JsonBlock, { title: "Vector DB", value: {
            stored: log.output.stored,
            stored_text: log.output.stored_text,
            vector_id: log.output.vector_id,
            vector_json: vectorRecord.vector_json
          }}),
          h(JsonBlock, { title: "Metadata", value: vectorRecord.metadata || null }),
          h(JsonBlock, { title: "Configured runtime", value: {
            provider: log.output.configured_provider,
            model: log.output.configured_model
          }})
        );
      }
      return h(MessageCard, { title, status: result.status }, h(JsonBlock, { title: "Output", value: log.output }));
    }

    function ModelErrorCard({ title, status, output }) {
      return h(MessageCard, { title, status },
        h(JsonBlock, { title: "Configured runtime", value: {
          provider: output.configured_provider,
          model: output.configured_model
        }}),
        h(JsonBlock, { title: "Error", value: output.error })
      );
    }

    function MessageCard({ title, status, split, children }) {
      return h("article", { className: "message-card" },
        h("div", { className: "message-card-head" },
          h("strong", null, title),
          h(Pill, { label: status })
        ),
        h("div", { className: `message-card-body${split ? " split" : ""}` }, children)
      );
    }

    function Field({ label, children }) {
      return h("div", { className: "field" }, h("label", null, label), children);
    }

    function Switch({ checked, onChange, label }) {
      return h("label", { className: "switch" },
        h("input", { type: "checkbox", checked, onChange: (event) => onChange(event.target.checked) }),
        h("span", null, label)
      );
    }

    function TabButton({ active, onClick, children }) {
      return h("button", { type: "button", className: `tab${active ? " tab-active" : ""}`, onClick }, children);
    }

    function Pill({ label }) {
      return h("span", { className: "pill" }, label);
    }

    function Badge({ tone, children }) {
      return h("span", { className: `badge${tone ? ` badge-${tone}` : ""}` }, children);
    }

    function PhaseBadge({ phase }) {
      if (phase === "baseline") return h(Badge, { tone: "ok" }, "baseline");
      if (phase === "monitoring") return h(Badge, { tone: "warn" }, "monitoring");
      return h(Badge, null, "pre-baseline");
    }

    function Metric({ label, value }) {
      return h("div", { className: "metric" },
        h("div", { className: "metric-label" }, label),
        h("div", { className: "metric-value" }, value ?? "n/a")
      );
    }

    function ScoreList({ scores }) {
      if (!scores) return h("span", { className: "detail-value" }, "n/a");
      const labels = {
        positive_emotion: "pos",
        negative_emotion: "neg",
        loneliness: "lonely",
        anxiety_stress: "stress",
        hopelessness: "hope",
        self_worth_low: "worth",
        risk: "risk"
      };
      return h("div", { className: "score-list" },
        Object.entries(labels)
          .filter(([key]) => scores[key] !== undefined && scores[key] !== null)
          .map(([key, label]) => h("span", { key, className: "score-chip" }, `${label}: ${Number(scores[key]).toFixed(1)}`))
      );
    }

    function LabeledBlock({ title, children }) {
      return h("div", null, h("div", { className: "box-title" }, title), children);
    }

    function JsonBlock({ title, value }) {
      return h(LabeledBlock, { title }, h("pre", null, JSON.stringify(value, null, 2)));
    }

    function privacyStatus(privacy) {
      if (!privacy || !privacy.pii_detected) return "clean";
      return `${privacy.redaction_count} redacted`;
    }

    function baselineRangeText(days) {
      const baselineDays = days.filter((day) => day.phase === "baseline");
      if (!baselineDays.length) return "not visible in current date range";
      return `${baselineDays[0].day} to ${baselineDays[baselineDays.length - 1].day}`;
    }

    function formatNumber(value) {
      if (value === null || value === undefined) return "n/a";
      return Number(value).toFixed(3);
    }

    function formatScores(scores) {
      if (!scores) return "n/a";
      const labels = {
        positive_emotion: "pos",
        negative_emotion: "neg",
        loneliness: "lonely",
        anxiety_stress: "stress",
        hopelessness: "hope",
        self_worth_low: "worth",
        risk: "risk"
      };
      return Object.entries(labels)
        .filter(([key]) => scores[key] !== undefined && scores[key] !== null)
        .map(([key, label]) => `${label}: ${Number(scores[key]).toFixed(1)}`)
        .join(" | ");
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

    ReactDOM.createRoot(document.getElementById("root")).render(h(App));
  </script>
</body>
</html>
"""
