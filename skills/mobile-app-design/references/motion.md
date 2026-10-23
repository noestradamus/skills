# Motion, gestures, and haptics

Use motion to explain, acknowledge, orient, or support direct manipulation. This reference owns shared behavior, not framework APIs. Use [SwiftUI](swiftui.md) or [Expo and React Native](expo-react-native.md) for implementation, [iOS](ios.md) and [Android](android.md) for platform conventions, and [Interaction and state](interaction-and-state.md) for navigation. Widgets have a different execution model; use [WidgetKit](widgetkit.md) before applying app animation techniques there.

## Decide what motion earns

Before implementation, state its purpose, trigger, frequency, and information retained without animation. If it adds no useful feedback or meaning, omit it. Repeated interactions deserve low interruption cost; rare celebratory moments can carry more expression. Do not invent daily-use counts or enforce universal timing limits.

Keep content and actions available promptly. Avoid decorative delays, replaying entrances during routine scrolling, and disabling input until an animation finishes. Tune expressive motion to the product's character, travel distance, object scale, and observed feel. Fast feedback should start when input engages; successful activation commits the action.

## Choose ownership and the smallest suitable tool

First identify who owns the transition: native control, navigator, layout, or custom interaction. Preserve native keyboard, navigation, sheet, and control behavior when it already meets the need. Do not layer a second animation or haptic over that behavior without a specific reason.

| Requirement | Prefer |
| --- | --- |
| Existing native transition or feedback | Its supported configuration |
| Simple state change | A scoped declarative animation or transition in the existing framework |
| Mount, exit, or genuine reflow | Supported layout/lifecycle animation with stable identity |
| Continuous drag or scroll response | The framework's gesture/animation state, with a deliberate commit boundary |
| Complex illustration | An appropriate existing asset/rendering tool, with a static equivalent |

Inspect versions before choosing an API. An existing adequate implementation need not be rewritten. Keep unrelated state changes outside the animation's scope.

## Make gestures continuous and recoverable

Define idle, tracking, settling, committed, and canceled outcomes. On takeover, continue from the current visible position, cancel competing motion where necessary, and preserve appropriate release velocity. Explicitly resolve direction, scroll competition, thresholds, boundaries, cancellation, and repeated input. Use native/library gesture behavior before implementing a custom state machine.

A spring often suits momentum and interruptible settling; timing can suit a deliberate two-state change. Choose parameters from the intended behavior and test them. Do not impose one spring or easing curve on every surface.

Separate transient presentation/gesture state from committed domain state. Keep per-frame work in the framework's animation machinery and commit semantic actions at deliberate boundaries, protecting against duplicate commits.

## Preserve geometry and exit lifecycle

Prefer less expensive properties when they express the intended result without distortion. Legitimate layout animation should be measured and profiled, not replaced with misleading scaling; property choice alone does not establish performance.

Measure relevant container/content bounds and refresh after text scaling, content updates, resizing, or orientation changes. Avoid fixed offscreen distances for variable content. Check transformed hit regions and clip boundaries.

An exit must define when semantic state changes, when the element unmounts, and what happens if interrupted. Maintain visible content long enough for an intended exit, but never make important state depend solely on decorative completion. Handle canceled exits, reduced motion, remote removal, failed optimistic changes, and focus restoration. Do not animate recycled rows as though every remount is new content.

## Reduced motion and optional haptics

Keep the same information, actions, and final state with reduced motion. Prefer immediate state changes or quieter alternatives where appropriate; remove unnecessary travel, parallax, and overshoot. Preserve native preference handling and verify effective per-screen options: a child override can defeat a parent fallback.

Use the framework's current preference source and test both launch-time and in-session changes where applicable. Check descendant animations as well as the parent transition; suppressing one celebration does not establish reduced-motion behavior for the whole screen.

Use haptics sparingly at meaningful selection, threshold, or result events. Avoid duplicates from native controls and per-frame pulses. Pair them with visible feedback; hardware and preferences can suppress them. Use the platform's supported feedback through the chosen framework. Scheduling at the causal event does not prove exact-frame delivery.

## Verify what cannot be inferred

Exercise rapid repeats, short flicks, slow drags, mid-flight takeover, reversal, cancellation, keyboard interaction, changed content, and reduced motion. Check that state remains correct without animation. Inspect performance in a release build on representative supported devices, especially slower hardware. Simulator recordings and source review can establish narrower findings; they cannot establish physical haptic timing or release-device smoothness. Report the evidence and remaining checks precisely.
