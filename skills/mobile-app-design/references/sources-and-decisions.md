# Sources and synthesis decisions

Maintenance reference. Do not load this file for routine design work. Sources were reviewed on **2026-09-07**. Repository revisions below are immutable; linked official documentation can change. The source authors do not endorse this synthesis.

## Attribution and reading coverage

| Source | Reviewed revision and coverage | Contribution |
|---|---|---|
| Expo Team, `building-native-ui` and its successors | [`d0075ffa09928f1edb3e7ac4f5af07586d4b344d`](https://github.com/expo/skills/tree/d0075ffa09928f1edb3e7ac4f5af07586d4b344d/plugins/expo/skills): `expo-native-ui/SKILL.md`; its animations, controls, visual-effects, icons references; `expo-router/SKILL.md`; its form-sheet, tabs, route-structure references; `expo-ui/SKILL.md` | Native primitives, platform integration, navigation and compatible implementation. MIT; 650 Industries, Inc. (Expo). |
| James Rochabrun, Apple HIG Designer | [`2482c176372299c92af01f8414a67172f324e8db`](https://github.com/jamesrochabrun/skills/tree/2482c176372299c92af01f8414a67172f324e8db/skills/apple-hig-designer): main skill and all five references | Apple interaction, typography, semantics, and accessibility foundations. Four references only redirect to the main file. MIT; James Rochabrun. |
| Paul Bakaus, Impeccable | [`36e4cea693f69fe9b08ec93cbd360fd3eb1f2aee`](https://github.com/pbakaus/impeccable/tree/36e4cea693f69fe9b08ec93cbd360fd3eb1f2aee/skill): `SKILL.src.md`, polish, craft-floor, operate, audit.native, adapt.native, ios, android; [public polish documentation](https://impeccable.style/docs/polish/) | Scope-preserving refinement, cause-based triage, visual judgment, and native evidence boundaries. Apache-2.0; Paul Bakaus. |
| Emil Kowalski, Animate Expo | [`d23d7f88a2e21c9e4b1418c7abe420f5c1052ba7`](https://github.com/emilkowalski/skills/tree/d23d7f88a2e21c9e4b1418c7abe420f5c1052ba7/skills/animate-expo): entire `SKILL.md` and `RECIPES.md` | Purpose and frequency before motion, direct-manipulation continuity, feedback, reduced motion, and measurement. MIT; Emil Kowalski. |
| Appllama, App Design Skill | [`dd5caaec3d5d50ad7fc0324da238119c6b7c3707`](https://github.com/Appllama/appllama-skills/tree/dd5caaec3d5d50ad7fc0324da238119c6b7c3707/skills/appllama-app-design-skill): main skill plus native-controls, motion, performance, image-assets, simulator-loop | Pattern research, explicit navigation/state semantics, complete journeys, and observing the running experience. MIT; Antmind Ventures Private Limited (appllama.io). |

Expo's [rename history](https://github.com/expo/skills/commit/b2fdce752bbf8f3ba83883d8a35c642e229c8812) establishes the original source's move to `expo-native-ui` and the navigation split into `expo-router`. Current successors were reviewed rather than treating both historical and current versions as simultaneous authorities. Installed Impeccable 4.1.3 and current upstream differ; the table pins the upstream material used for the final synthesis.

The package uses rewritten guidance and original decision structure. Upstream executable scripts, template applications, detector workflows, and animation recipes are not bundled. Attribution/license texts are retained in [Expo](../licenses/expo.txt), [Apple HIG Designer](../licenses/apple-hig-designer.txt), [Impeccable](../licenses/impeccable.txt), [Animate Expo](../licenses/animate-expo.txt), and [Appllama](../licenses/appllama.txt). Impeccable's [third-party notice](../licenses/impeccable-notice.txt) credits ehmo's MIT-licensed platform-design-skills. Preserve applicable notices if adapting this package further.

Coverage is deliberately narrower than the full upstream repositories. Expo's media/storage/WebGPU and other unrelated references, Expo UI's full component manuals, and the HIG skill's shell scripts were not audited. No upstream recipe was validated by running a native app during source analysis.

## Consequential synthesis decisions

| Inherited approach | Decision in this skill | Reason |
|---|---|---|
| Study a fixed quota of commercially successful screens | Research the unresolved decision; stop when evidence is sufficient | A local polish task and a novel flow need different effort; popularity does not prove suitability. |
| One accent, one gray family, prescribed type/radius rules | Stable semantic roles and a product-specific visual thesis | Consistency should preserve a legitimate expressive brief rather than erase it. |
| HIG interpreted as one visual template | Native behavior and accessible interaction with deliberate brand expression | Official Apple and Material guidance allow customization. |
| Tab bars and toolbars cannot coexist | Choose destination navigation and contextual actions by platform/window | Current [Apple toolbar guidance](https://developer.apple.com/design/human-interface-guidelines/toolbars) supports their combination on iPadOS. |
| Fixed minimum text size and normal-text scaling cap | Distinguish defaults from minima; allow accessibility reflow | [Apple accessibility guidance](https://developer.apple.com/design/human-interface-guidelines/accessibility) makes these distinctions; smaller default fonts are not automatically inaccessible. |
| Every completed flow leaves history | Remove invalid steps while preserving useful context and destinations | Contextual sign-in, receipts, and completed documents do not share one history rule. |
| Optimistic success for every action | Immediate acknowledgment; authoritative confirmation for consequential outcomes | A timeout can mean an unknown result; pretending success or blindly retrying is misleading. |
| Always root ScrollView, FlashList, uncontrolled input, or a new state library | Select by content, state ownership, compatibility, and measured need | The existing architecture may already fit; implementation preferences are not quality criteria. |
| Always use Expo Go or always replace a sheet library | Match runtime and component to the interaction contract | Native binary support and persistent versus modal sheet behavior differ. |
| One shadow API or one animation API everywhere | Verify supported exports, versions, architecture, and platform | Upstream examples disagree and age; even official general guides can lag SDK-specific pages. |
| Add animations whenever state changes | First decide what the motion explains and its interruption cost | Routine content should remain responsive and accessible. |
| Transform/opacity only; always bounce or never bounce | Prefer inexpensive motion while preserving the intended geometry and interaction | Some reflow is meaningful; gesture physics and frequency matter more than a blanket style rule. |
| Recycled row entrance/stagger recipe | No unintended replay during recycling; purposeful data transitions only | Cell mounting does not necessarily mean new content. |
| Startup reduced-motion query is enough | Verify active preferences, effective overrides, endpoint, and cancellation | A startup value can become stale; disabled motion still needs correct state. |
| Iterate until flawless versus stop after two passes | Acceptance repair continues; further cosmetic passes need a concrete defect | Neither endless perfection nor a rigid cap is a reliable completion rule. |
| Simulator video certifies performance | Separate visual, interaction, accessibility, and release-device evidence | Each claim requires a corresponding observation or measurement. |

## Keeping the skill useful

The core owns scope, authority, routing, and evidence claims. Shared state rules belong in interaction-and-state; platform exceptions belong in ios/android; volatile API choices belong in expo-react-native/motion. Correct a rule at its owner rather than repeating patches across files.

When an SDK, router, or animation library changes, inspect the relevant official versioned documentation and installed types; record material changes to these source pins and decisions. Recheck compatibility, native navigation/sheets, keyboard/insets, reduced motion, and build availability where affected. Do not automatically absorb new upstream prescriptions.

Evaluate with realistic tasks that force choices: a distinctive design-only brief, an existing older-stack polish task, interrupted authentication/submission, a recycled feed with a gesture, unavailable native tooling, and a large-text adaptive layout. Judge actual outputs and changes against scope, design specificity, platform/accessibility behavior, technical compatibility, state truth, and evidence. Update only for demonstrated defects or substantive new guidance.
