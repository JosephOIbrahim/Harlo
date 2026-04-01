""".usda text serialization for USD-Lite BrainStage.

Provides ``serialize()`` and ``parse()`` with round-trip guarantee:
``parse(serialize(stage)) == stage`` (using float-tolerant equality).

SDR arrays (2048-bit) are serialized as 512-char hex strings (Patch 9).
Floats always include a decimal point for unambiguous parsing.
Dicts and generic lists are JSON-encoded inline.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Optional

from .arc_types import ArcType
from .hex_sdr import sdr_to_hex, hex_to_sdr
from .prims import (
    ElenchusPrim,
    AssociationPrim,
    CognitiveProfilePrim,
    CompositionLayerPrim,
    CompositionPrim,
    GateStatusPrim,
    InquiryContainerPrim,
    InquiryPrim,
    IntakeHistoryPrim,
    MerkleRootPrim,
    MotorContainerPrim,
    MotorGateStatus,
    MotorPrim,
    MultipliersPrim,
    Provenance,
    RetrievalPath,
    SessionPrim,
    SkillPrim,
    SkillsContainerPrim,
    SourceType,
    TracePrim,
    VerificationState,
)
from .stage import BrainStage

# ---------------------------------------------------------------
# Serialize
# ---------------------------------------------------------------

_INDENT = "    "


def _fmt_float(v: float) -> str:
    """Format a float ensuring a decimal point is always present."""
    s = repr(v)
    if "." not in s and "e" not in s and "E" not in s and "inf" not in s.lower() and "nan" not in s.lower():
        s += ".0"
    return s


def _emit_attr(lines: list[str], depth: int, type_tok: str, name: str, value: str) -> None:
    """Append a typed attribute line."""
    indent = _INDENT * depth
    lines.append(f"{indent}{type_tok} {name} = {value}")


def _emit_block_open(lines: list[str], depth: int, type_name: str, prim_name: str) -> None:
    """Append a block opening line."""
    indent = _INDENT * depth
    lines.append(f"{indent}def {type_name} \"{prim_name}\"")
    lines.append(f"{indent}{{")


def _emit_block_close(lines: list[str], depth: int) -> None:
    """Append a block closing line."""
    lines.append(f"{_INDENT * depth}}}")


def _serialize_trace(lines: list[str], depth: int, trace: TracePrim) -> None:
    """Serialize a TracePrim."""
    _emit_block_open(lines, depth, "TracePrim", trace.trace_id)
    d = depth + 1
    _emit_attr(lines, d, "hex", "sdr", f"\"{sdr_to_hex(trace.sdr)}\"")
    _emit_attr(lines, d, "string", "content_hash", f"\"{trace.content_hash}\"")
    _emit_attr(lines, d, "float", "strength", _fmt_float(trace.strength))
    _emit_attr(lines, d, "token", "last_accessed", f"\"{trace.last_accessed.isoformat()}\"")
    if trace.co_activations:
        _emit_attr(lines, d, "dict", "co_activations", f"\"{json.dumps(trace.co_activations, sort_keys=True)}\"")
    if trace.competitions:
        _emit_attr(lines, d, "dict", "competitions", f"\"{json.dumps(trace.competitions, sort_keys=True)}\"")
    # Always serialize masks (they have default values)
    _emit_attr(lines, d, "hex", "hebbian_strengthen_mask", f"\"{sdr_to_hex(trace.hebbian_strengthen_mask)}\"")
    _emit_attr(lines, d, "hex", "hebbian_weaken_mask", f"\"{sdr_to_hex(trace.hebbian_weaken_mask)}\"")
    _emit_block_close(lines, depth)


def _serialize_provenance(lines: list[str], depth: int, prov: Provenance) -> None:
    """Serialize a Provenance block."""
    _emit_block_open(lines, depth, "Provenance", "provenance")
    d = depth + 1
    _emit_attr(lines, d, "token", "source_type", f"\"{prov.source_type.value}\"")
    _emit_attr(lines, d, "token", "origin_timestamp", f"\"{prov.origin_timestamp.isoformat()}\"")
    _emit_attr(lines, d, "string", "event_hash", f"\"{prov.event_hash}\"")
    _emit_attr(lines, d, "string", "session_id", f"\"{prov.session_id}\"")
    _emit_block_close(lines, depth)


def _serialize_layer(lines: list[str], depth: int, layer: CompositionLayerPrim) -> None:
    """Serialize a CompositionLayerPrim."""
    _emit_block_open(lines, depth, "CompositionLayerPrim", layer.layer_id)
    d = depth + 1
    _emit_attr(lines, d, "token", "arc_type", f"\"{layer.arc_type.name.lower()}\"")
    _emit_attr(lines, d, "dict", "opinion", f"\"{json.dumps(layer.opinion, sort_keys=True)}\"")
    _emit_attr(lines, d, "token", "timestamp", f"\"{layer.timestamp.isoformat()}\"")
    _emit_attr(lines, d, "bool", "permanent", "true" if layer.permanent else "false")
    if layer.provenance is not None:
        _serialize_provenance(lines, d, layer.provenance)
    _emit_block_close(lines, depth)


def _serialize_association(lines: list[str], depth: int, assoc: AssociationPrim) -> None:
    """Serialize the Association subtree."""
    _emit_block_open(lines, depth, "AssociationPrim", "Association")
    for trace_id in sorted(assoc.traces):
        _serialize_trace(lines, depth + 1, assoc.traces[trace_id])
    _emit_block_close(lines, depth)


def _serialize_composition(lines: list[str], depth: int, comp: CompositionPrim) -> None:
    """Serialize the Composition subtree."""
    _emit_block_open(lines, depth, "CompositionPrim", "Composition")
    for layer_id in sorted(comp.layers):
        _serialize_layer(lines, depth + 1, comp.layers[layer_id])
    _emit_block_close(lines, depth)


def _serialize_elenchus(lines: list[str], depth: int, ale: ElenchusPrim) -> None:
    """Serialize the Elenchus subtree."""
    _emit_block_open(lines, depth, "ElenchusPrim", "Elenchus")
    d = depth + 1
    if ale.gate_status is not None:
        gs = ale.gate_status
        _emit_block_open(lines, d, "GateStatusPrim", "GateStatus")
        d2 = d + 1
        _emit_attr(lines, d2, "token", "verification_state", f"\"{gs.verification_state.value}\"")
        _emit_attr(lines, d2, "int", "cycle_count", str(gs.cycle_count))
        _emit_attr(lines, d2, "token", "last_verified", f"\"{gs.last_verified.isoformat()}\"")
        _emit_block_close(lines, d)
    if ale.merkle_root is not None:
        mr = ale.merkle_root
        _emit_block_open(lines, d, "MerkleRootPrim", "MerkleRoot")
        d2 = d + 1
        _emit_attr(lines, d2, "string", "root_hash", f"\"{mr.root_hash}\"")
        _emit_attr(lines, d2, "int", "trace_count", str(mr.trace_count))
        _emit_block_close(lines, d)
    _emit_block_close(lines, depth)


def _serialize_session(lines: list[str], depth: int, sess: SessionPrim) -> None:
    """Serialize the Session subtree."""
    _emit_block_open(lines, depth, "SessionPrim", "Session")
    d = depth + 1
    _emit_attr(lines, d, "string", "current_session_id", f"\"{sess.current_session_id}\"")
    _emit_attr(lines, d, "int", "exchange_count", str(sess.exchange_count))
    _emit_attr(lines, d, "float", "surprise_rolling_mean", _fmt_float(sess.surprise_rolling_mean))
    _emit_attr(lines, d, "float", "surprise_rolling_std", _fmt_float(sess.surprise_rolling_std))
    _emit_attr(lines, d, "float", "last_query_surprise", _fmt_float(sess.last_query_surprise))
    _emit_attr(lines, d, "token", "last_retrieval_path", f"\"{sess.last_retrieval_path.value}\"")
    _emit_block_close(lines, depth)


def _serialize_inquiry(lines: list[str], depth: int, inq: InquiryContainerPrim) -> None:
    """Serialize the Inquiry subtree."""
    _emit_block_open(lines, depth, "InquiryContainerPrim", "Inquiry")
    for i, hyp in enumerate(inq.active):
        _emit_block_open(lines, depth + 1, "InquiryPrim", f"hypothesis_{i}")
        d2 = depth + 2
        _emit_attr(lines, d2, "string", "hypothesis", f"\"{hyp.hypothesis}\"")
        _emit_attr(lines, d2, "float", "confidence", _fmt_float(hyp.confidence))
        _emit_block_close(lines, depth + 1)
    _emit_block_close(lines, depth)


def _serialize_motor(lines: list[str], depth: int, motor: MotorContainerPrim) -> None:
    """Serialize the Motor subtree."""
    _emit_block_open(lines, depth, "MotorContainerPrim", "Motor")
    for i, mp in enumerate(motor.pending):
        _emit_block_open(lines, depth + 1, "MotorPrim", f"action_{i}")
        d2 = depth + 2
        _emit_attr(lines, d2, "string", "action", f"\"{mp.action}\"")
        _emit_attr(lines, d2, "token", "gate_status", f"\"{mp.gate_status.value}\"")
        _emit_block_close(lines, depth + 1)
    _emit_block_close(lines, depth)


def _serialize_skill(lines: list[str], depth: int, skill: SkillPrim) -> None:
    """Serialize a SkillPrim."""
    _emit_block_open(lines, depth, "SkillPrim", skill.domain)
    d = depth + 1
    _emit_attr(lines, d, "int", "trace_count", str(skill.trace_count))
    _emit_attr(lines, d, "token", "first_seen", f"\"{skill.first_seen.isoformat()}\"")
    _emit_attr(lines, d, "token", "last_seen", f"\"{skill.last_seen.isoformat()}\"")
    _emit_attr(lines, d, "float[]", "growth_arc", f"[{', '.join(_fmt_float(v) for v in skill.growth_arc)}]")
    _emit_attr(lines, d, "float", "hebbian_density", _fmt_float(skill.hebbian_density))
    _emit_block_close(lines, depth)


def _serialize_skills(lines: list[str], depth: int, skills: SkillsContainerPrim) -> None:
    """Serialize the Skills subtree."""
    _emit_block_open(lines, depth, "SkillsContainerPrim", "Skills")
    for domain in sorted(skills.domains):
        _serialize_skill(lines, depth + 1, skills.domains[domain])
    _emit_block_close(lines, depth)


def _serialize_cognitive_profile(lines: list[str], depth: int, cp: CognitiveProfilePrim) -> None:
    """Serialize the CognitiveProfile subtree."""
    _emit_block_open(lines, depth, "CognitiveProfilePrim", "CognitiveProfile")
    d = depth + 1
    # Multipliers
    m = cp.multipliers
    _emit_block_open(lines, d, "MultipliersPrim", "Multipliers")
    d2 = d + 1
    _emit_attr(lines, d2, "float", "surprise_threshold", _fmt_float(m.surprise_threshold))
    _emit_attr(lines, d2, "float", "reconstruction_threshold", _fmt_float(m.reconstruction_threshold))
    _emit_attr(lines, d2, "float", "hebbian_alpha", _fmt_float(m.hebbian_alpha))
    _emit_attr(lines, d2, "float", "allostatic_threshold", _fmt_float(m.allostatic_threshold))
    _emit_attr(lines, d2, "float", "detail_orientation", _fmt_float(m.detail_orientation))
    _emit_block_close(lines, d)
    # IntakeHistory
    ih = cp.intake_history
    _emit_block_open(lines, d, "IntakeHistoryPrim", "IntakeHistory")
    d2 = d + 1
    if ih.last_intake is not None:
        _emit_attr(lines, d2, "token", "last_intake", f"\"{ih.last_intake.isoformat()}\"")
    if ih.intake_version is not None:
        _emit_attr(lines, d2, "string", "intake_version", f"\"{ih.intake_version}\"")
    if ih.answer_embeddings:
        _emit_attr(lines, d2, "list", "answer_embeddings", f"\"{json.dumps(ih.answer_embeddings)}\"")
    _emit_block_close(lines, d)
    _emit_block_close(lines, depth)


def serialize(stage: BrainStage) -> str:
    """Serialize a BrainStage to .usda text format.

    Returns a complete .usda file as a string.
    None/empty optional fields are omitted from output.
    """
    lines: list[str] = ["#usda 1.0"]
    _emit_block_open(lines, 0, "BrainStage", "Brain")

    depth = 1
    _serialize_association(lines, depth, stage.association)
    _serialize_composition(lines, depth, stage.composition)
    _serialize_elenchus(lines, depth, stage.elenchus)
    if stage.session is not None:
        _serialize_session(lines, depth, stage.session)
    _serialize_inquiry(lines, depth, stage.inquiry)
    _serialize_motor(lines, depth, stage.motor)
    _serialize_skills(lines, depth, stage.skills)
    _serialize_cognitive_profile(lines, depth, stage.cognitive_profile)

    _emit_block_close(lines, 0)
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------
# Parse
# ---------------------------------------------------------------

# Regex patterns for parsing
_RE_HEADER = re.compile(r"^#usda\s+\d+\.\d+$")
_RE_DEF = re.compile(r'^(\s*)def\s+(\w+)\s+"([^"]*)"$')
_RE_OPEN = re.compile(r"^(\s*)\{$")
_RE_CLOSE = re.compile(r"^(\s*)\}$")
_RE_ATTR = re.compile(r'^(\s*)(\w+(?:\[\])?)\s+(\w+)\s*=\s*(.+)$')


def _parse_quoted(raw: str) -> str:
    """Extract value from a quoted string, handling the outer quotes."""
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    return raw


def _parse_float_array(raw: str) -> list[float]:
    """Parse a float[] value like ``[1.0, 2.0, 3.0]``."""
    raw = raw.strip()
    if raw == "[]":
        return []
    inner = raw.lstrip("[").rstrip("]")
    return [float(x.strip()) for x in inner.split(",") if x.strip()]


class _BlockParser:
    """Stateful parser that walks .usda lines and builds a BrainStage."""

    def __init__(self, lines: list[str]) -> None:
        self._lines = lines
        self._pos = 0

    def _peek(self) -> Optional[str]:
        if self._pos < len(self._lines):
            return self._lines[self._pos]
        return None

    def _advance(self) -> str:
        line = self._lines[self._pos]
        self._pos += 1
        return line

    def _skip_empty(self) -> None:
        while self._pos < len(self._lines) and self._lines[self._pos].strip() == "":
            self._pos += 1

    def _expect_open(self) -> None:
        """Consume the opening brace line."""
        self._skip_empty()
        line = self._advance()
        if not _RE_OPEN.match(line):
            raise ValueError(f"Expected '{{' but got: {line!r}")

    def _parse_attrs_and_children(self) -> tuple[dict[str, tuple[str, str]], list[tuple[str, str, object]]]:
        """Parse attributes and child blocks until a closing brace.

        Returns (attrs, children) where:
          attrs = {name: (type_tok, raw_value)}
          children = [(type_name, prim_name, parsed_object)]
        """
        attrs: dict[str, tuple[str, str]] = {}
        children: list[tuple[str, str, object]] = []

        for _ in iter(int, 1):  # bounded by _pos reaching end of lines
            self._skip_empty()
            line = self._peek()
            if line is None:
                raise ValueError("Unexpected end of input, expected '}'")

            if _RE_CLOSE.match(line):
                self._advance()
                return attrs, children

            m_def = _RE_DEF.match(line)
            if m_def:
                self._advance()
                type_name = m_def.group(2)
                prim_name = m_def.group(3)
                self._expect_open()
                child_attrs, child_children = self._parse_attrs_and_children()
                children.append((type_name, prim_name, (child_attrs, child_children)))
                continue

            m_attr = _RE_ATTR.match(line)
            if m_attr:
                self._advance()
                type_tok = m_attr.group(2)
                name = m_attr.group(3)
                raw_val = m_attr.group(4)
                attrs[name] = (type_tok, raw_val)
                continue

            # Skip unknown lines
            self._advance()

    def parse(self) -> BrainStage:
        """Parse the full .usda text into a BrainStage."""
        # Header
        self._skip_empty()
        header = self._advance()
        if not _RE_HEADER.match(header.strip()):
            raise ValueError(f"Expected #usda header, got: {header!r}")

        # Root block: def BrainStage "Brain"
        self._skip_empty()
        line = self._advance()
        m = _RE_DEF.match(line)
        if not m or m.group(2) != "BrainStage":
            raise ValueError(f"Expected BrainStage definition, got: {line!r}")

        self._expect_open()
        _, children = self._parse_attrs_and_children()

        stage = BrainStage()
        for type_name, prim_name, data in children:
            attrs, sub_children = data  # type: ignore[misc]
            if type_name == "AssociationPrim":
                stage.association = _build_association(sub_children)
            elif type_name == "CompositionPrim":
                stage.composition = _build_composition(sub_children)
            elif type_name == "ElenchusPrim":
                stage.elenchus = _build_elenchus(sub_children)
            elif type_name == "SessionPrim":
                stage.session = _build_session(attrs)
            elif type_name == "InquiryContainerPrim":
                stage.inquiry = _build_inquiry(sub_children)
            elif type_name == "MotorContainerPrim":
                stage.motor = _build_motor(sub_children)
            elif type_name == "SkillsContainerPrim":
                stage.skills = _build_skills(sub_children)
            elif type_name == "CognitiveProfilePrim":
                stage.cognitive_profile = _build_cognitive_profile(sub_children)

        return stage


# ---------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------

def _get_str(attrs: dict, name: str, default: str = "") -> str:
    if name not in attrs:
        return default
    return _parse_quoted(attrs[name][1])


def _get_int(attrs: dict, name: str, default: int = 0) -> int:
    if name not in attrs:
        return default
    return int(attrs[name][1].strip())


def _get_float(attrs: dict, name: str, default: float = 0.0) -> float:
    if name not in attrs:
        return default
    return float(attrs[name][1].strip())


def _get_token(attrs: dict, name: str, default: str = "") -> str:
    if name not in attrs:
        return default
    return _parse_quoted(attrs[name][1])


def _get_hex_sdr(attrs: dict, name: str) -> list[int]:
    if name not in attrs:
        return [0] * 2048
    return hex_to_sdr(_parse_quoted(attrs[name][1]))


def _get_dict(attrs: dict, name: str) -> dict:
    if name not in attrs:
        return {}
    return json.loads(_parse_quoted(attrs[name][1]))


def _get_float_array(attrs: dict, name: str) -> list[float]:
    if name not in attrs:
        return []
    return _parse_float_array(attrs[name][1])


def _get_list(attrs: dict, name: str) -> list:
    if name not in attrs:
        return []
    return json.loads(_parse_quoted(attrs[name][1]))


def _get_bool(attrs: dict, name: str, default: bool = False) -> bool:
    if name not in attrs:
        return default
    return attrs[name][1].strip().lower() == "true"


def _build_association(children: list) -> AssociationPrim:
    """Build AssociationPrim from parsed children."""
    traces: dict[str, TracePrim] = {}
    for type_name, prim_name, data in children:
        if type_name == "TracePrim":
            attrs, _ = data
            traces[prim_name] = TracePrim(
                trace_id=prim_name,
                sdr=_get_hex_sdr(attrs, "sdr"),
                content_hash=_get_str(attrs, "content_hash"),
                strength=_get_float(attrs, "strength"),
                last_accessed=datetime.fromisoformat(_get_token(attrs, "last_accessed")),
                co_activations=_get_dict(attrs, "co_activations"),
                competitions=_get_dict(attrs, "competitions"),
                hebbian_strengthen_mask=_get_hex_sdr(attrs, "hebbian_strengthen_mask"),
                hebbian_weaken_mask=_get_hex_sdr(attrs, "hebbian_weaken_mask"),
            )
    return AssociationPrim(traces=traces)


def _build_provenance(children: list) -> Optional[Provenance]:
    """Build Provenance from parsed children."""
    for type_name, prim_name, data in children:
        if type_name == "Provenance" and prim_name == "provenance":
            attrs, _ = data
            return Provenance(
                source_type=SourceType(_get_token(attrs, "source_type")),
                origin_timestamp=datetime.fromisoformat(_get_token(attrs, "origin_timestamp")),
                event_hash=_get_str(attrs, "event_hash"),
                session_id=_get_str(attrs, "session_id"),
            )
    return None


def _build_composition(children: list) -> CompositionPrim:
    """Build CompositionPrim from parsed children."""
    layers: dict[str, CompositionLayerPrim] = {}
    for type_name, prim_name, data in children:
        if type_name == "CompositionLayerPrim":
            attrs, sub_children = data
            arc_name = _get_token(attrs, "arc_type")
            layers[prim_name] = CompositionLayerPrim(
                layer_id=prim_name,
                arc_type=ArcType[arc_name.upper()],
                opinion=_get_dict(attrs, "opinion"),
                timestamp=datetime.fromisoformat(_get_token(attrs, "timestamp")),
                provenance=_build_provenance(sub_children),
                permanent=_get_bool(attrs, "permanent"),
            )
    return CompositionPrim(layers=layers)


def _build_elenchus(children: list) -> ElenchusPrim:
    """Build ElenchusPrim from parsed children."""
    gate_status = None
    merkle_root = None
    for type_name, prim_name, data in children:
        attrs, _ = data
        if type_name == "GateStatusPrim":
            gate_status = GateStatusPrim(
                verification_state=VerificationState(_get_token(attrs, "verification_state")),
                cycle_count=_get_int(attrs, "cycle_count"),
                last_verified=datetime.fromisoformat(_get_token(attrs, "last_verified")),
            )
        elif type_name == "MerkleRootPrim":
            merkle_root = MerkleRootPrim(
                root_hash=_get_str(attrs, "root_hash"),
                trace_count=_get_int(attrs, "trace_count"),
            )
    return ElenchusPrim(gate_status=gate_status, merkle_root=merkle_root)


def _build_session(attrs: dict) -> SessionPrim:
    """Build SessionPrim from parsed attributes."""
    return SessionPrim(
        current_session_id=_get_str(attrs, "current_session_id"),
        exchange_count=_get_int(attrs, "exchange_count"),
        surprise_rolling_mean=_get_float(attrs, "surprise_rolling_mean"),
        surprise_rolling_std=_get_float(attrs, "surprise_rolling_std"),
        last_query_surprise=_get_float(attrs, "last_query_surprise"),
        last_retrieval_path=RetrievalPath(_get_token(attrs, "last_retrieval_path", "system_1")),
    )


def _build_inquiry(children: list) -> InquiryContainerPrim:
    """Build InquiryContainerPrim from parsed children."""
    active: list[InquiryPrim] = []
    for type_name, prim_name, data in children:
        if type_name == "InquiryPrim":
            attrs, _ = data
            active.append(InquiryPrim(
                hypothesis=_get_str(attrs, "hypothesis"),
                confidence=_get_float(attrs, "confidence"),
            ))
    return InquiryContainerPrim(active=active)


def _build_motor(children: list) -> MotorContainerPrim:
    """Build MotorContainerPrim from parsed children."""
    pending: list[MotorPrim] = []
    for type_name, prim_name, data in children:
        if type_name == "MotorPrim":
            attrs, _ = data
            pending.append(MotorPrim(
                action=_get_str(attrs, "action"),
                gate_status=MotorGateStatus(_get_token(attrs, "gate_status")),
            ))
    return MotorContainerPrim(pending=pending)


def _build_skills(children: list) -> SkillsContainerPrim:
    """Build SkillsContainerPrim from parsed children."""
    domains: dict[str, SkillPrim] = {}
    for type_name, prim_name, data in children:
        if type_name == "SkillPrim":
            attrs, _ = data
            domains[prim_name] = SkillPrim(
                domain=prim_name,
                trace_count=_get_int(attrs, "trace_count"),
                first_seen=datetime.fromisoformat(_get_token(attrs, "first_seen")),
                last_seen=datetime.fromisoformat(_get_token(attrs, "last_seen")),
                growth_arc=_get_float_array(attrs, "growth_arc"),
                hebbian_density=_get_float(attrs, "hebbian_density"),
            )
    return SkillsContainerPrim(domains=domains)


def _build_cognitive_profile(children: list) -> CognitiveProfilePrim:
    """Build CognitiveProfilePrim from parsed children."""
    multipliers = MultipliersPrim()
    intake_history = IntakeHistoryPrim()
    for type_name, prim_name, data in children:
        attrs, _ = data
        if type_name == "MultipliersPrim":
            multipliers = MultipliersPrim(
                surprise_threshold=_get_float(attrs, "surprise_threshold", 2.0),
                reconstruction_threshold=_get_float(attrs, "reconstruction_threshold", 0.3),
                hebbian_alpha=_get_float(attrs, "hebbian_alpha", 0.01),
                allostatic_threshold=_get_float(attrs, "allostatic_threshold", 1.0),
                detail_orientation=_get_float(attrs, "detail_orientation", 0.5),
            )
        elif type_name == "IntakeHistoryPrim":
            li_str = _get_token(attrs, "last_intake", "")
            intake_history = IntakeHistoryPrim(
                last_intake=datetime.fromisoformat(li_str) if li_str else None,
                intake_version=_get_str(attrs, "intake_version", "") or None,
                answer_embeddings=_get_list(attrs, "answer_embeddings"),
            )
    return CognitiveProfilePrim(multipliers=multipliers, intake_history=intake_history)


# ---------------------------------------------------------------
# Public parse function
# ---------------------------------------------------------------


def parse(usda_text: str) -> BrainStage:
    """Parse a .usda text string back into a BrainStage.

    Raises ValueError on malformed input.
    Missing optional fields default to their dataclass defaults.
    """
    lines = usda_text.splitlines()
    parser = _BlockParser(lines)
    return parser.parse()
