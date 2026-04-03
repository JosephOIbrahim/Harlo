"""Incremental skills observer — ghost window compliant.

Patch 10: Cursor-based incremental processing. Only computes clustering
for traces newer than last_processed_timestamp. O(new_traces) per run.
Cursor persisted in SQLite alongside /Skills data.

Runs during the 30-second ghost window (Rule 33 compliant).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from ..usd_lite.prims import SkillPrim, SkillsContainerPrim, TracePrim


@dataclass
class ObserverCursor:
    """Persisted cursor for incremental processing."""
    last_processed_timestamp: datetime
    total_processed: int

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "last_processed_timestamp": self.last_processed_timestamp.isoformat(),
            "total_processed": self.total_processed,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ObserverCursor:
        """Deserialize from dict."""
        return cls(
            last_processed_timestamp=datetime.fromisoformat(d["last_processed_timestamp"]),
            total_processed=d.get("total_processed", 0),
        )


def initial_cursor() -> ObserverCursor:
    """Create a cursor at the epoch (processes everything on first run)."""
    return ObserverCursor(
        last_processed_timestamp=datetime(1970, 1, 1, tzinfo=timezone.utc),
        total_processed=0,
    )


def observe_traces(
    traces: dict[str, TracePrim],
    existing_skills: SkillsContainerPrim,
    cursor: ObserverCursor,
) -> tuple[SkillsContainerPrim, ObserverCursor]:
    """Incrementally observe traces and update skills.

    Only processes traces with last_accessed > cursor.last_processed_timestamp.
    Returns updated skills and new cursor position.

    Ghost window compliant: O(new_traces), not O(all_traces).
    """
    # Filter to new traces only
    new_traces = {
        tid: t for tid, t in traces.items()
        if t.last_accessed > cursor.last_processed_timestamp
    }

    if not new_traces:
        return existing_skills, cursor

    # Group new traces by domain (using content_hash prefix as domain proxy)
    domain_traces: dict[str, list[TracePrim]] = defaultdict(list)
    for tid, trace in new_traces.items():
        domain = _extract_domain(trace)
        domain_traces[domain].append(trace)

    # Update existing skills with new observations
    updated_domains = dict(existing_skills.domains)

    for domain, traces_list in domain_traces.items():
        if domain in updated_domains:
            skill = updated_domains[domain]
            updated_domains[domain] = _update_skill(skill, traces_list)
        else:
            updated_domains[domain] = _create_skill(domain, traces_list)

    # Compute new cursor position
    latest_ts = max(t.last_accessed for t in new_traces.values())
    new_cursor = ObserverCursor(
        last_processed_timestamp=latest_ts,
        total_processed=cursor.total_processed + len(new_traces),
    )

    return SkillsContainerPrim(domains=updated_domains), new_cursor


def query_skills(
    skills: SkillsContainerPrim,
    query: str,
) -> dict:
    """Query the skills model with natural language patterns.

    Patterns:
    - "what am I getting better at?" → domains with positive growth arcs
    - "what am I avoiding?" → domains with gap/avoidance signals
    - "how deep is my knowledge of X?" → specific domain analysis
    - "what should I work on?" → prioritized growth recommendations

    Returns JSON-serializable dict.
    """
    query_lower = query.lower()

    if any(w in query_lower for w in ["getting better", "improving", "growing", "progress"]):
        return _query_growing(skills)
    elif any(w in query_lower for w in ["avoiding", "gap", "weakness", "neglect"]):
        return _query_gaps(skills)
    elif any(w in query_lower for w in ["deep", "knowledge of", "how much", "expertise"]):
        return _query_depth(skills, query)
    elif any(w in query_lower for w in ["should", "work on", "recommend", "focus"]):
        return _query_recommendations(skills)
    else:
        return _query_overview(skills)


# ---------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------


def _extract_domain(trace: TracePrim) -> str:
    """Extract domain from trace metadata.

    Uses content_hash prefix as a domain proxy. In production,
    this would use the trace's domain tag from SQLite.
    """
    # Simple hash-based bucketing for now
    h = trace.content_hash
    if not h:
        return "general"
    # Use first 4 chars of hash as domain bucket
    return f"domain_{h[:4]}"


def _create_skill(domain: str, traces: list[TracePrim]) -> SkillPrim:
    """Create a new SkillPrim from observed traces."""
    strengths = [t.strength for t in traces]
    first = min(t.last_accessed for t in traces)
    last = max(t.last_accessed for t in traces)
    return SkillPrim(
        domain=domain,
        trace_count=len(traces),
        first_seen=first,
        last_seen=last,
        growth_arc=strengths,
        hebbian_density=0.0,
    )


def _update_skill(skill: SkillPrim, new_traces: list[TracePrim]) -> SkillPrim:
    """Update an existing SkillPrim with new observations."""
    new_strengths = [t.strength for t in new_traces]
    last = max(t.last_accessed for t in new_traces)
    return SkillPrim(
        domain=skill.domain,
        trace_count=skill.trace_count + len(new_traces),
        first_seen=skill.first_seen,
        last_seen=max(skill.last_seen, last),
        growth_arc=skill.growth_arc + new_strengths,
        hebbian_density=skill.hebbian_density,
    )


def _query_growing(skills: SkillsContainerPrim) -> dict:
    """Find domains with positive growth arcs."""
    growing = []
    for domain, skill in sorted(skills.domains.items()):
        if len(skill.growth_arc) >= 2:
            trend = skill.growth_arc[-1] - skill.growth_arc[0]
            if trend > 0:
                growing.append({
                    "domain": domain,
                    "trace_count": skill.trace_count,
                    "trend": round(trend, 4),
                    "growth_arc": skill.growth_arc[-5:],  # Last 5 points
                })
    return {
        "query_type": "growing",
        "domains": growing,
        "summary": f"{len(growing)} domain(s) showing positive growth",
    }


def _query_gaps(skills: SkillsContainerPrim) -> dict:
    """Find domains with decaying traces or no recent activity."""
    gaps = []
    for domain, skill in sorted(skills.domains.items()):
        if len(skill.growth_arc) >= 2:
            trend = skill.growth_arc[-1] - skill.growth_arc[0]
            if trend < 0:
                gaps.append({
                    "domain": domain,
                    "trace_count": skill.trace_count,
                    "trend": round(trend, 4),
                    "last_seen": skill.last_seen.isoformat(),
                })
    return {
        "query_type": "gaps",
        "domains": gaps,
        "summary": f"{len(gaps)} domain(s) showing decline",
    }


def _query_depth(skills: SkillsContainerPrim, query: str) -> dict:
    """Analyze a specific domain's depth."""
    # Try to find the domain mentioned in the query
    query_lower = query.lower()
    best_match = None
    for domain, skill in skills.domains.items():
        if domain.lower() in query_lower or query_lower in domain.lower():
            best_match = skill
            break

    if best_match is None:
        # Return the most active domain
        if skills.domains:
            best_match = max(skills.domains.values(), key=lambda s: s.trace_count)
        else:
            return {"query_type": "depth", "domain": None, "summary": "No skills data available"}

    return {
        "query_type": "depth",
        "domain": best_match.domain,
        "trace_count": best_match.trace_count,
        "first_seen": best_match.first_seen.isoformat(),
        "last_seen": best_match.last_seen.isoformat(),
        "growth_arc": best_match.growth_arc[-10:],
        "hebbian_density": best_match.hebbian_density,
        "summary": f"Domain '{best_match.domain}': {best_match.trace_count} traces",
    }


def _query_recommendations(skills: SkillsContainerPrim) -> dict:
    """Prioritized growth recommendations."""
    recommendations = []
    for domain, skill in sorted(skills.domains.items()):
        score = skill.trace_count * (1.0 + skill.hebbian_density)
        if len(skill.growth_arc) >= 2:
            trend = skill.growth_arc[-1] - skill.growth_arc[0]
            if trend < 0:
                score *= 2.0  # Boost declining domains
        recommendations.append({
            "domain": domain,
            "priority_score": round(score, 4),
            "trace_count": skill.trace_count,
            "reason": "declining" if len(skill.growth_arc) >= 2 and skill.growth_arc[-1] < skill.growth_arc[0] else "active",
        })
    recommendations.sort(key=lambda r: r["priority_score"], reverse=True)
    return {
        "query_type": "recommendations",
        "domains": recommendations[:5],
        "summary": f"Top {min(5, len(recommendations))} recommendation(s)",
    }


def _query_overview(skills: SkillsContainerPrim) -> dict:
    """General overview of all skills."""
    domains = []
    for domain, skill in sorted(skills.domains.items()):
        domains.append({
            "domain": domain,
            "trace_count": skill.trace_count,
            "last_seen": skill.last_seen.isoformat(),
        })
    return {
        "query_type": "overview",
        "domains": domains,
        "total_domains": len(domains),
        "summary": f"{len(domains)} domain(s) tracked",
    }
