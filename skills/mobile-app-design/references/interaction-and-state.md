# Interaction and state

Read when choosing navigation, implementing a form or flow, changing user-visible state, or reviewing interruption/recovery. Describe the semantics before selecting router APIs.

## Choose presentation by relationship

| Relationship | Starting choice | Resolve before implementation |
|---|---|---|
| Peer destinations used repeatedly | Tabs or the platform's adaptive navigation | Each destination's history, state restoration, reselection behavior |
| Deeper detail in the current task | Stack navigation | Return destination, parent context, deep-link entry |
| A focused subtask with its own lifecycle | Modal presentation, possibly a nested stack | Cancel, completion, dismissal, unsaved work |
| A short contextual choice | System menu, picker, dialog, or suitable sheet | Anchor, selection, dismissal, keyboard and accessibility focus |
| Immersive content | Appropriate full-screen presentation | Discoverable exit and restoration of prior context |
| An app state that has changed durably | State-based routing/guards and appropriate history update | Whether the old screen is still valid and where this invocation should return |

These are starting points, not one-to-one laws. A sheet may contain navigation if the platform and task support it; appearance alone does not decide whether state belongs in a route. Deep-linking, restoration, browser support when in scope, and the existing router model inform that decision. Prefer system share, photo, date, and permission surfaces when they satisfy the task.

Back reverses navigation. It does not undo a server event. For each critical transition, establish entry context, forward action, back/cancel behavior, completion destination, and what survives interruption. Do not indiscriminately replace history or block gestures.

Contextual sign-in or entitlement checks should return to the invoking task with its draft and intent intact. A full-app sign-in gate can change the root route when session state resolves. Successful onboarding need not remain reachable by back; completing a purchase may still leave a useful receipt or order detail. Guard routes by the actual state and purpose, not by a list of universally forbidden screens.

Test ordinary entry, direct links, warm and cold starts, logout/session expiry, and dismissal when relevant. A deep link needs a sensible parent/exit path, but should not fabricate navigation history that misrepresents how the user arrived. Preserve independent tab state in accordance with the product and platform.

## Model outcomes truthfully

Distinguish **not started**, **in progress**, **confirmed success**, **known failure**, and **outcome unknown** where the operation can have those states. A timeout after submitting a reservation or payment is not proof of failure. Exiting a screen is not proof the request was canceled. Use the existing service's reconciliation/status mechanism; give the user a clear way to recover without encouraging duplicate submissions.

Optimistic feedback is suitable for reversible, low-consequence actions with a reliable rollback. Consequential or server-dependent outcomes need confirmed state before declaring success. Keep the relevant data visible during a partial refresh. Prevent accidental duplicate actions while pending, communicate progress, and preserve a way to navigate or recover according to the operation's actual behavior.

Loading treatment follows uncertainty: use stable placeholders for known structure, progress when meaningful, and local busy feedback for a local update. Empty states explain why the surface is empty and a useful next action. Errors identify the affected action and recovery; do not clear valid user input. Offline and permission-limited states should retain the usable parts of the experience.

## Forms and the keyboard

Choose controls, input types, autofill, secure entry, capitalization, return-key actions, and validation timing from the field's meaning. Keep persistent labels and specific errors associated with their fields. Do not rely on placeholders as the only label or color as the only error cue.

Keep the focused input and its error visible as the keyboard changes. Account for multiline growth, suggestions, large text, hardware keyboards, scrolling, and dismissal. Coordinate keyboard avoidance with existing inset ownership rather than stacking compensations. Preserve user input through route changes, backgrounding, failed submission, and session interruptions as the product requires.

Ask about unsaved work only where navigation would actually discard it. Prefer saving or recoverable drafts where appropriate. Do not trap back for conversion funnels or inconsequential transient UI. On Android, the keyboard and transient overlays participate in system back; on iOS, preserve supported interactive dismissal and edge navigation. Use the platform references for specifics.

## Permissions, feedback, and accessible interaction

Request access at the moment its value is understandable. Prefer narrow system pickers to broader permissions when they fulfill the task. Design denial, limited access, later revocation, and settings return without blocking unrelated tasks. Avoid requesting permissions as decorative onboarding steps.

Provide visible feedback for actions and outcomes. Haptics and sound supplement it; they do not establish success alone. Give gesture actions discoverable alternatives where necessary. Preserve semantic role, accessible name/value/state, logical focus, and focus return after overlays. Announce consequential asynchronous changes without flooding assistive technology on every render.

Create a small state/transition table only when the flow is complex enough to benefit. Keep it near the implementation or design artifact it explains, and make it describe the actual behavior rather than an aspirational checklist.
