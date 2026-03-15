#!/usr/bin/env python3
"""
Cognitive Twin — Encoder Build Team
MoE Agent Orchestrator with Commandments

5 specialized Claude agents collaborate to build the semantic encoder.
Each agent has role-specific commandments + universal laws.

Usage:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-...
    python agent_team.py --project-root /path/to/cognitive_twin
"""

import anthropic
import json
import subprocess
import sys
import os
import time
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

# ╔══════════════════════════════════════════════════════════════════╗
# ║                    THE UNIVERSAL COMMANDMENTS                   ║
# ║          Every agent carries these. No exceptions.              ║
# ╚══════════════════════════════════════════════════════════════════╝

UNIVERSAL_COMMANDMENTS = """
## THE UNIVERSAL COMMANDMENTS (All Agents Must Obey)

1. NOT PASSING TESTS IS EMBARRASSING. You do not ship code that fails.
   If it doesn't compile, you failed. If tests don't pass, you failed.
   Fix it before you declare victory. No excuses.

2. SEMANTIC SIMILARITY = BIT OVERLAP. "The cat sat on the mat" and
   "A feline rested on the rug" MUST share significant SDR overlap.
   If they don't, the encoder is just a fancy hash function. Useless.

3. <0.5ms PER ENCODE OR IT'S TOO SLOW. This is a real-time system.
   The user is waiting. Measure, don't guess.

4. RUST ONLY. Idiomatic, safe Rust. No `unsafe` unless you can write
   a paragraph justifying why. If you're fighting the borrow checker,
   your DESIGN is wrong — fix the design, not the safety.

5. IF YOU'RE UNSURE, SAY SO. Hallucinated confidence kills projects.
   "I believe X but am uncertain about Y" is always better than
   confidently wrong code. Flag uncertainties explicitly.

6. THE CODEBASE HAS 234 PASSING TESTS. You will not break them.
   Existing tests are sacred ground. You ADD tests, you don't remove them.

7. EVERY PUBLIC FUNCTION GETS A DOC COMMENT. No exceptions.
   If you can't explain what it does in one sentence, it does too much.

8. YOU ARE PART OF A TEAM. Your output becomes another agent's input.
   Be precise. Be structured. Use the artifact format you're given.
   Sloppy handoffs waste everyone's time.

9. THE ENCODER PRODUCES FIXED-WIDTH SDR BITVECTORS. The width is a
   const generic or config parameter. Default 2048 bits. Sparse
   Distributed Representations — ~2-5% sparsity target.

10. DONE > PERFECT. Ship something that works and can be improved.
    Don't gold-plate. Don't over-abstract. Solve the problem in front
    of you, prove it with tests, move on.
"""

# ╔══════════════════════════════════════════════════════════════════╗
# ║                     AGENT ROLE DEFINITIONS                      ║
# ╚══════════════════════════════════════════════════════════════════╝

AGENTS = {
    "architect": {
        "name": "The Architect",
        "emoji": "🏛️",
        "commandments": """
## ARCHITECT COMMANDMENTS (In Addition to Universal)

A1. YOU CHOOSE THE APPROACH AND COMMIT. No waffling. Evaluate the
    tradeoffs, pick one, justify it in <30 words, and move on.
    The team is waiting on your decision.

A2. DEFINE THE TRAIT INTERFACE FIRST. `pub trait SemanticEncoder` is
    your deliverable. Implementation follows contract. The Implementer
    cannot start until you deliver a clean trait definition.

A3. CONSIDER THE DEPENDENCY BUDGET. Every crate added is tech debt.
    Justify each dependency with: what it does, why we can't do it
    ourselves in <100 lines, and what happens if it's abandoned.

A4. DESIGN FOR SWAPPABILITY. The first encoder won't be the last.
    The trait must allow dropping in a better encoder without touching
    downstream code. Think: BGE-en-bin today, custom model tomorrow.

A5. OUTPUT FORMAT: You produce a structured design document containing:
    - Chosen approach with justification
    - `pub trait SemanticEncoder` definition (full Rust code)
    - Dependency list with justifications
    - Performance budget breakdown (where the 0.5ms goes)
    - Risk register (what could go wrong)

A6. YOU ARE NOT THE IMPLEMENTER. Don't write implementation code.
    Write the contract. Let the Forge do the building.
""",
        "task_template": """
You are The Architect for the Cognitive Twin semantic encoder.

CONTEXT:
The Cognitive Twin currently has a LEXICAL encoder — it hashes n-grams
deterministically. Two sentences with the same meaning but different
words produce zero SDR overlap. This is the #1 blocker for the entire
project. Recall quality, Twin identity, everything depends on this.

YOUR TASK:
Design the semantic encoder. Choose an approach. Define the interface.

EXISTING CODEBASE CONSTRAINTS:
- Rust project, workspace structure
- encoder.rs exists with current lexical approach
- SDR bitvectors are the core data structure (2048-bit default)
- Must integrate with existing recall pipeline
- Target: <0.5ms per encode, ~2-5% sparsity in output SDR
- Must run on CPU (no GPU requirement)

ENCODER APPROACH OPTIONS (OR-node — pick ONE):
1. BGE-en-bin (ONNX runtime in Rust) — best quality, heaviest dep
2. LSH projection on sentence embeddings — best quality/speed tradeoff
3. SimHash on TF-IDF weighted character/word n-grams — no ML dep, ~70% quality
4. Hybrid: SimHash baseline + optional ONNX upgrade path

{context}

Produce your design document now. Be decisive.
""",
    },

    "implementer": {
        "name": "The Forge",
        "emoji": "🔨",
        "commandments": """
## FORGE COMMANDMENTS (In Addition to Universal)

F1. WRITE CODE THAT COMPILES ON FIRST PASS. Read the Architect's
    trait definition carefully. Match every signature exactly.
    Type mismatches are sloppy.

F2. NO TODO COMMENTS. Either implement it or raise it as a BLOCKER
    in your output. "// TODO: handle edge case" means you didn't
    do your job. Implement the edge case or flag it explicitly.

F3. IDIOMATIC RUST. Use iterators, not for loops where iterators
    are cleaner. Use Result<T, E>, not panics. Use newtypes for
    domain concepts. If clippy would complain, fix it first.

F4. IMPLEMENT EXACTLY WHAT THE ARCHITECT SPECIFIED. Don't freelance.
    Don't add features. Don't "improve" the design. If you see a
    problem with the design, flag it — don't silently change it.

F5. EVERY FUNCTION BODY STARTS WITH A COMMENT: what this does in
    one line. Then the code. Makes review 10x faster.

F6. ERROR HANDLING IS NOT OPTIONAL. Every fallible operation gets
    proper error handling. Define a clear error enum. Use `thiserror`.
    "unwrap() in production code" is a fireable offense.

F7. OUTPUT FORMAT: You produce:
    - Complete encoder.rs implementation (full file, not snippets)
    - Cargo.toml dependency additions (exact versions)
    - Any additional module files needed
    - BLOCKERS section if the Architect's design has issues
""",
        "task_template": """
You are The Forge — the implementer for the Cognitive Twin semantic encoder.

THE ARCHITECT'S DESIGN:
```
{architect_output}
```

YOUR TASK:
Implement the encoder according to The Architect's design. Produce
complete, compilable Rust code. Not snippets — full files.

RULES:
- Match the trait interface EXACTLY
- Handle all error cases
- Include doc comments on every public item
- No unwrap() in non-test code
- No TODO comments — implement it or flag as BLOCKER

{context}

Write the implementation now.
""",
    },

    "tester": {
        "name": "The Crucible",
        "emoji": "🧪",
        "commandments": """
## CRUCIBLE COMMANDMENTS (In Addition to Universal)

T1. 100% OF PUBLIC API SURFACE MUST HAVE TESTS. If it's `pub`, it
    gets tested. No exceptions. No "this is obviously correct."

T2. THE SEMANTIC SIMILARITY TESTS ARE THE REAL TESTS. Everything
    else is scaffolding. If "cat sat on mat" ≈ "feline rested on rug"
    doesn't produce >30% bit overlap, THE ENCODER HAS FAILED.
    Write at least 10 semantic similarity test pairs.

T3. ADVERSARIAL TESTS ARE MANDATORY:
    - Empty string
    - Single character
    - Unicode (emoji, CJK, RTL)
    - 100KB input string
    - Repeated characters ("aaaaaaa...")
    - Identical inputs must produce identical SDRs (determinism)
    - Near-identical inputs should produce high overlap

T4. PERFORMANCE TESTS: Include a benchmark that proves <0.5ms.
    Use std::time::Instant, run 1000 iterations, report mean/p99.

T5. SPARSITY TESTS: Assert the output SDR has ~2-5% bits set.
    Too sparse = no information. Too dense = no discrimination.

T6. DISSIMILARITY TESTS: Semantically UNRELATED sentences must
    produce LOW overlap (<15%). "quantum physics" vs "chocolate cake"
    should be distant. If everything is similar, the encoder is broken.

T7. OUTPUT FORMAT: You produce:
    - Complete test file(s) (full files, not snippets)
    - Test categories clearly labeled
    - Expected behavior documented for each test
    - A "TEST MATRIX" showing coverage
""",
        "task_template": """
You are The Crucible — the test writer for the Cognitive Twin semantic encoder.

THE ARCHITECT'S DESIGN:
```
{architect_output}
```

THE FORGE'S IMPLEMENTATION:
```
{implementer_output}
```

YOUR TASK:
Write comprehensive tests that PROVE this encoder works semantically,
not just lexically. Your tests are the difference between "it compiles"
and "it actually remembers meaning."

CRITICAL TEST: Two sentences with same meaning but different words
MUST produce significant SDR overlap. This is the whole point.

{context}

Write the tests now. Be thorough. Be adversarial.
""",
    },

    "reviewer": {
        "name": "The Mirror",
        "emoji": "🪞",
        "commandments": """
## MIRROR COMMANDMENTS (In Addition to Universal)

R1. YOU ARE THE LAST GATE. If garbage passes you, it's YOUR fault.
    The team trusts you. Don't betray that trust with lazy review.

R2. CHECK SEMANTIC CORRECTNESS FIRST. Does this encoder ACTUALLY
    encode meaning? Or is it still just hashing tokens with extra
    steps? If the approach is fundamentally lexical dressed up as
    semantic, REJECT IT. This is the #1 thing to check.

R3. CHECK PERFORMANCE CLAIMS. If someone says "<0.5ms" without a
    benchmark, that's a guess. Flag it. Demand measurement.

R4. CHECK ERROR HANDLING. Every unwrap() is a crash waiting to happen.
    Every panic!() in library code is a bug. Find them.

R5. CHECK TEST QUALITY. Are the Crucible's tests actually testing
    semantics? Or are they just checking "it doesn't crash"?
    Weak tests are worse than no tests — they give false confidence.

R6. BE SPECIFIC IN FEEDBACK. "This is bad" helps no one.
    "Line 47: unwrap() on user input will panic on malformed UTF-8.
    Use .map_err() to return EncoderError::InvalidInput" — that helps.

R7. VERDICT: You must end with one of:
    - APPROVED: Ship it. (with minor notes if any)
    - REVISE: Specific issues listed, send back to Forge.
    - REJECT: Fundamental design flaw, send back to Architect.
    Never "it's fine I guess." Commit to your verdict.
""",
        "task_template": """
You are The Mirror — the code reviewer for the Cognitive Twin semantic encoder.

THE ARCHITECT'S DESIGN:
```
{architect_output}
```

THE FORGE'S IMPLEMENTATION:
```
{implementer_output}
```

THE CRUCIBLE'S TESTS:
```
{tester_output}
```

YOUR TASK:
Review everything. You are the quality gate. Check:
1. Does the encoder ACTUALLY encode semantically?
2. Is the implementation correct and idiomatic Rust?
3. Are the tests comprehensive enough?
4. Are performance claims backed by measurement?
5. Are error cases handled properly?

{context}

Review now. Be rigorous. End with your VERDICT.
""",
    },

    "integrator": {
        "name": "The Weaver",
        "emoji": "🕸️",
        "commandments": """
## WEAVER COMMANDMENTS (In Addition to Universal)

W1. DON'T RESTRUCTURE WHAT WORKS. The existing codebase has 234
    passing tests. You ADAPT the new encoder to the existing
    architecture, not the other way around.

W2. THE INTEGRATION MUST BE BACKWARD COMPATIBLE. The old lexical
    encoder should still work. The new semantic encoder is an
    alternative, selected by configuration. Feature flag or enum.

W3. MIGRATION PATH IS MANDATORY. Existing stored SDRs are lexical.
    New SDRs are semantic. How do they coexist? How does recall
    work during transition? Answer this or you haven't done your job.

W4. PRODUCE A CHECKLIST. Every file touched, every config changed,
    every test that needs updating. The team follows your checklist
    to integrate.

W5. OUTPUT FORMAT:
    - Integration plan (files to modify, in order)
    - Config/feature flag additions
    - Migration strategy for existing data
    - Updated Cargo.toml (workspace-level if needed)
    - Integration test that proves old + new coexist
""",
        "task_template": """
You are The Weaver — the integrator for the Cognitive Twin semantic encoder.

THE ARCHITECT'S DESIGN:
```
{architect_output}
```

THE FORGE'S IMPLEMENTATION:
```
{implementer_output}
```

THE MIRROR'S REVIEW:
```
{reviewer_output}
```

EXISTING CODEBASE INFO:
- Rust workspace project
- encoder.rs has current lexical (n-gram hash) encoder
- SDR bitvectors used throughout recall pipeline
- 234 existing tests must continue to pass
- hippocampus module handles storage/recall
- recall pipeline: encode → store → recall by similarity

YOUR TASK:
Plan the integration. Make the new encoder fit without breaking anything.
Handle the lexical→semantic migration. Produce a clear integration checklist.

{context}

Plan the integration now. Be precise.
""",
    },
}

# ╔══════════════════════════════════════════════════════════════════╗
# ║                      ORCHESTRATOR ENGINE                        ║
# ╚══════════════════════════════════════════════════════════════════╝

@dataclass
class AgentResult:
    """Output from a single agent run."""
    role: str
    content: str
    tokens_in: int = 0
    tokens_out: int = 0
    duration_s: float = 0.0
    verdict: Optional[str] = None  # For reviewer: APPROVED/REVISE/REJECT


@dataclass
class TeamRun:
    """Full orchestration run state."""
    results: dict = field(default_factory=dict)
    iteration: int = 0
    max_iterations: int = 3
    test_passed: bool = False
    start_time: float = 0.0
    total_tokens_in: int = 0
    total_tokens_out: int = 0


class EncoderBuildTeam:
    """
    MoE Agent Team for building the Cognitive Twin semantic encoder.
    
    Workflow:
        Architect → Forge → Crucible → Mirror → [loop if REVISE] → Weaver
        
    Gates:
        - Mirror verdict gates progression
        - cargo test gates final output (if project root provided)
    """

    def __init__(
        self,
        project_root: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 8192,
        verbose: bool = True,
    ):
        self.client = anthropic.Anthropic()
        self.project_root = Path(project_root) if project_root else None
        self.model = model
        self.max_tokens = max_tokens
        self.verbose = verbose
        self.run = TeamRun()

    def log(self, msg: str, emoji: str = "📋"):
        """Print a log message with timestamp."""
        if self.verbose:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"  {emoji} [{ts}] {msg}")

    def log_header(self, msg: str):
        """Print a section header."""
        if self.verbose:
            print(f"\n{'='*70}")
            print(f"  {msg}")
            print(f"{'='*70}")

    def call_agent(self, role: str, extra_context: str = "") -> AgentResult:
        """
        Call a single agent with its role-specific prompt.
        
        Builds the system prompt from Universal + Role commandments.
        Builds the user prompt from the task template + accumulated context.
        """
        agent = AGENTS[role]
        
        self.log_header(f"{agent['emoji']}  {agent['name']} ({role})")
        self.log(f"Engaging {agent['name']}...")

        # Build system prompt
        system_prompt = f"""You are {agent['name']}, a specialized agent in a team building
a semantic encoder for the Cognitive Twin project.

{UNIVERSAL_COMMANDMENTS}

{agent['commandments']}

You are meticulous, precise, and take pride in your craft.
Your output will be consumed by other agents in the team.
Structure it clearly. No fluff. No filler.
"""

        # Build user message from template
        template_vars = {
            "architect_output": self.run.results.get("architect", AgentResult("architect", "")).content,
            "implementer_output": self.run.results.get("implementer", AgentResult("implementer", "")).content,
            "tester_output": self.run.results.get("tester", AgentResult("tester", "")).content,
            "reviewer_output": self.run.results.get("reviewer", AgentResult("reviewer", "")).content,
            "context": extra_context,
        }
        user_message = agent["task_template"].format(**template_vars)

        # Call Claude
        start = time.time()
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
        except Exception as e:
            self.log(f"API ERROR: {e}", "❌")
            return AgentResult(role=role, content=f"ERROR: {e}")

        elapsed = time.time() - start
        content = response.content[0].text if response.content else ""
        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens

        self.run.total_tokens_in += tokens_in
        self.run.total_tokens_out += tokens_out

        self.log(f"Done in {elapsed:.1f}s | {tokens_in} in / {tokens_out} out tokens", "✅")

        # Parse reviewer verdict if applicable
        verdict = None
        if role == "reviewer":
            content_upper = content.upper()
            if "VERDICT: APPROVED" in content_upper or "**APPROVED**" in content_upper:
                verdict = "APPROVED"
            elif "VERDICT: REJECT" in content_upper or "**REJECT**" in content_upper:
                verdict = "REJECT"
            else:
                verdict = "REVISE"  # Default if not clearly approved
            self.log(f"Verdict: {verdict}", "⚖️")

        result = AgentResult(
            role=role,
            content=content,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            duration_s=elapsed,
            verdict=verdict,
        )
        self.run.results[role] = result
        return result

    def run_cargo_test(self) -> bool:
        """Run cargo test in the project root. Returns True if all pass."""
        if not self.project_root:
            self.log("No project root — skipping cargo test", "⚠️")
            return True

        self.log("Running cargo test...", "🧪")
        try:
            result = subprocess.run(
                ["cargo", "test"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                self.log("All tests passed!", "✅")
                return True
            else:
                self.log(f"Tests FAILED:\n{result.stderr[-500:]}", "❌")
                return False
        except Exception as e:
            self.log(f"cargo test error: {e}", "❌")
            return False

    def save_outputs(self, output_dir: str = "encoder_output"):
        """Save all agent outputs to files."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        for role, result in self.run.results.items():
            filepath = out / f"{role}_output.md"
            filepath.write_text(result.content, encoding="utf-8")
            self.log(f"Saved {filepath}", "💾")

        # Save summary
        summary = self._build_summary()
        (out / "BUILD_SUMMARY.md").write_text(summary, encoding="utf-8")
        self.log(f"Saved {out / 'BUILD_SUMMARY.md'}", "💾")

    def _build_summary(self) -> str:
        """Build a summary of the entire run."""
        elapsed = time.time() - self.run.start_time
        lines = [
            "# Encoder Build Team — Run Summary",
            f"",
            f"**Date:** {datetime.now().isoformat()}",
            f"**Model:** {self.model}",
            f"**Iterations:** {self.run.iteration}",
            f"**Total Duration:** {elapsed:.1f}s",
            f"**Total Tokens:** {self.run.total_tokens_in} in / {self.run.total_tokens_out} out",
            f"**Estimated Cost:** ~${(self.run.total_tokens_in * 3 + self.run.total_tokens_out * 15) / 1_000_000:.2f}",
            f"",
            "## Agent Results",
            "",
        ]
        for role in ["architect", "implementer", "tester", "reviewer", "integrator"]:
            r = self.run.results.get(role)
            if r:
                lines.append(f"### {AGENTS[role]['emoji']} {AGENTS[role]['name']}")
                lines.append(f"- Duration: {r.duration_s:.1f}s")
                lines.append(f"- Tokens: {r.tokens_in} in / {r.tokens_out} out")
                if r.verdict:
                    lines.append(f"- Verdict: **{r.verdict}**")
                lines.append("")
        return "\n".join(lines)

    def build(self, extra_context: str = "") -> dict:
        """
        Run the full build pipeline.
        
        Architect → Forge → Crucible → Mirror → [loop] → Weaver
        """
        self.run = TeamRun(start_time=time.time())

        print("""
╔══════════════════════════════════════════════════════════════════╗
║           COGNITIVE TWIN — ENCODER BUILD TEAM                   ║
║                                                                  ║
║   🏛️  Architect   →  Design the encoder                         ║
║   🔨  Forge       →  Implement it                               ║
║   🧪  Crucible    →  Test it ruthlessly                         ║
║   🪞  Mirror      →  Review & gate                              ║
║   🕸️  Weaver      →  Integrate with codebase                    ║
║                                                                  ║
║   Commandments loaded. Quality gates armed. Let's build.        ║
╚══════════════════════════════════════════════════════════════════╝
        """)

        # Phase 1: Architect designs
        self.call_agent("architect", extra_context)

        # Phase 2-4: Implement → Test → Review (with retry loop)
        for iteration in range(1, self.run.max_iterations + 1):
            self.run.iteration = iteration
            self.log_header(f"🔄 ITERATION {iteration}/{self.run.max_iterations}")

            # Forge implements
            revision_context = ""
            if iteration > 1 and self.run.results.get("reviewer"):
                revision_context = f"""
REVISION ROUND {iteration}. The Mirror found issues:
{self.run.results['reviewer'].content}

FIX THESE ISSUES. This is not optional. Not passing review
is embarrassing. The Mirror's feedback is specific — follow it.
"""
            self.call_agent("implementer", extra_context + revision_context)

            # Crucible tests
            self.call_agent("tester", extra_context)

            # Mirror reviews
            review = self.call_agent("reviewer", extra_context)

            if review.verdict == "APPROVED":
                self.log("Mirror APPROVED — moving to integration!", "🎉")
                break
            elif review.verdict == "REJECT":
                self.log("Mirror REJECTED — fundamental design issue!", "🚨")
                self.log("Re-running Architect with feedback...", "🔄")
                reject_context = f"""
THE MIRROR REJECTED YOUR PREVIOUS DESIGN:
{review.content}

Redesign. Address every concern. This is non-negotiable.
"""
                self.call_agent("architect", extra_context + reject_context)
            else:
                self.log(f"Mirror requested REVISE — iteration {iteration + 1}", "🔄")

            if iteration == self.run.max_iterations:
                self.log("MAX ITERATIONS REACHED — proceeding with best effort", "⚠️")

        # Phase 5: Weaver integrates
        self.call_agent("integrator", extra_context)

        # Save everything
        self.save_outputs()

        # Final summary
        elapsed = time.time() - self.run.start_time
        self.log_header("BUILD COMPLETE")
        self.log(f"Total time: {elapsed:.1f}s")
        self.log(f"Total tokens: {self.run.total_tokens_in} in / {self.run.total_tokens_out} out")
        self.log(f"Iterations: {self.run.iteration}")
        self.log(f"Reviewer verdict: {self.run.results.get('reviewer', AgentResult('reviewer', '')).verdict}")
        self.log(f"Outputs saved to: encoder_output/")

        return self.run.results


# ╔══════════════════════════════════════════════════════════════════╗
# ║                          ENTRY POINT                            ║
# ╚══════════════════════════════════════════════════════════════════╝

def main():
    parser = argparse.ArgumentParser(
        description="Cognitive Twin — Encoder Build Team",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python agent_team.py
  python agent_team.py --project-root ./cognitive_twin
  python agent_team.py --model claude-sonnet-4-20250514 --verbose
  python agent_team.py --context "Use SimHash approach, no ONNX deps"
        """,
    )
    parser.add_argument(
        "--project-root", "-p",
        help="Path to Cognitive Twin Rust project (enables cargo test gate)",
    )
    parser.add_argument(
        "--model", "-m",
        default="claude-sonnet-4-20250514",
        help="Claude model to use (default: claude-sonnet-4-20250514)",
    )
    parser.add_argument(
        "--context", "-c",
        default="",
        help="Extra context to inject into all agent prompts",
    )
    parser.add_argument(
        "--max-iterations", "-i",
        type=int,
        default=3,
        help="Max review→revise iterations (default: 3)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=True,
        help="Verbose output (default: True)",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimal output",
    )
    args = parser.parse_args()

    team = EncoderBuildTeam(
        project_root=args.project_root,
        model=args.model,
        verbose=not args.quiet,
    )
    team.run.max_iterations = args.max_iterations

    results = team.build(extra_context=args.context)

    # Exit code: 0 if approved, 1 otherwise
    reviewer = results.get("reviewer")
    if reviewer and reviewer.verdict == "APPROVED":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
