# Cognitive Twin v6.0-MOTOR — Architecture

For the full architecture specification, refer to the cumulative
v6.0-MOTOR build spec document. The AGENTS.md in the repo root
contains all function signatures, interface contracts, and build
phases needed for implementation. The CLAUDE.md file contains all
33 inviolable rules.

Together, CLAUDE.md + AGENTS.md are sufficient for the agent swarm
to build the entire system autonomously.

## System Overview

```
HIPPOCAMPUS.recall(query, depth)
    → {context, traces, confidence}
                     │
BRAINSTEM.get_load() → allostatic_load
                     │
CALLOSUM.should_escalate(recall_result, load) → bool
         │                                │
         │ False                          │ True
         ▼                                ▼
    Return context              PREFRONTAL.resolve(stage) → Resolution
    via BRAINSTEM.wrap()                  │
                                         ▼
                            ALETHEIA.run_gvr(intent, resolution)
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                 VERIFIED     FIXABLE     SPEC_GAMED/UNPROVABLE
                    │         (revise,       (return to user)
                    │          max 3)
                    ▼
            CALLOSUM.check_intent(intent, resolution, profile)
                    │
            CALLOSUM.is_amygdala?(resolution)
                 │              │
              Standard       Amygdala
              (VERIFIED       (1-shot,
               only)          permanent)
                 │              │
                 └──────┬───────┘
                        ▼
            HIPPOCAMPUS.store_reflex(reflex)
              [REJECTS unverified]
                        │
                        ▼
            BRAINSTEM.apply_modulation(output, profile)
            BRAINSTEM.wrap_for_llm(core, wash)
                → JSON to LLM

  ─── MOTOR PATH ───────────────────────────────────────
            MOTOR.premotor.plan(intent, context) → ActionPlan
            ALETHEIA.run_gvr(intent, plan)
            MOTOR.basal_ganglia.gate(action, state)
              DEFAULT: INHIBIT
            MOTOR.executor.execute(action) → ActionResult
              [ONE action, then STOP]

  ─── INQUIRY PATH ─────────────────────────────────────
            DAEMON.dmn_teardown (30s budget, preemptable)
                → INQUIRY.synthesize → APOPHENIA_GUARD
                → queue survivors with TTL → 0W
```
