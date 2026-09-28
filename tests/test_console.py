"""Console regression tests: static assets, CSP scoping, backend/UI contract drift.

Every assertion here is about the contract between the served console and the
backend. The console must not invent routes, actions, audit events or severity
hints, and it must not carry secret material or inline script.
"""

import asyncio
import re
from html.parser import HTMLParser
from pathlib import Path

import httpx
import pytest

from sentinel.api import create_app
from sentinel.schemas import (
    ActionName,
    Assessment,
    IncidentAnalysis,
    IncidentEvent,
    ModelInfo,
    SeverityHint,
)
from sentinel.workflow import WorkflowError, WorkflowStore

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

CSP_DIRECTIVES = {
    "default-src": "'self'",
    "script-src": "'self'",
    "style-src": "'self'",
    "connect-src": "'self'",
    "img-src": "'self' data:",
    "font-src": "'self'",
    "object-src": "'none'",
    "base-uri": "'none'",
    "frame-ancestors": "'none'",
}

DEMO_INCIDENT = {
    "source": "novaops",
    "title": "API latency spike",
    "description": "p95 latency increased from 180ms to 2.4s",
    "severity_hint": "unknown",
    "evidence": ["error rate increased to 8.2%", "CPU increased to 91%"],
}

ASSESSMENT = {
    "summary": "p95 latency spiked alongside an elevated error rate.",
    "severity": "high",
    "confidence": 0.87,
    "likely_causes": ["CPU saturation"],
    "recommended_actions": ["Scale the API tier"],
    "requires_approval": True,
    "reasoning_summary": "Latency and errors rose together.",
}

STAGE_STATUSES = {"real", "simulated", "mixed", "planned"}

KEY_STATUS = {"real": "real", "mixed": "mixed", "sim": "simulated", "planned": "planned"}

CANONICAL_LOOP = (
    "OBSERVE",
    "UNDERSTAND",
    "DECIDE",
    "ACT / REQUEST APPROVAL",
    "VERIFY",
    "LEARN",
)

FORBIDDEN_IN_STATIC = (
    "nvapi-",
    "NVIDIA_API_KEY",
    "NVIDIA_BASE_URL",
    "integrate.api.nvidia.com",
    "reasoning_content",
    "chain-of-thought",
    "chain of thought",
)

ASSETS = ("index.html", "styles.css", "app.js")

CORE_ROUTES = {
    "/health",
    "/api/v1/incidents/analyze",
    "/api/v1/incidents/*",
    "/api/v1/incidents/*/approve",
    "/api/v1/incidents/*/reject",
    "/api/v1/incidents/*/execute",
}


def asset(name: str) -> str:
    """Contents of a static asset. Empty when the file does not exist yet."""
    path = STATIC_DIR / name
    return path.read_text(encoding="utf-8") if path.exists() else ""


def request(method: str, path: str):
    app = create_app()

    async def go():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.request(method, path)

    return asyncio.run(go())


class Markup(HTMLParser):
    """Elements with attributes, own text and children, plus script bodies."""

    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
            "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.elements: list[dict] = []
        self.scripts: list[dict] = []
        self._open: list[dict] = []

    @classmethod
    def parse(cls, source: str) -> "Markup":
        parser = cls()
        parser.feed(source)
        return parser

    def _push(self, tag, attrs, self_closing=False):
        element = {"tag": tag, "attrs": dict(attrs), "text": "", "children": []}
        if self._open:
            self._open[-1]["children"].append(element)
        self.elements.append(element)
        if tag == "script":
            self.scripts.append(element)
        if tag not in self.VOID and not self_closing:
            self._open.append(element)
        return element

    def handle_starttag(self, tag, attrs):
        self._push(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        self._push(tag, attrs, self_closing=True)

    def handle_endtag(self, tag):
        for index in range(len(self._open) - 1, -1, -1):
            if self._open[index]["tag"] == tag:
                del self._open[index]
                break

    def handle_data(self, data):
        if self._open:
            self._open[-1]["text"] += data

    def descendants(self, element) -> list[dict]:
        found = []
        for child in element["children"]:
            found.append(child)
            found.extend(self.descendants(child))
        return found

    def by_id(self, element_id: str):
        return next((el for el in self.elements if el["attrs"].get("id") == element_id), None)

    def ids(self) -> set[str]:
        return {el["attrs"]["id"] for el in self.elements if el["attrs"].get("id")}

    def with_attr(self, name: str) -> list[dict]:
        return [el for el in self.elements if name in el["attrs"]]

    def value_of(self, element_id: str) -> str:
        """The value a form control would submit, read from the markup."""
        element = self.by_id(element_id)
        if element is None:
            return ""
        if element["tag"] == "textarea":
            return element["text"].strip()
        if element["tag"] == "select":
            option = next(
                (child for child in self.descendants(element)
                 if child["tag"] == "option" and "selected" in child["attrs"]),
                None,
            )
            return "" if option is None else option["attrs"].get("value", "")
        return element["attrs"].get("value", "")


console = Markup.parse(asset("index.html"))


def stage_chips() -> dict[str, dict]:
    return {el["attrs"]["data-stage"]: el for el in console.with_attr("data-stage")}


def text_of(element) -> str:
    """Element text followed by its descendants' text, in document order."""
    parts = [element["text"], *(child["text"] for child in console.descendants(element))]
    return " ".join(" ".join(parts).split())


def classes(element) -> list[str]:
    return element["attrs"].get("class", "").split()


def js_map_keys(name: str) -> set[str]:
    """Keys of a top-level `const NAME = { ... }` literal in app.js."""
    match = re.search(rf"\b{name}\b\s*=\s*\{{(.*?)\n\}}", asset("app.js"), re.S)
    assert match, f"{name} not found in static/app.js"
    return set(re.findall(r"""["']([a-z_]+)["']\s*:""", match.group(1)))


def js_routes() -> set[str]:
    """Every absolute path the console mentions, placeholders normalised."""
    literals = re.findall(r"""[`'"](/[A-Za-z0-9_./${}-]*)[`'"]""", asset("app.js"))
    return {re.sub(r"\$\{[^}]*\}", "*", path) for path in literals}


def backend_audit_events() -> set[str]:
    """Audit event names the backend actually emits, gathered by running it."""

    def analyse(incident_id: str) -> IncidentAnalysis:
        return IncidentAnalysis(
            incident_id=incident_id,
            assessment=Assessment(**ASSESSMENT),
            model=ModelInfo(model="nvidia/nemotron-test"),
        )

    store = WorkflowStore()
    event = IncidentEvent(source=DEMO_INCIDENT["source"], title=DEMO_INCIDENT["title"])
    seen: set[str] = set()

    def collect(record):
        if record is not None:
            seen.update(entry.event for entry in record.audit_trail)

    collect(store.record_analysis(event, analyse("inc-blocked")))
    try:
        store.execute("inc-blocked", "scale_api_replicas")
    except WorkflowError:
        pass
    collect(store.decide("inc-blocked", "approved", "ok"))
    collect(store.execute("inc-blocked", "scale_api_replicas", "go"))

    collect(store.record_analysis(event, analyse("inc-rejected")))
    collect(store.decide("inc-rejected", "rejected", "no"))
    return seen


# -- serving ---------------------------------------------------------------


def test_console_assets_are_served():
    for name in ASSETS:
        response = request("GET", f"/static/{name}")
        assert response.status_code == 200, f"/static/{name} is not served"
    assert "javascript" in request("GET", "/static/app.js").headers["content-type"]
    assert "css" in request("GET", "/static/styles.css").headers["content-type"]


def test_console_links_its_own_assets():
    assert console.by_id("f-source") is not None, "console markup is missing"
    hrefs = {el["attrs"].get("href", "") for el in console.elements if el["tag"] == "link"}
    srcs = {el["attrs"].get("src", "") for el in console.scripts}
    assert "/static/styles.css" in hrefs
    assert "/static/app.js" in srcs


def test_no_inline_script_or_event_handlers():
    assert asset("index.html"), "static/index.html is missing"
    assert console.scripts, "console must load its behaviour as an external script"
    for script in console.scripts:
        assert script["attrs"].get("src", "").startswith("/static/"), "script must be external"
        assert not script["text"].strip(), "inline script is not allowed"
    inline = {
        key
        for el in console.elements
        for key in el["attrs"]
        if key.lower().startswith("on") or key.lower() == "style"
    }
    assert not inline, f"inline handlers/styles are not allowed: {sorted(inline)}"


# -- content security policy ----------------------------------------------


def test_console_response_carries_the_strict_csp():
    header = request("GET", "/").headers.get("content-security-policy")
    assert header, "GET / must carry a Content-Security-Policy header"
    directives = {}
    for part in header.split(";"):
        if part.strip():
            key, _, value = part.strip().partition(" ")
            directives[key.lower()] = " ".join(value.split())
    assert directives == CSP_DIRECTIVES
    assert "unsafe-inline" not in header
    assert "unsafe-eval" not in header


def test_csp_is_scoped_to_the_console_response():
    for path in ("/health", "/docs", "/static/app.js", "/static/styles.css"):
        response = request("GET", path)
        assert "content-security-policy" not in response.headers, (
            f"{path} must stay unaffected: the policy belongs to GET / alone, not middleware"
        )


# -- honest labelling ------------------------------------------------------


def test_loop_stages_are_each_marked():
    stages = {
        el["attrs"]["data-stage"]: el["attrs"].get("data-stage-status")
        for el in console.with_attr("data-stage")
    }
    assert stages, "no stage chips found in the loop strip"
    for stage, status in stages.items():
        assert status in STAGE_STATUSES, f"{stage} is not honestly labelled"
    for el in console.with_attr("data-stage"):
        assert el["text"].strip(), "a stage chip must name itself"


def test_canonical_loop_wording_is_kept_in_order():
    assert tuple(stage_chips()) == CANONICAL_LOOP, (
        "the loop strip must read OBSERVE → UNDERSTAND → DECIDE → ACT / REQUEST APPROVAL → VERIFY → LEARN"
    )


def test_act_stage_separates_the_real_gate_from_the_simulated_action():
    chip = stage_chips()["ACT / REQUEST APPROVAL"]
    assert chip["attrs"]["data-stage-status"] == "mixed", (
        "the approval policy and state machine are real: labelling the whole stage simulated is wrong"
    )
    wording = text_of(chip)
    assert "Approval: REAL" in wording, wording
    assert "Action: SIMULATED" in wording, wording
    assert "Approval: SIMULATED" not in wording
    assert "Action: REAL" not in wording


def test_legend_covers_every_status_the_strip_uses():
    legend = next(
        el for el in console.elements if el["tag"] == "p" and "legend" in classes(el)
    )
    keyed = {
        KEY_STATUS[cls[1]]
        for cls in (classes(el) for el in console.descendants(legend))
        if cls and cls[0] == "key" and len(cls) > 1
    }
    used = {el["attrs"]["data-stage-status"] for el in console.with_attr("data-stage")}
    assert keyed == used, f"legend keys {sorted(keyed)} do not match strip statuses {sorted(used)}"
    wording = text_of(legend).lower()
    assert "mixed" in wording
    assert "real gate" in wording, "the legend has to say what mixed means"
    assert "simulated action" in wording


def test_learn_stage_is_marked_not_implemented():
    learn = next(
        (el for el in console.with_attr("data-stage") if el["attrs"]["data-stage"] == "LEARN"),
        None,
    )
    assert learn is not None, "LEARN stage missing from the loop strip"
    assert learn["attrs"].get("data-stage-status") == "planned"
    assert "not implemented" in learn["text"].lower(), "LEARN must say it is not implemented"
    assert any(
        el["attrs"].get("data-stage-status") in ("real", "simulated")
        for el in console.with_attr("data-stage")
    )


def test_real_and_simulated_disclosure_is_present():
    body = asset("index.html").lower()
    assert "real nvidia inference" in body
    assert "safe simulated remediation" in body
    assert "simulated" in asset("app.js").lower(), "actions must be labelled simulated in the UI"


def test_disclosure_lists_the_real_and_simulated_halves_exactly():
    footer = next(el for el in console.elements if el["tag"] == "footer")
    columns = next(el for el in console.descendants(footer) if "disclosure-cols" in classes(el))
    groups = {}
    for column in columns["children"]:
        heading = next(child for child in column["children"] if child["tag"] == "h3")
        items = [
            text_of(li).lower()
            for child in column["children"]
            if child["tag"] == "ul"
            for li in child["children"]
        ]
        groups[text_of(heading).lower()] = items

    assert set(groups) == {"real", "simulated"}, groups.keys()
    real = " | ".join(groups["real"])
    simulated = " | ".join(groups["simulated"])
    for claim in ("nvidia", "policy", "approval state machine", "audit trail"):
        assert claim in real, f"{claim} is real and must stay in the REAL list"
    for claim in ("remediation execution", "before / after", "verification result"):
        assert claim in simulated, f"{claim} is simulated and must stay in the SIMULATED list"
    assert "approval" not in simulated, "the approval workflow is not simulated"


# -- contract drift --------------------------------------------------------


def test_action_labels_match_the_backend_action_surface():
    assert js_map_keys("ACTION_LABELS") == set(ActionName.__args__)


def test_audit_event_labels_cover_every_event_the_backend_emits():
    assert js_map_keys("AUDIT_LABELS") == backend_audit_events()


def test_severity_hint_options_match_the_backend_contract():
    options = console.with_attr("value")
    hints = {
        el["attrs"]["value"]
        for el in options
        if el["tag"] == "option" and el["attrs"]["value"] in SeverityHint.__args__
    }
    assert hints == set(SeverityHint.__args__)


def test_demo_incident_form_is_prefilled_and_valid():
    severity = console.value_of("f-severity")
    assert severity, "severity hint control has no prefilled value"
    form = IncidentEvent(
        source=console.value_of("f-source"),
        title=console.value_of("f-title"),
        description=console.value_of("f-description"),
        severity_hint=severity,
        evidence=[line.strip() for line in console.value_of("f-evidence").splitlines() if line.strip()],
    )
    assert form.model_dump() == DEMO_INCIDENT


def test_console_elements_have_ids_the_script_uses():
    referenced = set(
        re.findall(r"""(?:getElementById\(|byId\(\s*)["']([^"']+)["']""", asset("app.js"))
    )
    assert referenced, "app.js does not reference any element id"
    missing = referenced - console.ids()
    assert not missing, f"app.js targets ids absent from index.html: {sorted(missing)}"


# -- routes and secrets ----------------------------------------------------


def test_console_calls_only_documented_same_origin_routes():
    routes = js_routes()
    assert routes, "app.js performs no fetch()"
    documented = set(create_app().openapi()["paths"])
    normalised = {re.sub(r"\{[^}]+\}", "*", path) for path in documented}
    unknown = routes - normalised
    assert not unknown, f"console calls routes the API does not expose: {sorted(unknown)}"
    assert routes >= CORE_ROUTES, f"console must exercise the whole loop, missing: {sorted(CORE_ROUTES - routes)}"


def test_console_never_hardcodes_a_host_or_calls_the_provider():
    source = asset("app.js")
    assert source, "static/app.js is missing"
    assert not re.search(r"""["']https?://""", source), "fetches must be relative"
    assert "sentinel.novatechsystem.co.uk" not in source


@pytest.mark.parametrize("name", ASSETS)
def test_no_secret_material_or_hidden_reasoning_in_static_assets(name):
    source = asset(name)
    assert source, f"static/{name} is missing"
    for token in FORBIDDEN_IN_STATIC:
        assert token not in source, f"{token} found in static/{name}"


# -- the UI must not re-implement the backend ------------------------------


def test_audit_rendering_keeps_backend_append_order():
    source = asset("app.js")
    assert ".sort(" not in source, "audit order must stay the backend append order"
    assert ".reverse()" not in source, "audit order must stay the backend append order"


def test_ui_does_not_fake_progress_or_read_hidden_reasoning():
    source = asset("app.js")
    assert "reasoning_content" not in source
    assert not re.search(r"\bsetProgress\b|aria-valuenow", source), (
        "no fabricated completion indicator while the model is still running"
    )


def test_approval_gate_copy_does_not_imply_a_closed_incident_can_still_act():
    source = asset("app.js")
    assert "The approval gate is open for this incident." not in source, (
        "an executed incident is closed; gate copy must not read as still pending"
    )
    gate = source.split("function renderApproval")[1].split("function render")[0]
    assert "workflow.verification" in gate, (
        "the gate copy has to branch on whether the action already ran"
    )


def test_panels_stack_in_numbered_order_on_a_narrow_screen():
    css = asset("styles.css")
    narrow = css.split("@media (max-width: 60rem) {", 1)[1].split("\n}", 1)[0]
    assert "display: contents" in narrow, (
        "the two columns must dissolve so one column can be re-ordered"
    )
    ordered = dict(re.findall(r"#(panel-[a-z]+)\s*\{\s*order:\s*(\d+)", narrow))
    assert ordered == {
        "panel-incident": "1",
        "panel-assessment": "2",
        "panel-approval": "3",
        "panel-action": "4",
        "panel-verification": "5",
        "panel-audit": "6",
    }, "a phone must read OBSERVE → UNDERSTAND → DECIDE → ACT → VERIFY → AUDIT"
    assert set(ordered) == set(re.findall(r'class="panel" id="(panel-[a-z]+)"', asset("index.html"))), (
        "every panel needs a mobile order"
    )


@pytest.mark.parametrize("path", ["/", "/static/index.html"])
def test_console_is_reachable(path):
    assert request("GET", path).status_code == 200
