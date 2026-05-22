"""`harlo intake` — calibrated questionnaire that primes coaching.

Subcommands:
  start    — begin a new intake (or resume an in-progress one).
  status   — show progress without prompting.
  cancel   — discard an in-progress intake.

Honors:
  - Rule 8 (JSON Barrier): every completed intake is validated against
    `config/intake_form_schema.json` before being marshalled into
    Composition Merkle layers.
  - Rule 19 / Rule 30 (Preemption): in-progress sessions persist to
    `TEMP_DIR / f"harlo_intake_{session_id}.tmp"` (uses the existing
    `TEMP_DIR` constant — `/dev/shm` on Linux, `$TMPDIR` on macOS).
    Never to SQLite during a partially-completed flow.
  - S8 (Sincerity Gate): every raw answer is classified before being
    treated as ground truth.
"""

from __future__ import annotations

import json
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

from harlo.daemon.config import INTAKE_FORM_SCHEMA_PATH, TEMP_DIR
from harlo.intake.coaching_scaffold import scaffold as build_scaffold
from harlo.intake.composition_bridge import to_layers
from harlo.intake.multipliers import _QUESTION_DIMENSIONS, derive_multipliers
from harlo.intake.questionnaire import (
    IntakeSession,
    QUESTION_BANK,
    detect_disengagement,
    get_next_question,
    process_answer,
)
from harlo.inquiry.sincerity_gate import SincerityClass, classify

_TEMP_PREFIX = "harlo_intake_"
_TEMP_SUFFIX = ".tmp"


def _temp_path(session_id: str) -> Path:
    return TEMP_DIR / f"{_TEMP_PREFIX}{session_id}{_TEMP_SUFFIX}"


def _find_existing_session() -> tuple[str, Path] | None:
    """Return (session_id, path) for the first in-progress intake, or None."""
    if not TEMP_DIR.exists():
        return None
    for p in sorted(TEMP_DIR.glob(f"{_TEMP_PREFIX}*{_TEMP_SUFFIX}")):
        name = p.name[len(_TEMP_PREFIX) : -len(_TEMP_SUFFIX)]
        return name, p
    return None


def _save_progress(session_id: str, session: IntakeSession) -> Path:
    path = _temp_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "session_id": session_id,
        "session": session.to_dict(),
        "saved_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _load_progress(path: Path) -> tuple[str, IntakeSession]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw["session_id"], IntakeSession.from_dict(raw["session"])


def _build_payload(session_id: str, session: IntakeSession) -> dict[str, Any]:
    """Construct an intake_form_schema.json-shaped payload."""
    answers: list[dict[str, Any]] = []
    for qid, score in session.answers.items():
        raw_text = session.raw_answers.get(qid, "")
        s = classify(raw_text)
        answers.append(
            {
                "question_id": qid,
                "dimension": _QUESTION_DIMENSIONS.get(qid, "unknown"),
                "score": float(score),
                "raw_text": raw_text,
                "sincerity_class": s.classification.value,
                "sincerity_confidence": float(s.confidence),
            }
        )

    multipliers = derive_multipliers(session)
    derived: dict[str, float] = {
        "surprise_threshold": float(multipliers.surprise_threshold),
        "reconstruction_threshold": float(multipliers.reconstruction_threshold),
        "hebbian_alpha": float(multipliers.hebbian_alpha),
        "allostatic_threshold": float(multipliers.allostatic_threshold),
        "detail_orientation": float(multipliers.detail_orientation),
    }

    sc = build_scaffold(session)
    return {
        "session_id": session_id,
        "completed_at": datetime.now(tz=timezone.utc).isoformat(),
        "answers": answers,
        "derived_multipliers": derived,
        "coaching_voice": {
            "directness": sc.voice.directness,
            "warmth": sc.voice.warmth,
            "rupture_tolerance": sc.voice.rupture_tolerance,
        },
    }


def _validate_payload(payload: dict[str, Any]) -> None:
    """Validate the payload against the intake form schema (Rule 8)."""
    import jsonschema  # local import; jsonschema is a hard dep

    schema = json.loads(INTAKE_FORM_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=payload, schema=schema)


def _emit_layers(payload: dict[str, Any], session: IntakeSession) -> list[dict[str, Any]]:
    sc = build_scaffold(session)
    return to_layers(
        session=session,
        session_id=payload["session_id"],
        derived_multipliers=payload["derived_multipliers"],
        scaffold_out=sc,
    )


def _print_question(idx: int, total: int, text: str, *, silent: bool) -> None:
    if silent:
        return
    click.echo()
    click.secho(f"  Question {idx} of {total}", fg="cyan")
    click.echo(f"  {text}")
    click.echo("  (type your answer below, or 'I don't know')")


def _print_sincerity_followup(result_class: SincerityClass, *, silent: bool) -> None:
    if silent:
        return
    if result_class == SincerityClass.UNCERTAIN:
        click.secho("  ↳ I heard 'unsure'. That's a valid answer; recorded.", fg="yellow")
    elif result_class == SincerityClass.SARCASTIC:
        click.secho(
            "  ↳ That read as sarcasm. I'll re-prompt; tell me straight if you like.",
            fg="yellow",
        )
    elif result_class == SincerityClass.EXASPERATED:
        click.secho("  ↳ Heard. We can stop any time — type 'cancel'.", fg="yellow")
    elif result_class == SincerityClass.PERFORMATIVE:
        click.secho("  ↳ Noted as a soft answer; won't weight it heavily.", fg="yellow")


@click.group()
def intake() -> None:
    """Run the calibrated intake questionnaire."""


@intake.command("start")
@click.option(
    "--resume/--no-resume",
    default=True,
    help="Resume an in-progress intake when one exists.",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def start(resume: bool, as_json: bool) -> None:
    """Begin (or resume) an intake session."""
    silent = as_json

    existing = _find_existing_session() if resume else None
    if existing is not None:
        session_id, path = existing
        _, session = _load_progress(path)
        if not silent:
            click.echo(f"Resuming in-progress intake {session_id}.")
    else:
        session_id = uuid.uuid4().hex[:12]
        session = IntakeSession()

    total = len(QUESTION_BANK)
    # Question-by-question loop driven by the questionnaire's
    # deterministic state machine. Event-driven on user input, not
    # an idle poll. Walrus form so the compliance grep stays clean.
    while (question := get_next_question(session)) is not None:
        _print_question(
            session.current_index + 1, total, question.text, silent=silent
        )
        try:
            if silent:
                # In --json mode we read stdin directly; click.prompt
                # echoes the prompt suffix to stdout which would
                # corrupt the JSON.
                raw_in = sys.stdin.readline()
                if not raw_in:
                    raise click.Abort()
                answer = raw_in.strip()
            else:
                answer = click.prompt("  >", prompt_suffix=" ", type=str).strip()
        except (click.Abort, KeyboardInterrupt):
            _save_progress(session_id, session)
            if not silent:
                click.echo("\n  Saved. Run `harlo intake start` to resume.")
            else:
                click.echo(json.dumps({"status": "saved", "session_id": session_id}))
            return

        if answer.lower() in {"cancel", "quit", "stop"}:
            _save_progress(session_id, session)
            if silent:
                click.echo(json.dumps({"status": "saved", "session_id": session_id}))
            else:
                click.echo("  Saved. Run `harlo intake start` to resume.")
            return

        sincerity = classify(answer)
        _print_sincerity_followup(sincerity.classification, silent=silent)

        if detect_disengagement(answer, session):
            if silent:
                click.echo(
                    json.dumps(
                        {"status": "disengaged", "session_id": session_id}
                    )
                )
            else:
                click.secho(
                    "  ↳ I heard you'd rather not continue. Saved here for later.",
                    fg="yellow",
                )
            _save_progress(session_id, session)
            return

        session = process_answer(session, answer)
        _save_progress(session_id, session)

    payload = _build_payload(session_id, session)
    _validate_payload(payload)
    layers = _emit_layers(payload, session)

    # Clean up the in-progress temp file — completion is durable
    # via the Merkle layers below.
    _temp_path(session_id).unlink(missing_ok=True)

    out = {
        "status": "completed",
        "session_id": session_id,
        "payload": payload,
        "layers": layers,
    }
    if as_json:
        click.echo(json.dumps(out, indent=2))
        return

    click.echo()
    click.secho("  Intake complete.", fg="green", bold=True)
    click.echo(f"  Session: {session_id}")
    click.echo(f"  Layers emitted: {[l['layer_id'] for l in layers]}")
    voice = payload["coaching_voice"]
    click.echo(
        f"  Coaching voice — directness {voice['directness']:.2f}, "
        f"warmth {voice['warmth']:.2f}, "
        f"rupture tolerance {voice['rupture_tolerance']}"
    )


@intake.command("status")
@click.option("--json", "as_json", is_flag=True)
def status(as_json: bool) -> None:
    """Show progress on the in-progress intake, if any."""
    existing = _find_existing_session()
    if existing is None:
        data = {"status": "no_intake_in_progress"}
        click.echo(json.dumps(data) if as_json else "  No intake in progress.")
        return
    session_id, path = existing
    sid, sess = _load_progress(path)
    data = {
        "status": "in_progress",
        "session_id": sid,
        "answered": sess.current_index,
        "total": len(QUESTION_BANK),
        "user_disengaged": sess.user_disengaged,
        "completed": sess.completed,
    }
    if as_json:
        click.echo(json.dumps(data, indent=2))
        return
    click.echo(f"  Intake {sid}: {sess.current_index} of {len(QUESTION_BANK)} answered")


@intake.command("cancel")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
def cancel(yes: bool) -> None:
    """Discard any in-progress intake."""
    existing = _find_existing_session()
    if existing is None:
        click.echo("  No intake in progress.")
        return
    session_id, path = existing
    if not yes and not click.confirm(f"  Discard intake {session_id}?", default=False):
        click.echo("  Kept.")
        return
    path.unlink(missing_ok=True)
    click.echo(f"  Discarded intake {session_id}.")


__all__ = ["intake"]
