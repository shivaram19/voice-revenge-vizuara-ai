# Voice CRM UI Interaction Specification

Date: 2026-04-30  
Scope: Agent desktop interactions for live voice handling, transcript workflow, disposition, and pipeline movement  
Research Phase: Bidirectional (architecture to UX operationalization)

## Purpose
Define deterministic UI behavior for the Voice CRM workspace so call handling follows the underlying conversation state machine and turn-taking constraints.

## Interaction 1: Live Call Handling
### Trigger
- Incoming interaction enters queue with stage `Ringing`.

### UI Behavior
1. The interaction appears in the center stream with `Ringing` pill, queue name, and elapsed timer.
2. Operator actions are one-click: `Accept`, `Hold`, `Transfer`, `End`.
3. Upon `Accept`, the selected row transitions to `Live` and pins in right panel context.
4. On `Hold`, right panel shows explicit hold status and elapsed hold timer.
5. On `Transfer`, transfer destination selector opens with role and queue targets.
6. On `End`, disposition drawer opens immediately (cannot silently close).

### State Alignment
- `Ringing` maps to pre-LISTENING session queue state.
- `Live` maps to LISTENING/THINKING/SPEAKING runtime loop.
- Interruptions and barge-in must update UI within one state update tick.

## Interaction 2: Transcript Review
### Trigger
- Interaction is in `Live` state and transcript events are streaming.

### UI Behavior
1. Transcript auto-scroll is ON by default.
2. Operator can freeze scroll while new lines continue buffering.
3. Speaker badges are visible for `Caller` and `Agent`.
4. Confidence-risk lines (low certainty) are visually marked for confirmation.
5. On reconnect, transcript resumes from latest acknowledged offset.

### Operational Notes
- Transcript pane should remain open during transfers to preserve continuity.
- During active call, transcript remains in right panel to avoid context-switch cost.

## Interaction 3: Disposition and Next Action
### Trigger
- Call end event or handoff completion.

### UI Behavior
1. Disposition card appears with required fields: outcome, urgency, owner, follow-up mode.
2. Next-action recommendation appears from extracted intent and urgency signals.
3. `Submit disposition` writes stage and follow-up task atomically.
4. Completed disposition shifts record into `Pipeline` stage board.

### Validation Rules
- `Escalated` requires owner assignment.
- `Booked` requires date/time and channel confirmation.
- `WrapUp` without next action is rejected.

## Interaction 4: Pipeline Transition
### Trigger
- Operator drags item across pipeline stages or submits stage change in detail view.

### UI Behavior
1. Stage change opens conditional fields relevant to destination stage only.
2. Required fields block drop/submit if incomplete.
3. Time-in-stage starts/reset according to new stage timestamp.
4. Stage probability updates weighted forecast in analytics cards.

## Keyboard and Accessibility Rules
- Keyboard shortcuts: `A` accept, `H` hold, `T` transfer, `/` search, `G` goto.
- All high-risk actions (`End`, `Escalate`) require visible focus state and confirmation affordance.
- Live regions announce stage changes for assistive tech.

## References
[^1]: Sacks, H., Schegloff, E. A., & Jefferson, G. (1974). A Simplest Systematics for the Organization of Turn-Taking for Conversation. *Language*, 50(4), 696-735.
[^2]: Nielsen Norman Group. (2009). Progressive Disclosure. https://www.nngroup.com/articles/progressive-disclosure
[^3]: Nielsen Norman Group. (2025). Dashboards: Making Charts and Graphs Easier to Understand. https://www.nngroup.com/articles/dashboards-preattentive/
[^4]: Internal Architecture Doc. (2026). Conversation State Machine. `docs/architecture/data-flow/conversation-state-machine.md`.
[^5]: Internal Architecture Doc. (2026). Turn-Taking Design. `docs/architecture/turn-taking-design.md`.
