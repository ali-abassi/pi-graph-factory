"""Validate and normalize human-led, autonomous, and direct factory intake."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


INTAKE_MODES = ("direct", "interactive", "auto")
CORE_AREAS = {"intent", "audience", "scope", "experience", "taste", "architecture",
              "validation"}
INTERACTIVE_SECTIONS = {
    "Objective", "Definition Of Done", "Planning Posture", "Achievability Check",
    "Pass/Fail Checklist", "Deliverables", "Task Graph", "Orchestration Plan",
    "Validation", "Stop Conditions", "Ready-To-Run Goal Prompt",
}
AUTO_SECTIONS = {
    "Intent Read", "Status", "Resolved Direction", "Self-Grill Ledger",
    "Taste Direction", "Experience Architecture", "Product And Technical Architecture",
    "Execution Contract", "Assumptions", "Human-Only Decisions", "Ready-To-Run Prompt",
}


class IntakeError(ValueError):
    """The requested intake cannot safely enter planning."""


def _text(path: str, label: str) -> str:
    try:
        value = Path(path).expanduser().read_text(encoding="utf-8").strip()
    except OSError as error:
        raise IntakeError(f"cannot read {label}: {error}") from error
    if not value:
        raise IntakeError(f"{label} must not be empty")
    return value


def _sections(value: str, required: set[str], label: str) -> None:
    headings = set(re.findall(r"^##\s+(.+?)\s*$", value, flags=re.MULTILINE))
    if missing := sorted(required - headings):
        raise IntakeError(f"{label} is missing required sections: {', '.join(missing)}")


def _section(value: str, name: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(name)}\s*$\n(.*?)(?=^##\s|\Z)",
        value,
        flags=re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def _has_strings(value: dict[str, Any], fields: set[str]) -> bool:
    return all(isinstance(value.get(field), str) and value[field].strip() for field in fields)


def validate_auto_ledger(value: object) -> dict[str, Any]:
    """Enforce only the safety and completeness properties needed before planning."""

    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise IntakeError("auto intake ledger must be a schema_version 1 JSON object")
    if not _has_strings(value, {"goal", "intent_read"}):
        raise IntakeError("auto intake ledger needs a goal and intent_read")
    status = value.get("ready_status")
    if status == "human_decision_required":
        raise IntakeError(
            "auto intake has unresolved human-only decisions; resolve them interactively "
            "before initialization"
        )
    if status not in {"ready", "ready_with_assumptions"}:
        raise IntakeError("auto intake ready_status must be ready or ready_with_assumptions")
    if value.get("human_decisions") != []:
        raise IntakeError("auto intake must resolve or explicitly escalate human-only decisions")

    coverage = value.get("coverage")
    if not isinstance(coverage, list) or any(not isinstance(item, dict) for item in coverage):
        raise IntakeError("auto intake coverage must be an array of objects")
    if any(
        item.get("status") not in {"resolved", "assumed", "not_applicable"}
        or not _has_strings(item, {"area", "reason"})
        for item in coverage
    ):
        raise IntakeError("auto intake coverage needs a safe status and reason")
    areas = [item["area"] for item in coverage]
    if len(areas) != len(set(areas)) or not CORE_AREAS <= set(areas):
        raise IntakeError("auto intake needs each core coverage area exactly once")

    questions = value.get("questions")
    required = {"id", "area", "question", "answer", "basis", "would_overturn"}
    if not isinstance(questions, list) or not questions:
        raise IntakeError("auto intake questions must be a non-empty array")
    for item in questions:
        if not isinstance(item, dict) or not _has_strings(item, required):
            raise IntakeError("every auto intake question needs its decision evidence")
        if item.get("answer_type") not in {"fact", "inference", "default", "constraint"}:
            raise IntakeError(f"auto intake decision {item['id']} is invalid or human-only")
        confidence, reversibility = item.get("confidence"), item.get("reversibility")
        if confidence not in {"low", "medium", "high"} or reversibility not in {
            "easy", "moderate", "hard",
        }:
            raise IntakeError(f"auto intake decision {item['id']} has invalid risk metadata")
        if item.get("status") != "resolved" or (confidence == "low" and reversibility != "easy"):
            raise IntakeError(f"auto intake decision {item['id']} is not safely resolved")
        implications = item.get("implications")
        if not isinstance(implications, list) or not implications or not all(
            isinstance(detail, str) and detail.strip() for detail in implications
        ):
            raise IntakeError(f"auto intake decision {item['id']} needs implications")

    summary = value.get("decision_summary")
    summary_fields = {"point_of_view", "primary_user", "core_outcome", "signature_move",
                      "architecture"}
    if not isinstance(summary, dict) or not _has_strings(summary, summary_fields):
        raise IntakeError("auto intake decision_summary is incomplete")
    for field in ("non_goals", "quality_floor"):
        items = summary.get(field)
        if not isinstance(items, list) or not items or not all(
            isinstance(item, str) and item.strip() for item in items
        ):
            raise IntakeError(f"auto intake decision_summary {field} must be non-empty")
    return value


def resolve_intake(
    mode: str,
    request: str | None,
    request_file: str | None,
    ledger_file: str | None,
) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
    """Return the canonical request, provenance metadata, and optional ledger."""

    if mode == "direct":
        if ledger_file:
            raise IntakeError("direct intake does not accept --intake-ledger")
        value = _text(request_file, "request file") if request_file else (request or "").strip()
        if not value:
            raise IntakeError("request must not be empty")
        return value, {
            "mode": mode, "status": "ready", "artifact": "request.md", "summary": value,
        }, None
    if mode not in INTAKE_MODES:
        raise IntakeError(f"unsupported intake mode: {mode}")
    if request is not None or not request_file:
        raise IntakeError(f"{mode} intake requires a durable --request-file artifact")
    value = _text(request_file, f"{mode} intake brief")

    if mode == "interactive":
        if ledger_file:
            raise IntakeError("interactive intake does not accept --intake-ledger")
        _sections(value, INTERACTIVE_SECTIONS, "interactive intake brief")
        match = re.search(
            r"(?:^|\n)\s*[-*]?\s*Status:\s*(Ready With Assumptions|Ready|Not Goal-Ready)\b",
            value,
            flags=re.IGNORECASE,
        )
        if not match or match.group(1).lower() == "not goal-ready":
            raise IntakeError("interactive intake must declare a goal-ready status")
        status = match.group(1).lower().replace(" ", "_")
        return value, {
            "mode": mode, "status": status, "artifact": "goal-brief.md",
            "summary": _section(value, "Objective"),
        }, None

    _sections(value, AUTO_SECTIONS, "auto intake brief")
    if not ledger_file:
        raise IntakeError("auto intake requires --intake-ledger")
    try:
        ledger = validate_auto_ledger(json.loads(_text(ledger_file, "auto intake ledger")))
    except json.JSONDecodeError as error:
        raise IntakeError(f"auto intake ledger is invalid JSON: {error}") from error
    return value, {
        "mode": mode,
        "status": ledger["ready_status"],
        "artifact": "self-grilled-brief.md",
        "ledger": "self-grill.json",
        "summary": ledger["decision_summary"]["core_outcome"],
    }, ledger
