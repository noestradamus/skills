# Motion, gestures, and haptics

Use motion to explain, acknowledge, orient, or support direct manipulation. Technical guidance checked 2026-09-07. Keep platform-specific conventions in [iOS](ios.md) and [Android](android.md), and navigation relationships in [Interaction and state](interaction-and-state.md).

## Decide what motion earns

Before implementation, state its purpose, trigger, frequency, and information retained without animation. If it adds no useful feedback or meaning, omit it. Repeated interactions deserve low interruption cost; rare celebratory moments can carry more expression. Do not invent daily-use counts or enforce universal timing limits.

Keep content and actions available promptly. Avoid decorative delays, replaying entrances during routine scrolling, and disabling input until an animation finishes. Tune expressive motion to the product's character, travel distance, object scale, and observed feel. Fast feedback should start when input engages; successful activation commits the action.

## Choose ownership and the smallest suitable tool

First identify who owns the transition: native control, navigator, layout, or custom interaction. Preserve native keyboard, navigation, sheet, and control behavior when it already meets the need. Do not layer a second animation or haptic over that behavior without a specific reason.

| Requirement | Prefer |
| --- | --- |
| Existing native transition or feedback | Its supported configuration |
| Simple state change | Existing declarative transition; compatible Reanimated CSS transition if available |
| Mount, exit, or genuine reflow | Supported layout/lifecycle animation with stable identity |
| Continuous drag or scroll response | UI-runtime shared values and gesture primitives |
| Complex illustration | An appropriate existing asset/rendering tool, with a static equivalent |

Inspect versions before choosing an API. An existing adequate implementation need not be rewritten. Reanimated/Worklets compatibility is version-specific. [Compatibility](https://docs.swmansion.com/react-native-reanimated/docs/guides/compatibility/).

## Make gestures continuous and recoverable

Define idle, tracking, settling, committed, and canceled outcomes. On takeover, continue from the current visible position, cancel competing motion where necessary, and preserve appropriate release velocity. Explicitly resolve direction, scroll competition, thresholds, boundaries, cancellation, and repeated input. Use native/library gesture behavior before implementing a custom state machine.

A spring often suits momentum and interruptible settling; timing can suit a deliberate two-state change. Choose parameters from the intended behavior and test them. Do not impose one spring or easing curve on every surface.

Keep continuous calculations on the UI runtime. Send semantic events to React at deliberate boundaries, with protection against duplicate commits. React state is appropriate for discrete press/selection changes, not as a per-frame animation transport. Reanimated get/set is compiler-compatible; shared-value reads or writes during render are invalid. [Shared values](https://docs.swmansion.com/react-native-reanimated/docs/core/useSharedValue/).

## Preserve geometry and exit lifecycle

Prefer non-layout animated properties when they express the intended result without distortion. They still cost rendering work; backgroundColor is also non-layout. Legitimate layout animation should be measured and profiled, not replaced with misleading scaling. [Performance guidance](https://docs.swmansion.com/react-native-reanimated/docs/guides/performance/).

Measure relevant container/content bounds and refresh after text scaling, content updates, resizing, or orientation changes. Avoid fixed offscreen distances for variable content. Check transformed hit regions and clip boundaries.

An exit must define when semantic state changes, when the element unmounts, and what happens if interrupted. Maintain visible content long enough for an intended exit, but never make important state depend solely on decorative completion. Handle canceled exits, reduced motion, remote removal, failed optimistic changes, and focus restoration. Do not animate recycled rows as though every remount is new content.

## Reduced motion and optional haptics

Keep the same information, actions, and final state with reduced motion. Prefer immediate state changes or quieter alternatives where appropriate; remove unnecessary travel, parallax, and overshoot. Preserve native preference handling and verify effective per-screen options: a child override can defeat a parent fallback.

Reanimated normally respects ReduceMotion.System, but useReducedMotion reports the startup setting and does not itself rerender on changes. For custom behavior that must update live, use an appropriate reactive preference source such as AccessibilityInfo's query and change event. Test preferences both before launch and while open. [Reanimated accessibility](https://docs.swmansion.com/react-native-reanimated/docs/guides/accessibility/), [useReducedMotion](https://docs.swmansion.com/react-native-reanimated/docs/device/useReducedMotion/), [AccessibilityInfo](https://reactnative.dev/docs/accessibilityinfo).

Use haptics sparingly at meaningful selection, threshold, or result events. Avoid duplicates from native controls and per-frame pulses. Pair them with visible feedback; hardware and preferences can suppress them. Android has dedicated haptic APIs. Scheduling at the causal event does not prove exact-frame delivery. [Expo Haptics](https://docs.expo.dev/versions/v56.0.0/sdk/haptics/).

## Verify what cannot be inferred

Exercise rapid repeats, short flicks, slow drags, mid-flight takeover, reversal, cancellation, keyboard interaction, changed content, and reduced motion. Check that state remains correct without animation. Inspect performance in a release build on representative supported devices, especially slower hardware. Simulator recordings and source review can establish narrower findings; they cannot establish physical haptic timing or release-device smoothness. Report the evidence and remaining checks precisely.
