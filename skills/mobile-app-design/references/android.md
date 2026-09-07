# Android

Platform guidance checked 2026-09-07. Resolve device OS, target SDK, installed Expo/React Native, navigator, and component support before using version-dependent behavior. Native Compose examples establish platform expectations; translate through the project's supported APIs. Use [Interaction and state](interaction-and-state.md) for shared flow mechanics.

## Familiar behavior, flexible expression

Preserve system navigation, input, accessibility, and permission behavior while shaping a distinct visual identity. Material supports custom color roles, typography, and shapes. A brand palette does not require abandoning familiar controls, and Android quality does not require every product to reproduce a stock sample. Use the existing theme/component abstractions where they support the intended result. [Material 3](https://developer.android.com/develop/ui/compose/designsystems/material3).

Choose primary navigation for the destination structure and available window. A navigation bar commonly holds three to five peers; richer structures may need another presentation. Wider windows often benefit from a navigation rail or persistent drawer. Supporting content can become an adjacent pane instead of an oversized phone screen. [Navigation patterns](https://developer.android.com/design/ui/mobile/guides/layout-and-content/layout-and-nav-patterns), [Adaptive navigation](https://developer.android.com/develop/adaptive-apps/guides/build-adaptive-navigation).

## System back and transient surfaces

Distinguish app Up from system Back. Up remains within the app hierarchy; Back can return to the application that opened a deep link. Let the navigator own ordinary behavior. Intercept back only for a concrete interaction that needs it, and preserve system root navigation. [Navigation principles](https://developer.android.com/guide/navigation/principles).

Predictive back previews the destination before commitment. Custom transitions must support gesture cancellation as well as completion. On Android 16 devices for apps targeting API 36+, predictive system animations are enabled by default and legacy back callbacks are no longer dispatched. Confirm the installed navigation library's integration before adding handlers or manifest changes. [Predictive-back setup](https://developer.android.com/develop/ui/compose/system/predictive-back-setup), [Android 16 changes](https://developer.android.com/about/versions/16/behavior-changes-16).

Use modal sheets for bounded interruptions. Use nonmodal supporting surfaces when the parent task must remain interactive. On larger windows, a bottom sheet may become a side surface. Retain the component's back handling, accessible pane announcement, focus behavior, and dismissal affordance when changing its visual treatment. [Bottom sheets](https://developer.android.com/develop/ui/compose/components/bottom-sheets), [Semantics](https://developer.android.com/develop/ui/compose/accessibility/semantics).

## Insets, input, and windows

Treat system bars, gesture areas, display cutouts, window captions, and the keyboard as runtime geometry. Extend backgrounds appropriately while keeping important controls visible and operable. Check existing inset ownership before adding padding; double handling can create large gaps. Test both gesture and three-button navigation. [System bars](https://developer.android.com/design/ui/mobile/guides/foundations/system-bars), [Insets](https://developer.android.com/develop/ui/compose/system/insets-ui).

Edge-to-edge is enforced for SDK 35+ targets on Android 15+ devices. For API 36 targets on Android 16, the previous opt-out is disabled. Adapt the layout rather than relying on a legacy opaque navigation-bar recipe. Keep the focused field, its error, and the next action reachable while the keyboard opens. [Edge-to-edge](https://developer.android.com/develop/ui/views/layout/edge-to-edge), [Android 16 changes](https://developer.android.com/about/versions/16/behavior-changes-16).

Use current window dimensions and posture rather than a phone/tablet boolean. Reflow, constrain, or reveal content as space changes. Android 16 changes the treatment of orientation and resizability restrictions on large screens for affected targets; portrait locking is an unreliable layout strategy. [Adaptive guidance](https://developer.android.com/develop/adaptive-apps/guides/adaptive-dos-and-donts).

## Accessibility and theming

Use **48×48dp as a comfortable custom-control target default**. Padding can make a smaller icon easy to hit. Maintain separation and check neighboring hit areas; evaluate existing native compact controls using their component behavior rather than automatically flagging their visible dimensions. [Accessible controls](https://developer.android.com/guide/topics/ui/accessibility/views/apps-views).

Honor font-size settings through the framework's supported text scaling. Android 14+ supports nonlinear scaling up to 200%; a single multiplier cannot reproduce it. Let rows and labels reflow. Native guidance uses scalable units for text and line height; verify how the React Native version maps these behaviors rather than transferring Compose sizing syntax. [Font scaling](https://developer.android.com/about/versions/14/features).

Check TalkBack names, roles, state descriptions, grouping, and pane changes. Reading order can become incorrect when a single column becomes multiple panes. Keyboard focus order needs its own check. Prefer contextual announcements over a live region that speaks every update. [Semantics](https://developer.android.com/develop/ui/compose/accessibility/semantics), [Traversal](https://developer.android.com/develop/ui/compose/accessibility/traversal).

Pair semantic content and surface colors, checking contrast in actual states. Dynamic color is available on Android 12+; choose its relationship to the brand deliberately and provide appropriate fallback themes. Preserve meaning with animations disabled. Use start/end geometry and test custom directional icons, long strings, and mixed-direction content in RTL. [Material theming](https://developer.android.com/develop/ui/compose/designsystems/material3), [Languages](https://developer.android.com/training/basics/supporting-devices/languages.html).

## Targeted verification

Select checks affected by the change:

- Gesture/three-button navigation; predictive back commit and cancel where supported.
- Keyboard, cutouts, and edge-to-edge; reachable final fields and actions.
- Large font/display settings; compact and resized wide windows.
- TalkBack and relevant hardware-keyboard traversal.
- Light/dark, disabled animations, and long/RTL content.

Record actual OS/runtime coverage; a web preview does not establish these behaviors.
