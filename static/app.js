/* The console renders what the backend reports and decides nothing of its own:
   every field, state and metric on this page comes from an API response. */

const ROUTES = {
  health: "/health",
  analyze: "/api/v1/incidents/analyze",
  incident: (id) => `/api/v1/incidents/${id}`,
  approve: (id) => `/api/v1/incidents/${id}/approve`,
  reject: (id) => `/api/v1/incidents/${id}/reject`,
  execute: (id) => `/api/v1/incidents/${id}/execute`,
};

const ACTION_LABELS = {
  "scale_api_replicas": "Scale API Replicas",
  "restart_api_service": "Restart API Service",
};

const AUDIT_LABELS = {
  "incident_analyzed": "Incident analyzed",
  "approval_requested": "Human approval requested",
  "approval_granted": "Operator approved",
  "approval_rejected": "Operator rejected",
  "execution_blocked": "Execution blocked by policy",
  "execution_requested": "Simulated action requested",
  "execution_finished": "Simulated action finished",
  "verification_recorded": "Outcome verified",
};

const METRIC_LABELS = {
  "api_replicas": "API replicas",
  "p95_latency_ms": "p95 latency (ms)",
  "error_rate_percent": "Error rate (%)",
  "service_restarts": "Service restarts",
};

const APPROVAL_NOTE = "Approved from Sentinel console.";
const REJECTION_NOTE = "Rejected from Sentinel console.";
const EXECUTION_NOTE = "Executed from Sentinel hackathon console.";
const ATTEMPT_NOTE = "Execution attempted from Sentinel console.";

// Product language for the codes the backend can return, so a refusal reads as
// policy rather than as a crash. Messages come from our own API, never from the
// provider.
const NOTICES = {
  approval_required: {
    tone: "warn",
    title: "Execution blocked by Sentinel policy",
    detail: "Approval is required before this action can run.",
  },
  approval_rejected: {
    tone: "warn",
    title: "Execution blocked by Sentinel policy",
    detail: "This incident was rejected. A rejection is permanent.",
  },
  already_executed: {
    tone: "warn",
    title: "Nothing left to execute",
    detail: "This incident has already been executed.",
  },
  invalid_transition: {
    tone: "warn",
    title: "That decision is no longer available",
    detail: "The incident has already moved past this step.",
  },
  incident_not_found: {
    tone: "error",
    title: "Incident not found",
    detail: "This container no longer holds that incident. State lives in memory, so a restart clears it.",
  },
  workflow_store_full: {
    tone: "error",
    title: "Sentinel is at capacity",
    detail: "This slice tracks 200 incidents in memory and none of them has finished. Restart the container to reset.",
  },
  provider_not_configured: {
    tone: "error",
    title: "Model not configured",
    detail: "The container is missing its NVIDIA model configuration. Set the NVIDIA environment variables and restart.",
  },
  provider_unavailable: {
    tone: "error",
    title: "NVIDIA could not be reached",
    detail: "The inference request failed upstream. Run the incident again.",
  },
  invalid_model_response: {
    tone: "error",
    title: "The model answer was unusable",
    detail: "Sentinel does not patch or invent assessment fields. Run the incident again.",
  },
  provider_timeout: {
    tone: "error",
    title: "The model took too long",
    detail: "Inference is given 90 seconds and Sentinel does not retry. Run the incident again.",
  },
  validation: {
    tone: "warn",
    title: "The incident details are incomplete",
    detail: "Source and title are required, severity hint must be one of the listed values, and evidence is a list.",
  },
  transport: {
    tone: "error",
    title: "Sentinel is unreachable",
    detail: "The console could not reach its own API. Check that the container is still running.",
  },
  unknown: {
    tone: "error",
    title: "The request did not succeed",
    detail: "Sentinel refused this request. Try the step again.",
  },
};

const el = {
  statusDot: byId("status-dot"),
  statusValue: byId("status-value"),
  notice: byId("notice"),
  noticeTitle: byId("notice-title"),
  noticeDetail: byId("notice-detail"),
  runStatus: byId("run-status"),
  runLabel: byId("run-label"),
  runElapsed: byId("run-elapsed"),
  incidentId: byId("a-incident"),
  workflowState: byId("state-value"),
  source: byId("f-source"),
  title: byId("f-title"),
  description: byId("f-description"),
  severityHint: byId("f-severity"),
  evidence: byId("f-evidence"),
  action: byId("f-action"),
  runButton: byId("btn-run"),
  clearButton: byId("btn-clear"),
  approveButton: byId("btn-approve"),
  rejectButton: byId("btn-reject"),
  attemptButton: byId("btn-attempt"),
  executeButton: byId("btn-execute"),
  assessmentEmpty: byId("a-empty"),
  assessmentFacts: byId("a-facts"),
  assessmentBody: byId("a-body"),
  severity: byId("a-severity"),
  confidence: byId("a-confidence"),
  model: byId("a-model"),
  requiresApproval: byId("a-approval"),
  summary: byId("a-summary"),
  causes: byId("a-causes"),
  recommendations: byId("a-actions"),
  rationale: byId("a-rationale"),
  approvalEmpty: byId("ap-empty"),
  approvalBody: byId("ap-body"),
  approvalFlag: byId("ap-flag"),
  approvalExplain: byId("ap-explain"),
  approvalDecision: byId("ap-decision"),
  verificationEmpty: byId("v-empty"),
  verificationFacts: byId("v-facts"),
  verificationBody: byId("v-body"),
  verificationAction: byId("v-action"),
  verificationStatus: byId("v-status"),
  verificationSimulated: byId("v-simulation"),
  verificationMetrics: byId("v-metrics"),
  auditEmpty: byId("audit-empty"),
  auditList: byId("audit-list"),
};

const state = {
  online: false,
  workflow: null,
  notice: null,
  run: null,
};

let tick = null;

function byId(id) {
  return document.getElementById(id);
}

function put(node, value) {
  if (node) node.textContent = value;
}

function show(node, visible) {
  if (node) node.classList.toggle("is-hidden", !visible);
}

function enable(node, usable) {
  if (node) node.disabled = !usable;
}

function clear(node) {
  if (node) node.replaceChildren();
}

function add(parent, tag, text, className) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  parent.appendChild(node);
  return node;
}

function noticeFor(code) {
  return NOTICES[code] || NOTICES.unknown;
}

async function api(method, path, body) {
  const options = { method, headers: { Accept: "application/json" } };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(path, options);
  } catch (error) {
    return { ok: false, notice: NOTICES.transport };
  }
  const text = await response.text();
  let payload = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch (error) {
    payload = null;
  }
  if (response.ok) return { ok: true, payload };
  if (response.status === 422) return { ok: false, notice: NOTICES.validation };
  const detail = payload && payload.detail;
  if (detail && typeof detail === "object" && detail.error) {
    return { ok: false, notice: noticeFor(detail.error), message: detail.message };
  }
  return { ok: false, notice: NOTICES.unknown };
}

function startRun(label) {
  state.run = { label, startedAt: Date.now() };
  state.notice = null;
  if (tick) clearInterval(tick);
  tick = setInterval(() => {
    if (!state.run) return;
    put(el.runElapsed, `${Math.round((Date.now() - state.run.startedAt) / 1000)}s`);
  }, 1000);
  render();
}

function endRun() {
  state.run = null;
  if (tick) {
    clearInterval(tick);
    tick = null;
  }
}

function report(notice, message) {
  endRun();
  state.notice = { tone: notice.tone, title: notice.title, detail: message || notice.detail };
  render();
}

function incidentEvent() {
  return {
    source: el.source.value.trim(),
    title: el.title.value.trim(),
    description: el.description.value.trim(),
    severity_hint: el.severityHint.value,
    evidence: el.evidence.value
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.length > 0),
  };
}

async function refresh(incidentId) {
  const response = await api("GET", ROUTES.incident(incidentId));
  if (response.ok) state.workflow = response.payload;
  return response;
}

async function runDemoIncident() {
  startRun("NVIDIA Nemotron is assessing the incident (allow up to 90s)");
  const response = await api("POST", ROUTES.analyze, incidentEvent());
  if (!response.ok) {
    report(response.notice);
    return;
  }
  const loaded = await refresh(response.payload.incident_id);
  endRun();
  if (!loaded.ok) {
    state.workflow = null;
    report(loaded.notice);
    return;
  }
  render();
}

async function decide(kind) {
  const workflow = state.workflow;
  if (!workflow) return;
  const path = kind === "approve" ? ROUTES.approve(workflow.incident_id) : ROUTES.reject(workflow.incident_id);
  startRun(kind === "approve" ? "Recording operator approval" : "Recording operator rejection");
  const response = await api("POST", path, {
    note: kind === "approve" ? APPROVAL_NOTE : REJECTION_NOTE,
  });
  if (!response.ok) {
    report(response.notice);
    return;
  }
  state.workflow = response.payload;
  endRun();
  render();
}

async function runAction(note) {
  const workflow = state.workflow;
  if (!workflow) return;
  const action = el.action.value;
  startRun("Running the simulated action");
  const response = await api("POST", ROUTES.execute(workflow.incident_id), { action, note });
  if (!response.ok) {
    await refresh(workflow.incident_id);
    report(response.notice);
    return;
  }
  state.workflow = response.payload;
  endRun();
  render();
}

function resetDemo() {
  el.source.value = "novaops";
  el.title.value = "API latency spike";
  el.description.value = "p95 latency increased from 180ms to 2.4s";
  el.severityHint.value = "unknown";
  el.evidence.value = "error rate increased to 8.2%\nCPU increased to 91%";
  el.action.value = "scale_api_replicas";
  state.workflow = null;
  state.notice = null;
  endRun();
  render();
}

function renderHealth() {
  put(el.statusValue, state.online ? el.statusValue.dataset.ok : el.statusValue.dataset.off);
  el.statusDot.classList.toggle("dot-online", state.online);
  el.statusDot.classList.toggle("dot-offline", !state.online);
  el.statusDot.classList.remove("dot-checking");
}

function renderNotice() {
  show(el.notice, Boolean(state.notice));
  if (!state.notice) return;
  el.notice.classList.toggle("notice-warn", state.notice.tone === "warn");
  el.notice.classList.toggle("notice-error", state.notice.tone === "error");
  put(el.noticeTitle, state.notice.title);
  put(el.noticeDetail, state.notice.detail);
}

function renderRun() {
  show(el.runStatus, Boolean(state.run));
  if (state.run) put(el.runLabel, state.run.label);
}

function renderAssessment(workflow) {
  const assessment = workflow.analysis.assessment;
  show(el.assessmentEmpty, false);
  show(el.assessmentFacts, true);
  show(el.assessmentBody, true);
  el.severity.className = `sev sev-${assessment.severity}`;
  put(el.severity, assessment.severity);
  put(el.confidence, `${Math.round(assessment.confidence * 100)}%`);
  put(el.model, `${workflow.analysis.model.provider} · ${workflow.analysis.model.model}`);
  put(el.requiresApproval, assessment.requires_approval ? "Yes · operator gate" : "No");
  put(el.summary, assessment.summary);
  clear(el.causes);
  assessment.likely_causes.forEach((cause) => add(el.causes, "li", cause));
  clear(el.recommendations);
  assessment.recommended_actions.forEach((action) => add(el.recommendations, "li", action));
  put(el.rationale, assessment.reasoning_summary);
}

function renderApproval(workflow) {
  const assessment = workflow.analysis.assessment;
  show(el.approvalEmpty, false);
  show(el.approvalBody, true);
  el.approvalFlag.classList.toggle("gate-closed", workflow.state === "awaiting_approval");
  if (workflow.state === "awaiting_approval") {
    put(el.approvalFlag, "⚠ HUMAN APPROVAL REQUIRED");
    put(
      el.approvalExplain,
      "Sentinel policy prevents execution until an operator approves this high/critical incident."
    );
  } else if (assessment.requires_approval && workflow.state === "rejected") {
    put(el.approvalFlag, "Rejected");
    put(el.approvalExplain, "The operator declined this incident. A rejection is permanent.");
  } else if (workflow.approval) {
    put(el.approvalFlag, "Operator approved");
    put(
      el.approvalExplain,
      workflow.verification
        ? "Approved, and the simulated action has run. This incident is closed."
        : "Approved. The gate is open for a simulated action."
    );
  } else {
    put(el.approvalFlag, "No approval required");
    put(el.approvalExplain, "Sentinel assessed this incident as low enough to act without a gate.");
  }
  const decision = workflow.approval;
  show(el.approvalDecision, Boolean(decision));
  if (decision) {
    put(
      el.approvalDecision,
      `${decision.decision} by ${decision.actor} · ${decision.note || "no note"} · ${decision.decided_at}`
    );
  }
}

function renderVerification(workflow) {
  const verification = workflow.verification;
  show(el.verificationEmpty, !verification);
  show(el.verificationFacts, Boolean(verification));
  show(el.verificationBody, Boolean(verification));
  if (!verification) {
    put(el.verificationEmpty, "Nothing has been executed yet.");
    return;
  }
  put(el.verificationAction, ACTION_LABELS[workflow.action] || workflow.action);
  put(el.verificationStatus, verification.status === "verified" ? "VERIFIED" : "FAILED");
  el.verificationStatus.classList.toggle("ok", verification.status === "verified");
  el.verificationStatus.classList.toggle("bad", verification.status !== "verified");
  put(el.verificationSimulated, verification.simulated ? "YES · simulated" : "NO");
  clear(el.verificationMetrics);
  Object.keys(verification.before).forEach((key) => {
    const label = METRIC_LABELS[key] || key;
    const changed = verification.before[key] !== verification.after[key];
    add(
      el.verificationMetrics,
      "li",
      `${label}: ${verification.before[key]} → ${verification.after[key]}`,
      changed ? "moved" : "flat"
    );
  });
}

function renderAudit(workflow) {
  const trail = workflow.audit_trail;
  show(el.auditEmpty, trail.length === 0);
  show(el.auditList, trail.length > 0);
  clear(el.auditList);
  // Backend append order is the authoritative sequence: never re-sort it here.
  trail.forEach((entry) => {
    const row = add(el.auditList, "li", "", `actor-${entry.actor}`);
    const head = add(row, "p", "", "trail-head");
    add(head, "span", AUDIT_LABELS[entry.event] || entry.event, "trail-event");
    add(head, "span", entry.actor, "trail-actor");
    add(head, "span", entry.timestamp, "trail-time");
    const details = Object.entries(entry.details || {});
    if (details.length) {
      add(row, "p", details.map(([key, value]) => `${key}: ${value}`).join(" · "), "trail-details");
    }
  });
}

function renderControls(workflow) {
  const awaiting = workflow && workflow.state === "awaiting_approval";
  const busy = Boolean(state.run);
  // "analyzed" only ever exists when the backend decided no gate was needed, so
  // the executable set is read from the state alone rather than re-derived here.
  const executable = workflow && ["approved", "analyzed"].includes(workflow.state);
  enable(el.approveButton, awaiting);
  enable(el.rejectButton, awaiting);
  enable(el.attemptButton, awaiting);
  enable(el.executeButton, executable);
  // The action is free to choose at any point; only the backend decides whether
  // pressing Execute is allowed.
  el.action.disabled = !workflow || busy;
  enable(el.runButton, !busy);
  enable(el.clearButton, !busy);
  el.source.disabled = busy;
  el.title.disabled = busy;
  el.description.disabled = busy;
  el.severityHint.disabled = busy;
  el.evidence.disabled = busy;
}

function renderIdle() {
  put(el.incidentId, "—");
  put(el.workflowState, "idle");
  show(el.assessmentEmpty, true);
  show(el.assessmentFacts, false);
  show(el.assessmentBody, false);
  put(el.severity, "—");
  put(el.confidence, "—");
  put(el.model, "—");
  put(el.requiresApproval, "—");
  show(el.approvalEmpty, true);
  show(el.approvalBody, false);
  put(el.approvalFlag, "");
  put(el.approvalExplain, "");
  show(el.approvalDecision, false);
  show(el.verificationEmpty, true);
  show(el.verificationFacts, false);
  show(el.verificationBody, false);
  show(el.auditEmpty, true);
  show(el.auditList, false);
  clear(el.auditList);
  renderControls(null);
}

function render() {
  renderHealth();
  renderNotice();
  renderRun();
  const workflow = state.workflow;
  if (!workflow) {
    renderIdle();
    return;
  }
  put(el.incidentId, workflow.incident_id);
  put(el.workflowState, workflow.state);
  renderAssessment(workflow);
  renderApproval(workflow);
  renderVerification(workflow);
  renderAudit(workflow);
  renderControls(workflow);
}

async function pollHealth() {
  const response = await api("GET", ROUTES.health);
  state.online = response.ok;
  renderHealth();
}

function start() {
  el.runButton.addEventListener("click", runDemoIncident);
  el.clearButton.addEventListener("click", resetDemo);
  el.approveButton.addEventListener("click", () => decide("approve"));
  el.rejectButton.addEventListener("click", () => decide("reject"));
  el.attemptButton.addEventListener("click", () => runAction(ATTEMPT_NOTE));
  el.executeButton.addEventListener("click", () => runAction(EXECUTION_NOTE));
  pollHealth();
  setInterval(pollHealth, 15000);
  render();
}

start();
