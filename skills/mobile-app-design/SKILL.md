---
name: mobile-app-design
description: Design, implement, review, and polish native mobile screens and flows in Expo/React Native for iOS and Android. Use for mobile visual direction, navigation, native interaction, motion, accessibility, and interface refinement. Not for responsive websites or backend-only work.
---

# Mobile App Design

Make the main task clear, give the product a deliberate visual identity, preserve native behavior, and verify the experience at the level the evidence supports. Use this skill for the requested part of the work; a small fix does not require a full design process.

## Establish the task

Inspect the brief, supplied references, existing screens/components/tokens, and relevant project instructions. Before implementation, inspect the installed Expo, React Native, router, animation, and styling versions and the supported platforms. An existing interface is design evidence even without a design document.

Determine whether the user wants **design**, **implementation**, **review**, or **polish**; combine them only as the request warrants. Design-only work produces a concrete proposal without modifying application code. Review reports evidence and recommendations. Polish preserves identity, information architecture, factual copy, and behavior except for the defects in scope. Redesign can replace the visual direction when requested.

Infer what is already supported by the project. Ask only when a missing answer would materially change the result: the primary user task, target platform, binding visual direction, or a consequential behavior. For reversible choices, state a reasonable assumption and proceed. Do not require an intake questionnaire, research quota, or approval checkpoint for every screen.

## Load guidance selectively

Read the reference when its decisions arise, before making those decisions. Do not load the whole package by default.

| Decision | Reference |
|---|---|
| New visual direction, hierarchy, layout, reference study, or imagery | [Design direction](references/design-direction.md) |
| Navigation, forms, state transitions, permissions, interrupted flows, recovery | [Interaction and state](references/interaction-and-state.md) |
| iOS controls, presentation, accessibility, safe areas, adaptation | [iOS](references/ios.md) |
| Android controls, system back, accessibility, insets, adaptation | [Android](references/android.md) |
| Writing or changing Expo/React Native UI code | [Expo and React Native](references/expo-react-native.md) |
| Custom transitions, gestures, haptics, motion review | [Motion](references/motion.md) |
| Reviewing or finishing an existing experience; validating implemented work | [Polish and verification](references/polish-and-verification.md) |
| Maintaining this skill, checking a disputed inherited rule, updating a recipe | [Sources and decisions](references/sources-and-decisions.md) |

Read the relevant platform reference before changing platform-dependent behavior. For a cross-platform flow, resolve both platforms; code sharing is not evidence that their behavior should be identical. A local visual fix can use the existing platform conventions without reopening navigation design.

## Resolve competing guidance

Use the explicit brief and the product's actual context to select the intended outcome. Preserve accessibility, truthful state, recoverability, and supported platform behavior within that outcome. If those conflict with the brief, explain the concrete conflict and propose the closest usable alternative.

Treat inherited advice in three classes:

- **Constraints:** actual platform/API limits, accessibility needs, data integrity, and the user's authorized scope. Verify uncertain technical constraints against the installed version and official documentation.
- **Defaults:** native controls, semantic tokens, familiar navigation, restrained frequent motion. Depart when a product need justifies the cost and the result remains usable.
- **Choices:** palette, typeface, density, shape, imagery, and expressive motion. Make them coherent with the selected direction; no universal ban on colors, gradients, custom fonts, or playful brands.

Current official platform/library documentation resolves technical conflicts with a source skill. Existing project abstractions usually outrank a preferred package. A popular reference app provides a pattern to investigate, not proof that the pattern is right for this product. If verification is unavailable, choose a compatible established path or mark the assumption; do not present a guess as checked.

## Work from intent to observable behavior

**Frame the experience.** Identify the primary task, information needed to act, critical state changes, and relevant constraints. For new or redesigned work, articulate a short visual thesis specific enough to determine hierarchy, composition, typography, color roles, and motion character. Use the supplied visual reference as authority where specified.

**Resolve the flow.** Choose navigation and presentation by the relationship between tasks. Specify what happens on back, cancel, completion, interruption, and re-entry where relevant. Design with realistic content and applicable loading, empty, error, offline, permission, and long-content states. An attractive success screen cannot substitute for these decisions.

**Build a coherent slice.** Use native or established project components for conventional behavior. Carry the chosen design through shared tokens, recurring content roles, and interaction patterns. Introduce custom implementation where it delivers a concrete product benefit; preserve its semantics and accessible alternatives. Validate a representative end-to-end slice before multiplying it into many screens.

**Inspect and refine.** Use the app and inspect its rendered output when tools permit. Fix blocked tasks and misleading state before layout and motion defects; then refine optical alignment, text, imagery, and copy. Keep the whole affected path at a consistent level of finish.

**Finish against evidence.** Define task-relevant acceptance checks, inspect them in a batch, fix the observed issues, and confirm the affected behavior. Continue when new defects or changes warrant it; stop once the checks pass and no material known defect remains. Do not repeat subjective polishing indefinitely. If the available runtime prevents verification, complete useful work and name the remaining checks and limitations precisely.

## Deliver a result the next person can use

Scale the handoff to the task:

- Design: concrete screens/flow, visual direction, platform differences, applicable states, and unresolved decisions. Include artifacts when requested or useful.
- Implementation or polish: the finished changes, relevant interaction behavior, verification evidence, and material gaps.
- Review: actionable findings tied to observed screens, states, or code, with user impact and a specific correction. Identify code-inferred risks separately from reproduced defects.

Distinguish **implemented**, **visually inspected**, **interaction-tested**, and **measured on device**. A web preview does not verify native behavior; a simulator recording does not establish release-device performance; reading accessibility props does not establish screen-reader usability. Never invent tool runs or measurements. Tools and external research services are optional capabilities, not dependencies of this skill.
