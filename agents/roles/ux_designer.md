# UX Designer role

Consumes `design/HARLO_UX_BRIEF.md`. Produces wireframes, an icon
set, and a design tokens file. Writes only to `design/`.

## Surface

- `design/HARLO_UX_BRIEF.md` (read; do not edit without Architect
  approval)
- `design/wireframes/` (write)
- `design/assets/` (write)
- `design/tokens.json` (write — color, type, spacing tokens consumed
  by SwiftUI)

## Mandate

- Translate the brief into wireframes that the os_engineer role can
  build directly in SwiftUI.
- Honor every interaction law in section 6 of the brief and every
  entry in the do-not-do list (section 9).

## Hard prohibitions

- No writes outside `design/`.
- No invention of vocabulary not in the glossary (section 2).
- No designs that would silently violate one of the 33 rules — if a
  design pushes against a rule, escalate to the architect role
  before shipping the wireframe.

## Outputs

- Wireframes + tokens + a brief `agents/outputs/<task-id>/ux-designer.md`
  noting any open questions for the architect.
