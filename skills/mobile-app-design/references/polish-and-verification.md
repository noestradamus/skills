# Polish and verification

Use this reference to review an existing experience, refine a completed path, or validate implementation. Start with the intended outcome and available evidence. In review mode, inspect and report without editing application code. In design-only work, assess the proposal and specify checks for implementation; do not imply that proposed behavior has run.

## Establish the scope and baseline

Identify affected screens, shared components, native targets, and critical outcomes. Read incumbent tokens and neighboring flows. Inspect current rendered output when available; otherwise label screenshots or fixtures by source and freshness, distinguishing their evidence from current code.

For polish, preserve the established identity, information architecture, factual copy, and behavior outside the defects in scope. A different aesthetic is a redesign proposal. Missing documentation does not invalidate a coherent existing system.

Define acceptance before changing anything: what must the user be able to do, perceive, and recover from? Select checks for likely failures. A spacing correction needs affected layout coverage; a purchase flow needs transition and recovery evidence.

## Triage by user impact

Address findings in this order:

1. Blocked tasks, data loss, misleading success, duplicate actions, inaccessible controls, and broken navigation or recovery.
2. Missing applicable states, hidden keyboard inputs, clipping, unreadable text, and inconsistent hierarchy.
3. Drift in shared patterns, tokens, interaction feedback, imagery, and motion.
4. Optical details, copy consistency, and cleanup caused by the change.

Record the trigger, location, user impact, evidence, and specific correction. Separate a reproduced defect from a risk inferred from code. Do not bury a critical failure in an average quality score or fill a review with unsupported aesthetic objections.

Find the narrowest correct repair: a local value, missing shared token, duplicated component, or flow mismatch. Reuse established abstractions when they own the behavior; introduce one only when reuse is real.

## Inspect the finished surface

Inspect realistic content across affected states, including the relevant theme and larger text settings:

- **Hierarchy and spacing:** the main task is discoverable; proximity communicates groups; headings have appropriate separation; alignment is optically credible as well as mathematically consistent. Tokens establish rhythm without forbidding justified optical adjustments.
- **Typography:** same-role text is consistent, readable, and appropriately scalable. Check wrapping, truncation, numerals, baseline alignment, localized expansion, and missing content where relevant. Do not force a line break that breaks another supported width or language.
- **Color and imagery:** semantic meanings remain stable; text and controls have adequate contrast in their actual states; icons share a coherent weight and alignment. Inspect image aspect ratio, crop, sharpness, transparency edges, and theme compatibility.
- **Interaction and copy:** controls expose their purpose and current state through appropriate feedback and semantics. Keep labels, punctuation, tense, and terminology consistent. Errors explain the problem and available recovery. Preserve supplied facts, prices, permissions, and product claims.

Refinement should improve the affected path consistently. Avoid lavishly finishing one screen while its arrival or recovery state remains incomplete.

For custom colors, use WCAG 2.2 AA contrast as a default design target: at least 4.5:1 for ordinary text and 3:1 for essential graphical/control-state cues against adjacent colors. Use the 3:1 large-text exception only after establishing the standard's qualifying size and weight; do not equate CSS points and native logical points blindly. Check the intended foreground/background values and compositing, not anti-aliased glyph-edge pixels. Respect the standard's applicability and exceptions; a contrast calculation alone is not an accessibility-conformance claim. [Text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html), [Non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html).

## Select native checks from the changed behavior

Use the platform references for target-specific requirements, [interaction and state](interaction-and-state.md) for state mechanics, and [motion](motion.md) for custom animation behavior. Expand coverage only where the task exposes the risk:

| Changed surface | Representative checks |
|---|---|
| Layout, type, or reusable control | Affected compact/expanded windows, safe areas, relevant themes, large text, long labels, reachable targets |
| Form or editor | Focus and keyboard/IME visibility, autofill where applicable, correction after errors, draft preservation, cancel and return |
| Navigation or consequential action | Normal entry and relevant deep link, platform Back, completion, cancellation, rapid repeated input, pending/failure/recovery |
| Persistent or asynchronous flow | Relevant offline/slow state, lost permission, background/foreground, re-entry or relaunch according to the persistence contract |
| Gesture or motion | Actual moving interaction, interruption/reversal, repeated input, system motion preference |
| Performance-sensitive surface | Representative data volume and interaction, release build, suitable physical target and measurement |

Do not invent irrelevant states for every component. Test lifecycle transitions when they can invalidate the state changed by the work. Use representative configurations for shared behavior and inspect platform-specific paths separately.

Before changing device theme, font scale, motion preferences, or other settings, record their current values and the explicit device identifier. Restore those values afterward, including after a failed check. Reuse available tools and runtimes; do not install packages, reset simulator data, or change global tooling merely to satisfy this checklist.

## Match the claim to the evidence

| Evidence | Supports | Remaining limits |
|---|---|---|
| Source inspection and automated checks | Implementation structure, defined semantics, checks actually executed | Rendered appearance and real interaction may differ |
| Current native screenshot | Visible layout and state for the captured configuration | Gestures, transitions, focus traversal, and performance |
| Simulator/emulator interaction or recording | Observed flow, keyboard behavior, interruption, and visible motion | Physical haptics, hardware performance, and untested configurations |
| Actual VoiceOver/TalkBack session | Observed names, order, focus movement, announcements, and task access | Other assistive technologies and untested paths |
| Release build measured on hardware | The measured interaction under the recorded device/data conditions | Other devices, refresh rates, workloads, and OS versions |

A web preview supports web-rendered observations. Reading accessibility properties supports semantic inspection. Neither establishes native runtime or screen-reader usability. Record measurement conditions before comparing performance; a subjective smoothness impression is not an FPS result.

## Finish deliberately

Batch representative inspection, repair observed defects, and confirm affected behavior. Continue when a change or newly demonstrated failure warrants it. Stop when acceptance checks pass and no material known defect remains; avoid repeated cosmetic searches without a concrete concern.

If a required capability is unavailable, complete useful authorized work, identify precisely what remains unverified, and give the next concrete check. Never replace missing evidence with a success claim.

Finish with the changes or prioritized findings, actual verification, and material limitations. Link useful artifacts and name relevant runtime/device conditions. Remove accidental churn and temporary artifacts introduced by the work. Keep the handoff proportional to the task.
