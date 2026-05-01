# Voice CRM Design System v1

Date: 2026-04-30  
Scope: Slack + CRM hybrid visual language, interaction states, density model, and accessibility baseline  
Research Phase: DFS (UI primitives and operational ergonomics)

## Design Goals
- Preserve high information density without overwhelming operators.
- Keep critical call actions glanceable and one-click reachable.
- Use progressive disclosure so first view answers: what needs action now.

## Token Set (v1)
### Core Surface Tokens
- `--vc-bg`: `#020617`
- `--vc-surface`: `#0f172a`
- `--vc-surface-elevated`: `#111827`
- `--vc-border`: `#1e293b`

### Semantic Tokens
- `--vc-accent`: `#7c3aed`
- `--vc-success`: `#059669`
- `--vc-warning`: `#d97706`
- `--vc-danger`: `#dc2626`

### Usage Notes
- Keep accent for navigation focus and selected views only.
- Use semantic colors for operational state, not decoration.

## Component States
### Interaction Row
- `default`: neutral surface with queue metadata.
- `selected`: elevated background + subtle ring.
- `attention`: state chip + queue timer emphasis.
- `disabled`: reduced opacity, no action affordance.

### Stage Chip
- `Ringing`: info tone.
- `Live`: success tone.
- `WrapUp`: neutral tone.
- `Escalated`: danger tone.
- `Booked`: accent tone.

### Action Buttons
- Primary: `Accept` and `Submit disposition`.
- Secondary: `Hold`, `Transfer`, `Assign owner`.
- Destructive: `End`.

## Density Modes
### Comfortable (default)
- Row height tuned for mixed-experience operators.
- More vertical spacing and larger click targets.

### Compact (power users)
- Reduced row spacing and tighter cards.
- Preserves hierarchy while fitting larger queue volumes.

## Typography and Layout
- Primary font: Inter (already configured in layout).
- Left rail fixed-width, center stream fluid, right context fixed panel.
- KPI summary must fit above fold on standard laptop viewport.

## Accessibility Rules
- Focus indicators required on all interactive elements.
- Color is never sole indicator for state; pair with text/shape.
- Keyboard path supports primary call operations without pointer.
- Transcript updates must be announced via live regions.
- Minimum text contrast target: WCAG AA for normal text.

## Analytics Card Rule
- Limit top-level metrics to 4-6 per screen section to reduce cognitive load.
- Details appear on drill-in, not in first view.

## Implementation Mapping
- `landing/app/globals.css`: token declaration and global dark baseline.
- `landing/components/VoiceCrmWorkspace.tsx`: state chips, density toggles, panel hierarchy.

## References
[^1]: Nielsen Norman Group. (2009). Progressive Disclosure. https://www.nngroup.com/articles/progressive-disclosure
[^2]: Nielsen Norman Group. (2025). Dashboards: Making Charts and Graphs Easier to Understand. https://www.nngroup.com/articles/dashboards-preattentive/
[^3]: Slack. (2024). A redesigned Slack, built for focus. https://slack.com/blog/productivity/a-redesigned-slack-built-for-focus
