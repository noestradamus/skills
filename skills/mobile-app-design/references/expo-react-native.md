# Expo and React Native implementation

Use this reference for Expo/React Native implementation, not a SwiftUI app. Base guidance checked 2026-09-07; motion and widget routing checked 2026-10-23. Match it to the installed project rather than assuming today's APIs apply. Resolve interaction semantics in [Interaction and state](interaction-and-state.md), platform behavior in [iOS](ios.md) and [Android](android.md), and motion intent in [Motion](motion.md).

## Establish compatibility before selecting APIs

Read package.json, the lockfile, app configuration, existing navigators, theme/components, Babel setup, and relevant native configuration. Identify installed Expo SDK, React Native, Router, Reanimated, Worklets, Gesture Handler, styling system, architecture, and supported OS versions. Inspect installed types when an example and the project disagree.

Each Expo SDK targets a specific React Native version. Reanimated 4 requires New Architecture and compatible Worklets; compatibility can differ between patches. Do not upgrade the framework to implement a visual preference. When a dependency is needed, use the project's package manager and Expo's compatible installation path rather than npm latest. [Expo SDK compatibility](https://docs.expo.dev/versions/latest/), [Reanimated compatibility](https://docs.swmansion.com/react-native-reanimated/docs/guides/compatibility/).

## Select components by required behavior

Prefer an existing component that already satisfies the task. Otherwise choose native or established primitives before custom implementations.

| Need | Selection check |
| --- | --- |
| Standard switch, picker, menu, or form control | Does the installed native/project component support the required values, labels, disabled state, and both platforms? |
| Small settings group | Use a suitable grouped-row component; verify its label/value/action semantics. |
| Feed, catalog, or unbounded results | Use a virtualized list with stable item identity. |
| Sheet | Determine route destination versus local modal versus persistent inline panel before selecting technology. |
| Distinctive custom interaction | State the benefit and implement accessibility, cancellation, state, and platform behavior it replaces. |

`@expo/ui` can be a useful native option on compatible SDKs; it is not a mandatory migration. Its native bottom-sheet replacement is modal and does not support persistent inline peek. Some compatibility props are accepted without affecting native behavior. Check actual capability before swapping libraries. [Bottom-sheet compatibility](https://docs.expo.dev/versions/latest/sdk/ui/drop-in-replacements/bottomsheet/).

Keep route files focused on routes and layouts. Preserve deep-link identity and navigation state during refactoring. Platform-specific route files are supported when a non-platform counterpart exists; extracting platform components is also valid. SDK 56+ changes React Navigation import entry points, so check the installed Router before copying imports. [Platform modules](https://docs.expo.dev/router/advanced/platform-specific-modules/), [Router reference](https://docs.expo.dev/versions/latest/sdk/router/).

Keep server state in the existing data layer and transient UI state near its owner. Give drafts the persistence their recovery contract requires. Introduce a cache, store, or persistence library for a demonstrated need, not because a design source names one.

## Layout, lists, and insets

Use flex layout and content-driven sizing. Use reactive window/container measurements when necessary; invalidate measurements after resizing, text scaling, content changes, or orientation changes. Avoid fixed heights for variable text.

Choose ScrollView for bounded content that needs scrolling and FlatList/SectionList or the established virtualized component for large datasets. Avoid wrapping a same-direction virtualized list inside a plain ScrollView. Place its surrounding content in the list's header/footer when appropriate. Keep keys stable, preserve visible position when data changes, and avoid replaying entrance animations as rows are recycled. A short grouped native list is not automatically a virtualized feed.

Assign inset ownership per edge: navigator, scroll container, or screen. Verify top and bottom without double padding. `contentInsetAdjustmentBehavior` is an iOS API, not an Android safe-area solution. Put content padding on the scroll content container, and keep fixed overlays clear of system controls. Maps and cameras need intentional edge-to-edge layout rather than an unconditional root ScrollView. [ScrollView](https://reactnative.dev/docs/scrollview#contentinsetadjustmentbehavior).

## Forms and keyboard

Choose input type, return action, autofill, capitalization, secure entry, and validation from the field's meaning. Keep labels visible and error messages associated with inputs. Test the last field and submit action with the keyboard open and enlarged text; avoid clearing input after recoverable failure.

Controlled inputs fit ordinary forms; isolate typing state and measure expensive downstream rendering before changing that contract. Preserve IME composition and cursor behavior. Select autofill props deliberately: RN advises against setting both autoComplete and textContentType together because iOS gives the latter precedence. [TextInput](https://reactnative.dev/docs/textinput).

Commit a Pressable action through successful activation (normally onPress), not merely onPressOut. HitSlop cannot extend beyond parent bounds and overlapping siblings have precedence; verify the effective target rather than asserting size from padding alone. [Pressable](https://reactnative.dev/docs/pressable).

Core keyboard avoidance can handle simple layouts. For complex forms or content that follows an interactive keyboard, consider the installed keyboard-controller components and provider. Avoid combining several independent keyboard-offset mechanisms. Reanimated's current useAnimatedKeyboard is deprecated; verify the project's supported alternative before copying old recipes. General guides and SDK pages can disagree about Expo Go inclusion; use the SDK-specific library reference and actual binary. [Keyboard guide](https://docs.expo.dev/guides/keyboard-handling/), [Reanimated keyboard deprecation](https://docs.swmansion.com/react-native-reanimated/docs/device/useAnimatedKeyboard/), [SDK 56 controller](https://docs.expo.dev/versions/v56.0.0/sdk/keyboard-controller/).

## Styling and rendering

Extend the existing token and styling system. Inline styles, StyleSheet, and an established styling library are implementation choices. Use semantic color roles; verify light/dark and high-contrast combinations. For animated color properties, check supported representations. Keeping semantic colors on a normal child while animating its wrapper can avoid unnecessary interpolation.

Select shadows by capability and intended depth. `boxShadow` requires New Architecture; Android outset/inset support begins at Android 9/10. Elevation also affects stacking. Avoid a global replacement that changes layering or excludes supported devices. [Shadow APIs](https://reactnative.dev/docs/shadow-props), [View styles](https://reactnative.dev/docs/view-style-props#boxshadow).

## Motion and feedback in React Native

Keep existing native navigation and control transitions where adequate. For custom work, select compatible Reanimated CSS transitions for simple state changes, layout/entering/exiting APIs for genuine lifecycle changes, or shared values with gesture primitives for continuous manipulation. These are options, not a reason to upgrade or replace an existing solution. Verify installed Reanimated/Worklets/architecture compatibility before choosing an API.

Keep continuous calculations on the animation/UI runtime. Send semantic events to React at deliberate boundaries; React state suits discrete selection, not per-frame animation transport. Do not read or write shared values during render. Reanimated's `get`/`set` methods provide a React Compiler-compatible route where supported. [Shared values](https://docs.swmansion.com/react-native-reanimated/docs/core/useSharedValue/).

Prefer transform/opacity when they express the intended effect, without treating other properties as forbidden. Animated colors, including `backgroundColor`, are non-layout but still consume rendering work; legitimate reflow needs measurement. [Performance](https://docs.swmansion.com/react-native-reanimated/docs/guides/performance/).

Reanimated normally respects `ReduceMotion.System`; `useReducedMotion` reports the startup preference and does not itself trigger rerenders on changes. For custom behavior that must update live, use an appropriate reactive source such as `AccessibilityInfo`'s query and change event. Inspect child overrides and test the final state with motion disabled. [Accessibility](https://docs.swmansion.com/react-native-reanimated/docs/guides/accessibility/), [useReducedMotion](https://docs.swmansion.com/react-native-reanimated/docs/device/useReducedMotion/), [AccessibilityInfo](https://reactnative.dev/docs/accessibilityinfo).

Use existing platform-aware feedback primitives, or compatible Expo Haptics when needed. On Android prefer its dedicated haptic API where appropriate. Trigger once at the semantic event; native feedback may already cover it, and hardware/preferences can suppress it. [Expo Haptics](https://docs.expo.dev/versions/latest/sdk/haptics/).

## Widgets in an Expo/React Native project

For Apple widgets also read [WidgetKit](widgetkit.md). Inspect the existing integration before choosing handwritten SwiftUI or a compatible bridge. Current `expo-widgets` uses Expo UI in an isolated widget runtime, not the app's ordinary React Native tree; it has no React hooks, app state, or async work inside widget components. Match examples to the installed SDK/package and keep generated target settings in their owning config. Native configuration changes need a rebuilt binary; Expo Go does not validate the widget.

For `expo-widgets`, a running-app interaction listener is insufficient for actions while the app is terminated. Verify the supported interaction path and persistence/reconciliation contract; a widget props update is not proof that the app's domain store changed. Read the current package docs for version-specific behavior. [Expo Widgets](https://docs.expo.dev/versions/latest/sdk/widgets/).

## Verify in the appropriate runtime

Use existing project scripts and a compatible preview for iteration. Expo Go cannot validate arbitrary native configuration; production projects commonly use development builds. Release builds on representative physical devices establish performance and feel. [Development-build FAQ](https://docs.expo.dev/develop/development-builds/faq/).

Run relevant type/build checks, inspect actual native output where possible, and exercise the affected path. Report the platform, runtime, states, and evidence obtained. A successful web preview or compile does not establish native keyboard, gesture, accessibility, or device performance behavior. Follow [Polish and verification](polish-and-verification.md) for acceptance and coverage gaps.
