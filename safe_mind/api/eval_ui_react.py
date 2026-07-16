EVAL_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Safe Mind Pipeline Eval</title>
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
    .sidebar-section-run {
      background: linear-gradient(180deg, #f2fbf7 0%, #ffffff 38%);
      border-left: 4px solid var(--accent);
    }
    .sidebar-section-dashboard {
      background: linear-gradient(180deg, #f5f7ff 0%, #ffffff 42%);
      border-left: 4px solid #4f66b0;
    }
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
    .dataset-meta-grid {
      display: grid;
      grid-template-columns: 92px minmax(0, 1fr);
      gap: 8px;
    }
    .dataset-textarea {
      min-height: 118px;
      max-height: 26vh;
      direction: ltr;
      text-align: left;
      font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
      font-size: 12px;
      line-height: 1.4;
    }
    .prompt-card {
      position: relative;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #eef0f2;
      overflow: hidden;
    }
    .prompt-code {
      margin: 0;
      max-height: 210px;
      overflow: auto;
      padding: 38px 12px 12px;
      background: transparent;
      color: #111827;
      border-radius: 0;
      font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
      font-size: 12px;
      line-height: 1.55;
      direction: ltr;
      text-align: left;
      white-space: pre-wrap;
      word-break: normal;
    }
    .prompt-copy-btn {
      position: absolute;
      top: 8px;
      right: 8px;
      min-height: 28px;
      border: 1px solid #c7ccd3;
      background: #fff;
      color: #344054;
      padding: 0 9px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 780;
      box-shadow: 0 1px 2px rgba(24, 33, 47, 0.08);
    }
    .prompt-copy-btn:hover {
      background: #f8fafb;
      color: #18212f;
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
    .hint-dashboard {
      border-color: #c5ccef;
      background: #f4f6ff;
      color: #344078;
    }
    .hint-dashboard strong { color: #27315f; }
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
    .workspace-actions {
      display: flex;
      align-items: center;
      justify-content: end;
      gap: 8px;
      flex-wrap: wrap;
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
    .tab-dashboard.tab-active, .tab-dashboard.tab-active:hover { background: #4f66b0; color: #fff; }
    .tab-run.tab-active, .tab-run.tab-active:hover { background: var(--accent); color: #fff; }
    .tab-dashboard:not(.tab-active) { color: #4f66b0; }
    .tab-run:not(.tab-active) { color: var(--accent); }
    .button-run { background: var(--accent); }
    .button-run:hover { background: var(--accent-strong); }
    .button-dashboard { background: #4f66b0; }
    .button-dashboard:hover { background: #3d508f; }
    .button-export {
      min-height: 32px;
      padding: 0 10px;
      border-radius: 6px;
      background: #217346;
      font-size: 12px;
    }
    .button-export:hover { background: #185c37; }
    .content {
      min-height: 0;
      overflow: auto;
      padding: 14px;
      display: grid;
      align-content: start;
      gap: 14px;
    }
    .loading-state {
      min-height: 420px;
      display: grid;
      place-items: center;
      border: 1px solid var(--line);
      border-radius: 8px;
      background:
        radial-gradient(circle at 50% 38%, rgba(22, 116, 95, 0.08), transparent 28%),
        #fbfcfd;
    }
    .loading-card {
      display: grid;
      justify-items: center;
      gap: 14px;
      color: #344054;
      text-align: center;
      padding: 26px;
      width: min(520px, 100%);
    }
    .signal-loader {
      position: relative;
      width: 112px;
      height: 112px;
    }
    .signal-loader-ring {
      position: absolute;
      inset: 0;
      border: 2px solid rgba(22, 116, 95, 0.14);
      border-top-color: var(--accent);
      border-radius: 999px;
      animation: spin 1.15s linear infinite;
    }
    .signal-loader-ring:nth-child(2) {
      inset: 16px;
      border-top-color: #4f66b0;
      animation-duration: 1.75s;
      animation-direction: reverse;
    }
    .signal-loader-dot {
      position: absolute;
      left: 50%;
      top: 50%;
      width: 14px;
      height: 14px;
      border-radius: 999px;
      background: var(--accent);
      transform: translate(-50%, -50%);
      animation: pulse 1.25s ease-in-out infinite;
    }
    .loading-title {
      font-size: 17px;
      font-weight: 820;
      color: var(--ink);
    }
    .loading-subtitle {
      color: var(--muted);
      font-size: 13px;
      max-width: 420px;
    }
    .progress-panel {
      width: min(440px, 100%);
      display: grid;
      gap: 8px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 12px;
      text-align: left;
    }
    .progress-meta {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      color: #344054;
      font-size: 12px;
      font-weight: 760;
    }
    .progress-count {
      color: var(--ink);
      font-size: 14px;
      font-weight: 840;
    }
    .progress-track {
      height: 10px;
      overflow: hidden;
      border-radius: 999px;
      background: #e9eef3;
    }
    .progress-fill {
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--accent), #4f66b0);
      transition: width 220ms ease;
    }
    .progress-stage {
      color: var(--muted);
      font-size: 12px;
      overflow-wrap: anywhere;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    @keyframes pulse {
      0%, 100% { box-shadow: 0 0 0 0 rgba(22, 116, 95, 0.28); }
      50% { box-shadow: 0 0 0 18px rgba(22, 116, 95, 0); }
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
      align-items: start;
    }
    .detail-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 10px;
      min-width: 0;
    }
    .detail-card-wide { grid-column: 1 / -1; }
    .score-history {
      display: grid;
      gap: 7px;
      max-height: 186px;
      overflow: auto;
      padding-right: 2px;
    }
    .score-history-row {
      display: grid;
      grid-template-columns: 74px minmax(0, 1fr);
      gap: 8px;
      align-items: start;
      padding: 7px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfd;
    }
    .score-history-label {
      color: var(--muted);
      font-size: 11px;
      font-weight: 820;
      line-height: 1.3;
    }
    .decision-deltas {
      display: grid;
      gap: 7px;
      max-height: 182px;
      overflow: auto;
      padding-right: 2px;
      direction: rtl;
      text-align: right;
    }
    .decision-delta-item {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 8px;
      align-items: center;
      min-height: 34px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfd;
      padding: 6px 8px;
      color: #102033;
      font-size: 13px;
      font-weight: 760;
      line-height: 1.25;
    }
    .decision-delta-name {
      min-width: 0;
      overflow-wrap: anywhere;
    }
    .decision-delta-value {
      direction: ltr;
      unicode-bidi: isolate;
      white-space: nowrap;
      border-radius: 999px;
      padding: 2px 8px;
      font-weight: 860;
    }
    .decision-summary {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 10px;
    }
    .decision-stat {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f8fafb;
      padding: 8px;
      min-width: 0;
    }
    .decision-stat-label {
      color: var(--muted);
      font-size: 10px;
      font-weight: 780;
      text-transform: uppercase;
      letter-spacing: 0;
    }
    .decision-stat-value {
      color: var(--ink);
      font-size: 15px;
      font-weight: 840;
      margin-top: 2px;
      overflow-wrap: anywhere;
    }
    .change-list {
      display: grid;
      gap: 6px;
    }
    .change-row {
      display: grid;
      grid-template-columns: minmax(72px, 1fr) repeat(3, minmax(58px, auto));
      align-items: center;
      gap: 8px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 7px 8px;
    }
    .change-label {
      color: #102033;
      font-size: 12px;
      font-weight: 820;
    }
    .change-value {
      color: #344054;
      font-size: 12px;
      font-weight: 720;
      text-align: right;
      white-space: nowrap;
    }
    .change-delta {
      border-radius: 999px;
      padding: 2px 7px;
      font-weight: 840;
      text-align: center;
    }
    .change-up {
      color: var(--danger);
      background: #fff5f5;
      border: 1px solid #efb4b8;
    }
    .change-down {
      color: #16745f;
      background: #f1fbf7;
      border: 1px solid #b8dacd;
    }
    .change-flat {
      color: #475467;
      background: #f8fafb;
      border: 1px solid var(--line);
    }
    .reason-note {
      margin-top: 10px;
      border-top: 1px solid var(--line);
      padding-top: 9px;
      color: #475467;
      font-size: 12px;
      line-height: 1.45;
      max-height: 58px;
      overflow: auto;
      direction: rtl;
      text-align: right;
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
      .split, .grid-2, .dataset-meta-grid { grid-template-columns: 1fr; }
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
    const sampleDataset = [
      "timestamp,message",
      "2026-01-03 09:15,I barely slept last night",
      "2026-01-03 22:40,Everything feels pointless",
      "2026-01-04 08:10,I am going to school now",
      "2026-01-14 21:35,I feel alone again and I cannot calm down"
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
      const [datasetText, setDatasetText] = useState(sampleDataset);
      const [datasetFormat, setDatasetFormat] = useState("csv");
      const [uid, setUid] = useState("");
      const [parentPhone, setParentPhone] = useState("");
      const [alertDays, setAlertDays] = useState("2026-01-17, 2026-01-24");
      const [sendAlerts, setSendAlerts] = useState(false);
      const [activeView, setActiveView] = useState("dashboard");
      const [runData, setRunData] = useState(null);
      const [runJob, setRunJob] = useState(null);
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
          setError("Enter a child user ID or run a dataset simulation first.");
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
        if (!datasetText.trim()) {
          setError("Paste a CSV or JSON dataset first.");
          return;
        }
        setLoadingRun(true);
        setRunJob(null);
        try {
          const response = await fetch("/eval/datasets/jobs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              dataset_text: datasetText,
              dataset_format: datasetFormat,
              child_user_id: null,
              uid: uid.trim() || null,
              parent_phone: parentPhone.trim() || null,
              send_alerts: sendAlerts,
              source_app: "eval-dataset",
              locale: "he"
            })
          });
          if (!response.ok) throw new Error(await response.text());
          const job = await response.json();
          setRunJob(job);
          const data = await pollDatasetJob(job.job_id);
          setRunData(data);
          setChildUserId(data.child_user_id);
          setTimelineData(data.timeline);
          setStartDay(data.start_day);
          setTimelineDays(Math.max(1, data.timeline?.days?.length || 30));
          setActiveView("summary");
          await loadKnownUsers(data.child_user_id);
        } catch (err) {
          setError(err.message);
        } finally {
          setLoadingRun(false);
        }
      }

      async function pollDatasetJob(jobId) {
        let lastStatus = null;
        for (;;) {
          const response = await fetch(`/eval/datasets/jobs/${encodeURIComponent(jobId)}`);
          if (!response.ok) throw new Error(await response.text());
          const status = await response.json();
          lastStatus = status;
          setRunJob(status);
          if (status.status === "succeeded") return status.result;
          if (status.status === "failed") {
            throw new Error(status.error || "Dataset simulation failed.");
          }
          await sleep(1800);
        }
      }

      function exportCurrentView() {
        if (activeView === "dashboard") {
          exportDashboardExcel(timelineData);
          return;
        }
        exportRunExcel(runData);
      }

      const canExport = activeView === "dashboard"
        ? Boolean(timelineData?.days?.length)
        : Boolean(runData?.timeline?.days?.length);

      return h("div", { className: "app-shell" },
        h("header", { className: "topbar" },
          h("div", { className: "topbar-inner" },
            h("div", { className: "brand" },
              h("div", { className: "brand-mark" }, "SM"),
              h("div", null,
                h("h1", null, "Safe Mind Pipeline Eval"),
                h("p", { className: "subtle" },
                  "Dataset simulation for historical monitoring, daily flags, and parent-alert decisions."
                )
              )
            )
          )
        ),
        h("main", { className: "layout" },
          h("aside", { className: "sidebar" },
            h(PipelineControls, {
              datasetText, setDatasetText, datasetFormat, setDatasetFormat,
              uid, setUid, parentPhone, setParentPhone, sendAlerts, setSendAlerts,
              alertDays, setAlertDays, loadingRun, runEval
            }),
            h(DashboardControls, {
              knownUsers, childUserId, setChildUserId, startDay, setStartDay,
              timelineDays, setTimelineDays, loadingTimeline, loadTimeline
            }),
            error ? h("div", { className: "error" }, error) : null
          ),
          h("section", { className: "workspace" },
            h("div", { className: "workspace-head" },
              h("div", null,
                h("h2", null, activeView === "dashboard" ? "Alert Dashboard" : "Dataset Run"),
                h("p", { className: "subtle" }, "Fixed baseline, daily drift, gate decisions, and alert delivery status.")
              ),
              h("div", { className: "workspace-actions" },
                h("button", {
                  type: "button",
                  className: "button-export",
                  disabled: !canExport,
                  onClick: exportCurrentView
                }, "Export Excel"),
                h("div", { className: "tabs" },
                  h(TabButton, { active: activeView === "dashboard", tone: "dashboard", onClick: () => setActiveView("dashboard") }, "Dashboard"),
                  h(TabButton, { active: activeView === "summary", tone: "run", onClick: () => setActiveView("summary") }, "Run")
                )
              )
            ),
            h("div", { className: "content" },
              loadingRun
                ? h(LoadingState, {
                    title: "Running dataset simulation",
                    subtitle: runJob
                      ? "The server is processing the dataset in the background. You can follow the message count below."
                      : "Queued job. The server can keep processing large datasets while this screen polls for progress.",
                    progress: runJob
                  })
                : loadingTimeline
                  ? h(LoadingState, {
                      title: "Loading alert dashboard",
                      subtitle: "Fetching stored signal days and rebuilding the monitoring timeline."
                    })
                  : activeView === "dashboard"
                    ? h(AlertDashboard, { data: timelineData })
                    : h(DatasetResults, { data: runData })
            )
          )
        )
      );
    }

    function sleep(ms) {
      return new Promise((resolve) => setTimeout(resolve, ms));
    }

    function exportDashboardExcel(data) {
      if (!data || !data.days || !data.days.length) return;
      const baselineDays = data.days.filter((day) => day.phase === "baseline").length;
      const monitoringDays = data.days.filter((day) => day.phase === "monitoring").length;
      const deviationDays = data.days.filter((day) => day.is_deviation).length;
      const pushDays = data.days.filter((day) => day.should_send_push).length;
      const summaryRows = [
        ["Export type", "Alert Dashboard"],
        ["Child user ID", data.child_user_id],
        ["Start day", data.start_day],
        ["End day", data.end_day],
        ["Baseline days", baselineDays],
        ["Monitoring days", monitoringDays],
        ["Deviation days", deviationDays],
        ["Push decisions", pushDays],
        ["Baseline range", baselineRangeText(data.days)]
      ];
      downloadExcelFile(
        `safe-mind-dashboard-${safeFilePart(data.child_user_id)}-${data.start_day || "start"}-${data.end_day || "end"}.xls`,
        [
          { title: "Summary", rows: summaryRows },
          { title: "Daily timeline", rows: timelineExportRows(data.days) }
        ]
      );
    }

    function exportRunExcel(data) {
      if (!data || !data.timeline?.days?.length) return;
      const finalized = data.finalized_days || [];
      const finalizedByDay = Object.fromEntries(finalized.map((item) => [item.day, item]));
      const timelineDays = data.timeline.days || [];
      const dryRunAlerts = finalized.filter((item) => item.alert_delivery === "dry_run").length;
      const deviationDays = timelineDays.filter((day) => day.is_deviation).length;
      const pushDays = timelineDays.filter((day) => day.should_send_push).length;
      const maxStreak = timelineDays.reduce((max, day) => Math.max(max, day.deviations_in_window || 0), 0);
      const runtime = data.runtime || {};
      const summaryRows = [
        ["Export type", "Dataset Run"],
        ["Child user ID", data.child_user_id],
        ["UID", data.uid],
        ["Start day", data.start_day],
        ["End day", data.end_day],
        ["Messages processed", data.count],
        ["Flagged days", deviationDays],
        ["Push days", pushDays],
        ["Max streak", maxStreak],
        ["Dry-run alerts", dryRunAlerts],
        ["WhatsApp sent", data.whatsapp_sent],
        ["WhatsApp skipped", data.whatsapp_skipped],
        ["WhatsApp failed", data.whatsapp_failed],
        ["Analyzer provider", runtime.psychological_analyzer_provider],
        ["Analyzer model", runtime.psychological_analyzer_model]
      ];
      downloadExcelFile(
        `safe-mind-run-${safeFilePart(data.uid || data.child_user_id)}-${data.start_day || "start"}-${data.end_day || "end"}.xls`,
        [
          { title: "Summary", rows: summaryRows },
          { title: "Daily timeline", rows: timelineExportRows(timelineDays, finalizedByDay) }
        ]
      );
    }

    function timelineExportRows(days, finalizedByDay = {}) {
      const metricCols = metricDefinitions();
      const headers = [
        "Day",
        "Phase",
        "Message count",
        "Deviation",
        "Max metric streak",
        "Push decision",
        "Delivery",
        "Reason",
        "Message score history",
        ...metricCols.map((metric) => `Daily ${metric.label}`),
        ...metricCols.map((metric) => `Baseline ${metric.label}`),
        ...metricCols.map((metric) => `Delta ${metric.label}`)
      ];
      const rows = days.map((day) => {
        const finalized = finalizedByDay[day.day] || {};
        return [
          day.day,
          day.phase,
          day.message_count ?? 0,
          yesNo(day.is_deviation),
          day.deviations_in_window ?? 0,
          yesNo(day.should_send_push),
          finalized.alert_delivery || "",
          day.reason || "",
          messageScoreHistoryCell(day.message_scores),
          ...metricCols.map((metric) => scoreCell(day.scores, metric.key)),
          ...metricCols.map((metric) => scoreCell(day.baseline_scores, metric.key)),
          ...metricCols.map((metric) => deltaCell(day.scores, day.baseline_scores, metric.key))
        ];
      });
      return [headers, ...rows];
    }

    function scoreCell(scores, key) {
      if (!scores || scores[key] === null || scores[key] === undefined) return "";
      const value = Number(scores[key]);
      return Number.isFinite(value) ? Number(value.toFixed(3)) : "";
    }

    function deltaCell(scores, baselineScores, key) {
      if (!scores || !baselineScores) return "";
      const daily = Number(scores[key]);
      const baseline = Number(baselineScores[key]);
      if (!Number.isFinite(daily) || !Number.isFinite(baseline)) return "";
      return Number((daily - baseline).toFixed(3));
    }

    function messageScoreHistoryCell(messageScores) {
      if (!Array.isArray(messageScores) || !messageScores.length) return "";
      return messageScores
        .map((item, index) => `M${index + 1}: ${formatScoresInline(item.scores)}`)
        .join("\\n");
    }

    function yesNo(value) {
      return value ? "yes" : "no";
    }

    function safeFilePart(value) {
      return String(value || "export").replace(/[^a-zA-Z0-9_-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 80) || "export";
    }

    function downloadExcelFile(filename, sections) {
      const html = [
        "<html xmlns:o=\\"urn:schemas-microsoft-com:office:office\\" xmlns:x=\\"urn:schemas-microsoft-com:office:excel\\" xmlns=\\"http://www.w3.org/TR/REC-html40\\">",
        "<head><meta charset=\\"utf-8\\"><style>table{border-collapse:collapse;margin-bottom:24px;}th,td{border:1px solid #b7c0ce;padding:6px 8px;mso-number-format:'\\\\@';}th{background:#edf2f7;font-weight:700;}h2{font-family:Arial,sans-serif;font-size:16px;}</style></head>",
        "<body>",
        ...sections.flatMap((section) => [
          `<h2>${escapeHtml(section.title)}</h2>`,
          tableHtml(section.rows)
        ]),
        "</body></html>"
      ].join("");
      const blob = new Blob(["\\ufeff", html], { type: "application/vnd.ms-excel;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    }

    function tableHtml(rows) {
      return `<table>${rows.map((row, index) => {
        const tag = index === 0 ? "th" : "td";
        return `<tr>${row.map((cell) => `<${tag}>${escapeHtml(cell)}</${tag}>`).join("")}</tr>`;
      }).join("")}</table>`;
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    function DashboardControls(props) {
      return h("div", { className: "sidebar-section sidebar-section-dashboard" },
        h("div", { className: "section-head" },
          h("div", null,
            h("h2", null, "Alert Dashboard"),
            h("p", { className: "subtle" }, "Load the last 30 days for any stored child user.")
          )
        ),
        h("div", { className: "hint hint-dashboard" },
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
        h("button", { type: "button", className: "button-dashboard", disabled: props.loadingTimeline, onClick: () => props.loadTimeline() },
          props.loadingTimeline ? "Loading..." : "Load Dashboard"
        )
      );
    }

    function PipelineControls(props) {
      const promptText = buildDatasetPrompt(props.alertDays);
      const [promptCopied, setPromptCopied] = useState(false);

      async function handleCopyPrompt() {
        await copyText(promptText);
        setPromptCopied(true);
        window.setTimeout(() => setPromptCopied(false), 1400);
      }

      return h("div", { className: "sidebar-section sidebar-section-run" },
        h("div", { className: "section-head" },
          h("div", null,
            h("h2", null, "Dataset Simulation"),
            h("p", { className: "subtle" }, "Run historical messages through the real monitoring pipeline.")
          )
        ),
        h(Field, { label: "Wanted alert days" },
          h("input", {
            type: "text",
            value: props.alertDays,
            placeholder: "2026-01-17, 2026-01-24",
            onChange: (event) => props.setAlertDays(event.target.value)
          })
        ),
        h("div", { className: "hint" },
          h("strong", null, "Generate a long dataset with AI"),
          "Copy this prompt into your AI tool, then paste the CSV it returns into Historical dataset. Each run creates a fresh test user."
        ),
        h("div", { className: "field" },
          h("label", null, "Prompt to copy"),
          h("div", { className: "prompt-card" },
            h("button", {
              type: "button",
              className: "prompt-copy-btn",
              onClick: handleCopyPrompt
            }, promptCopied ? "Copied" : "Copy"),
            h("pre", { className: "prompt-code" }, promptText)
          )
        ),
        h("div", { className: "dataset-meta-grid" },
          h(Field, { label: "Format" },
            h("select", {
              value: props.datasetFormat,
              onChange: (event) => props.setDatasetFormat(event.target.value)
            },
              h("option", { value: "csv" }, "CSV"),
              h("option", { value: "json" }, "JSON")
            )
          ),
          h(Field, { label: "Parent phone" },
            h("input", {
              type: "text",
              value: props.parentPhone,
              placeholder: "+972...",
              onChange: (event) => props.setParentPhone(event.target.value)
            })
          )
        ),
        h("div", { className: "hint" },
          h("strong", null, "Dataset format"),
          "CSV columns: timestamp,message. JSON can be an array of objects with timestamp and message."
        ),
        h(Field, { label: "External user ID" },
          h("input", {
            type: "text",
            value: props.uid,
            placeholder: "Optional; generated when empty",
            onChange: (event) => props.setUid(event.target.value)
          })
        ),
        h(Field, { label: "Historical dataset" },
          h("textarea", {
            className: "dataset-textarea",
            value: props.datasetText,
            onChange: (event) => props.setDatasetText(event.target.value)
          })
        ),
        h("div", { className: "switch-list" },
          h(Switch, {
            checked: props.sendAlerts,
            onChange: props.setSendAlerts,
            label: "Send WhatsApp alerts for alert days"
          })
        ),
        h("button", { type: "button", className: "button-run", disabled: props.loadingRun, onClick: props.runEval },
          props.loadingRun ? "Running..." : "Run Dataset"
        )
      );
    }

    function LoadingState({ title, subtitle, progress }) {
      return h("div", { className: "loading-state" },
        h("div", { className: "loading-card" },
          h("div", { className: "signal-loader", "aria-hidden": "true" },
            h("div", { className: "signal-loader-ring" }),
            h("div", { className: "signal-loader-ring" }),
            h("div", { className: "signal-loader-dot" })
          ),
          h("div", { className: "loading-title" }, title),
          h("div", { className: "loading-subtitle" }, subtitle),
          progress ? h(ProgressPanel, { progress }) : null
        )
      );
    }

    function ProgressPanel({ progress }) {
      const processed = Number(progress.processed_messages || 0);
      const total = Number(progress.total_messages || 0);
      const percent = total > 0 ? Math.max(0, Math.min(100, Math.round((processed / total) * 100))) : 0;
      return h("div", { className: "progress-panel" },
        h("div", { className: "progress-meta" },
          h("span", null, "Messages processed"),
          h("span", { className: "progress-count" }, `${processed} / ${total}`)
        ),
        h("div", { className: "progress-track", role: "progressbar", "aria-valuemin": 0, "aria-valuemax": total, "aria-valuenow": processed },
          h("div", { className: "progress-fill", style: { width: `${percent}%` } })
        ),
        h("div", { className: "progress-meta" },
          h("span", null, `${percent}% complete`),
          h("span", null, stageText(progress.stage || progress.status))
        ),
        progress.job_id ? h("div", { className: "progress-stage" }, `Job: ${progress.job_id}`) : null
      );
    }

    function buildDatasetPrompt(alertDays) {
      const daysText = String(alertDays || "").trim() || "choose 1-2 monitoring days after the baseline";
      return [
        "Create a Safe Mind evaluation CSV dataset.",
        "",
        "Output only CSV text, with exactly these columns:",
        "timestamp,message",
        "",
        "Requirements:",
        "- Use one child/teen voice, realistic short messages, no explanations.",
        "- Create at least 10 baseline signal days before any alert day.",
        "- Baseline days should be emotionally normal or mildly positive.",
        "- A baseline day counts only if it has at least one message.",
        "- To trigger an alert, create 3 consecutive message days ending on each requested alert day.",
        "- On every one of those 3 consecutive trigger days, every message must clearly repeat at least these 4 dimensions: loneliness, anxiety/stress, hopelessness, and low self-worth.",
        "- Use explicit, unmistakable wording for trigger days, such as: I feel completely alone, I cannot calm down, nothing will get better, I feel worthless.",
        "- Do not make trigger-day messages subtle, mixed, hopeful, or resolved. They must stay consistently concerning across all 3 days.",
        "- If there is more than one requested alert day, add at least 2 calm recovery message days after the first alert streak before starting the next 3-day alert streak.",
        "- Keep messages non-graphic and non-instructional.",
        "- Include 1-3 messages per message day.",
        "- Use ISO-like timestamps such as 2026-01-03 09:15.",
        "- Use exactly the requested alert days as the 3rd day of each trigger streak. For example, if 2026-01-17 is requested, make 2026-01-15, 2026-01-16, and 2026-01-17 the 3 consecutive trigger days.",
        "- Do not create extra severe days during the 10-day baseline.",
        "",
        `Requested alert days: ${daysText}`,
        "",
        "Make sure the CSV is long enough for Safe Mind: 10 baseline days first, then the exact 3-day streaks needed for the requested alert days, with recovery days between separate alert streaks."
      ].join("\\n");
    }

    async function copyText(value) {
      try {
        await navigator.clipboard.writeText(value);
      } catch (_) {
        return;
      }
    }

    function AlertDashboard({ data }) {
      if (!data) {
        return h("div", { className: "empty" }, "Run a dataset or enter a child user ID, then load the dashboard.");
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
              onSelect: () => setSelectedDay((current) => current?.day === day.day ? null : day)
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
            h(DecisionSummary, { day })
          ),
          h(DetailCard, { title: `Message score history (${messageScoreCount(day)})`, wide: true },
            h(MessageScoreHistory, { messageScores: day.message_scores })
          )
        )
      );
    }

    function DetailCard({ title, children, wide = false }) {
      return h("div", { className: `detail-card${wide ? " detail-card-wide" : ""}` },
        h("div", { className: "box-title" }, title),
        children
      );
    }

    function DatasetResults({ data }) {
      if (!data) return h("div", { className: "empty" }, "No dataset run yet.");
      const runtime = data.runtime || {};
      const finalized = data.finalized_days || [];
      const timelineDays = data.timeline?.days || [];
      const finalizedByDay = Object.fromEntries(finalized.map((item) => [item.day, item]));
      const dryRunAlerts = finalized.filter((item) => item.alert_delivery === "dry_run").length;
      const baselineDays = timelineDays.filter((day) => day.phase === "baseline").length;
      const monitoringDays = timelineDays.filter((day) => day.phase === "monitoring").length;
      const deviationDays = timelineDays.filter((day) => day.is_deviation).length;
      const pushDays = timelineDays.filter((day) => day.should_send_push).length;
      const maxStreak = timelineDays.reduce((max, day) => Math.max(max, day.deviations_in_window || 0), 0);

      return h(React.Fragment, null,
        h("div", { className: "pill-row" },
          h(Pill, { label: `messages: ${data.count}` }),
          h(Pill, { label: `child: ${data.child_user_id}` }),
          h(Pill, { label: `uid: ${data.uid}` }),
          h(Pill, { label: `${data.start_day} to ${data.end_day}` }),
          h(Pill, { label: `flagged days: ${deviationDays}` }),
          h(Pill, { label: `push days: ${pushDays}` }),
          h(Pill, { label: `dry-run alerts: ${dryRunAlerts}` }),
          h(Pill, { label: `sent: ${data.whatsapp_sent}` }),
          h(Pill, { label: `skipped: ${data.whatsapp_skipped}` }),
          h(Pill, { label: `failed: ${data.whatsapp_failed}` }),
          h(Pill, { label: `analyzer model: ${runtime.psychological_analyzer_model || runtime.psychological_analyzer_provider || "n/a"}` })
        ),
        h("div", { className: "panel-block" },
          h("div", { className: "hint" },
            h("strong", null, "Run complete"),
            pushDays
              ? "At least one day reached the alert gate. If sending was enabled and a parent phone was provided, delivery appears in the table below."
              : "No alert was sent. A max streak of 3 is not enough by itself; Safe Mind requires 3 different metrics to each reach a 3-day streak on the same day."
          ),
          h("div", { className: "metric-grid" },
            h(Metric, { label: "Messages processed", value: data.count }),
            h(Metric, { label: "Baseline days", value: baselineDays }),
            h(Metric, { label: "Monitoring days", value: monitoringDays }),
            h(Metric, { label: "Flagged days", value: deviationDays })
          ),
          h("div", { className: "metric-grid" },
            h(Metric, { label: "Max streak", value: maxStreak }),
            h(Metric, { label: "Push days", value: pushDays }),
            h(Metric, { label: "Dry-run alerts", value: dryRunAlerts }),
            h(Metric, { label: "WhatsApp sent", value: data.whatsapp_sent })
          )
        ),
        h(RunTimelineTable, { days: timelineDays, finalizedByDay })
      );
    }

    function RunTimelineTable({ days, finalizedByDay }) {
      const [selectedDay, setSelectedDay] = useState(days.find((day) => day.should_send_push) || days.find((day) => day.is_deviation) || days[0]);
      const selectedKey = selectedDay ? selectedDay.day : null;
      return h("div", { className: "timeline-wrap" },
        h("table", null,
          h("thead", null,
            h("tr", null,
              ["Day", "Phase", "Msgs", "Flag", "Streak", "Push", "Delivery"]
                .map((head) => h("th", { key: head }, head))
            )
          ),
          h("tbody", null, days.flatMap((day) => {
            const selected = day.day === selectedKey;
            const finalizedDay = finalizedByDay[day.day] || {};
            const delivery = finalizedDay.alert_delivery || "not_needed";
            const row = h(RunTimelineRow, {
              key: `${day.day}-row`,
              day,
              delivery,
              selected,
              onSelect: () => setSelectedDay((current) => current?.day === day.day ? null : day)
            });
            if (!selected) return [row];
            return [
              row,
              h("tr", { key: `${day.day}-detail`, className: "detail-row" },
                h("td", { className: "detail-cell", colSpan: 7 },
                  h(RunDayDetailPanel, { day, delivery })
                )
              )
            ];
          }))
        )
      );
    }

    function RunTimelineRow({ day, delivery, selected, onSelect }) {
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
        h("td", null, day.message_count ?? 0),
        h("td", null, day.is_deviation ? h(Badge, { tone: "warn" }, "flag") : h(Badge, { tone: "ok" }, "clear")),
        h("td", null, day.deviations_in_window ?? 0),
        h("td", null, day.should_send_push ? h(Badge, { tone: "alert" }, "send") : h(Badge, { tone: "ok" }, "hold")),
        h("td", null, h(DeliveryBadge, { delivery }))
      );
    }

    function RunDayDetailPanel({ day, delivery }) {
      return h("section", { className: "detail-panel" },
        h("div", { className: "detail-head" },
          h("h3", null, `Run detail: ${day.day}`),
          h("div", { className: "pill-row" },
            h(PhaseBadge, { phase: day.phase }),
            day.is_deviation ? h(Badge, { tone: "warn" }, "flagged") : h(Badge, { tone: "ok" }, "clear"),
            day.should_send_push ? h(Badge, { tone: "alert" }, "push") : h(Badge, { tone: "ok" }, "hold"),
            h(DeliveryBadge, { delivery })
          )
        ),
        h("div", { className: "detail-grid" },
          h(DetailCard, { title: "Daily metrics" }, h(ScoreList, { scores: day.scores })),
          h(DetailCard, { title: "Baseline metrics" }, h(ScoreList, { scores: day.baseline_scores })),
          h(DetailCard, { title: "Decision" },
            h(DecisionSummary, { day, delivery })
          ),
          h(DetailCard, { title: `Message score history (${messageScoreCount(day)})`, wide: true },
            h(MessageScoreHistory, { messageScores: day.message_scores })
          )
        )
      );
    }

    function DeliveryBadge({ delivery }) {
      if (delivery === "sent") return h(Badge, { tone: "alert" }, "sent");
      if (delivery === "failed") return h(Badge, { tone: "alert" }, "failed");
      if (delivery === "skipped") return h(Badge, { tone: "warn" }, "skipped");
      if (delivery === "dry_run") return h(Badge, { tone: "warn" }, "dry run");
      return h(Badge, { tone: "ok" }, "not needed");
    }

    function DecisionSummary({ day }) {
      return h(MetricChangeList, { scores: day.scores, baselineScores: day.baseline_scores });
    }

    function MetricChangeList({ scores, baselineScores }) {
      if (!scores || !baselineScores) {
        return h("div", { className: "detail-value" }, "No baseline comparison available yet.");
      }
      return h("div", { className: "decision-deltas" },
        decisionMetricDefinitions()
          .map((metric) => ({
            ...metric,
            daily: Number(scores[metric.key]),
            baseline: Number(baselineScores[metric.key])
          }))
          .filter((metric) => (
            Number.isFinite(metric.daily)
            && Number.isFinite(metric.baseline)
            && Math.abs(metric.daily - metric.baseline) >= 0.05
          ))
          .map((metric) => {
            const delta = metric.daily - metric.baseline;
            return h("div", { key: metric.key, className: "decision-delta-item" },
              h("span", { className: "decision-delta-name" }, metric.hebrew),
              h("span", { className: `decision-delta-value ${decisionDeltaClass(metric, delta)}` },
                `${formatDelta(delta)} מהרגיל`
              )
            );
          })
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

    function TabButton({ active, tone, onClick, children }) {
      return h("button", { type: "button", className: `tab tab-${tone || "default"}${active ? " tab-active" : ""}`, onClick }, children);
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
      return h("div", { className: "score-list" },
        metricDefinitions()
          .filter((metric) => scores[metric.key] !== undefined && scores[metric.key] !== null)
          .map((metric) => h("span", { key: metric.key, className: "score-chip" }, `${metric.short}: ${Number(scores[metric.key]).toFixed(1)}`))
      );
    }

    function MessageScoreHistory({ messageScores }) {
      if (!Array.isArray(messageScores) || !messageScores.length) {
        return h("span", { className: "detail-value" }, "No per-message scores stored for this day.");
      }
      return h("div", { className: "score-history" },
        messageScores.map((item, index) => h("div", { key: item.event_id || index, className: "score-history-row" },
          h("div", { className: "score-history-label" }, `M${index + 1}`),
          h(ScoreList, { scores: item.scores })
        ))
      );
    }

    function messageScoreCount(day) {
      return Array.isArray(day?.message_scores) ? day.message_scores.length : 0;
    }

    function metricDefinitions() {
      return [
        { key: "positive_emotion", short: "pos", label: "Positive" },
        { key: "negative_emotion", short: "neg", label: "Negative" },
        { key: "loneliness", short: "lonely", label: "Loneliness" },
        { key: "anxiety_stress", short: "stress", label: "Stress" },
        { key: "hopelessness", short: "hope", label: "Hopelessness" },
        { key: "self_worth_low", short: "worth", label: "Low worth" },
        { key: "risk", short: "risk", label: "Risk" }
      ];
    }

    function decisionMetricDefinitions() {
      return [
        { key: "negative_emotion", hebrew: "רגש שלילי", concerningDirection: 1 },
        { key: "loneliness", hebrew: "בדידות", concerningDirection: 1 },
        { key: "anxiety_stress", hebrew: "חרדה/סטרס", concerningDirection: 1 },
        { key: "hopelessness", hebrew: "חוסר תקווה", concerningDirection: 1 },
        { key: "self_worth_low", hebrew: "ערך עצמי נמוך", concerningDirection: 1 },
        { key: "risk", hebrew: "סיכון", concerningDirection: 1 },
        { key: "positive_emotion", hebrew: "רגש חיובי", concerningDirection: -1 }
      ];
    }

    function formatDelta(delta) {
      if (Math.abs(delta) < 0.05) return "0.0";
      const rounded = Number(delta.toFixed(1));
      const formatted = Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
      return `${rounded > 0 ? "+" : ""}${formatted}`;
    }

    function deltaClass(delta) {
      if (Math.abs(delta) < 0.05) return "change-flat";
      return delta > 0 ? "change-up" : "change-down";
    }

    function decisionDeltaClass(metric, delta) {
      if (Math.abs(delta) < 0.05) return "change-flat";
      const concerning = metric.concerningDirection * delta > 0;
      return concerning ? "change-up" : "change-down";
    }

    function stageText(stage) {
      const labels = {
        queued: "Queued",
        starting: "Starting",
        running: "Running",
        processing_messages: "Analyzing messages",
        finalizing_days: "Finalizing days",
        building_timeline: "Building timeline",
        complete: "Complete",
        succeeded: "Complete",
        failed: "Failed"
      };
      return labels[stage] || stage || "Running";
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

    function formatScoresInline(scores) {
      if (!scores) return "n/a";
      return metricDefinitions()
        .filter((metric) => scores[metric.key] !== undefined && scores[metric.key] !== null)
        .map((metric) => `${metric.short}-${Number(scores[metric.key]).toFixed(1)}`)
        .join(", ");
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
