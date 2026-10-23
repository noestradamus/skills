# WidgetKit

Apple guidance checked 2026-10-23. Use with [iOS](ios.md) and [Interaction and state](interaction-and-state.md). Read [SwiftUI](swiftui.md) when editing native Swift code; for an Expo-owned widget, also read [Expo and React Native](expo-react-native.md). The extension, data, and lifecycle decisions below apply across supported authoring paths; Swift API examples describe the native path.

## Establish the extension boundary

Inspect the installed SDK, deployment targets, supported widget families and placements, extension target, shared code/assets, entitlements, signing, and persistence configuration. WidgetKit uses a separate extension and a limited set of supported views. A supported bridge may generate the extension: preserve its owning configuration instead of editing generated files that the next build replaces. Do not assume the host application's UI runtime or in-memory state exists inside the widget. [Extension architecture](https://developer.apple.com/documentation/widgetkit/creating-a-widget-extension).

Choose the widget's useful glance or quick action before its layout. It is not a compressed app screen. Design each supported family around its information capacity; fewer useful items beat unreadably small copies of a larger widget. Longer reading, text input, and complex editing belong in the app. [Widget HIG](https://developer.apple.com/design/human-interface-guidelines/widgets).

## Make freshness explicit

Build timeline entries from available data and predictable changes, such as an event start or a day boundary. Choose the next refresh from the data's meaning; account for calendar and timezone changes when relevant. A widget is not a continuously running view: timers, ordinary view lifecycle callbacks, or polling cannot promise arbitrary real-time updates. Supported dynamic date views can update their presentation without keeping the extension alive. App-requested reloads are scheduling requests, not proof of an immediate display update; never promise fixed reload quotas or timing. [Timelines and reloads](https://developer.apple.com/documentation/widgetkit/keeping-a-widget-up-to-date).

Distinguish placeholder, gallery example, actual empty data, stale data, failed read, and missing configuration where applicable. Keep useful last-known content with truthful freshness cues when possible. Never display sample progress as real user data. For an ongoing live event, evaluate ActivityKit separately; Live Activities have a different update lifecycle and are not a workaround for refreshing an ordinary dashboard. [Widget strategy](https://developer.apple.com/documentation/widgetkit/developing-a-widgetkit-strategy).

## Persist actions before presenting their result

For supported native deployments, use `Button(intent:)` or `Toggle` with an `AppIntent` for direct actions. Ordinary closure-based app controls do not provide equivalent widget execution. Verify a wrapper's corresponding API instead of substituting native syntax into its runtime. Separate actions from links that open the app. On a locked device, interaction may require authentication. [Widget interactivity](https://developer.apple.com/documentation/widgetkit/adding-interactivity-to-widgets-and-live-activities).

Pass stable entity identifiers, read current persisted state when executing, validate the action, and await necessary writes before returning from `perform()`. Native intent completion triggers a timeline reload; the provider must read the committed result. Handle errors with truthful state rather than leaving a successful-looking toggle after a failed write. Define repeated-action semantics: prefer setting an intended state where appropriate, and protect non-idempotent operations from duplicate execution. Test rapid input against stale entries and deleted entities. These are persistence decisions, not animations. [Intent execution and reloads](https://developer.apple.com/documentation/widgetkit/adding-interactivity-to-widgets-and-live-activities).

## Share data without destroying active work

Use an appropriately entitled App Group when the app and extension share local data. Verify both targets resolve the intended group and store; a shared identifier alone does not prove access or matching schema. Use the storage system's concurrency and change-detection mechanisms. A process-local actor or cache does not coordinate all writers in different processes. Avoid read-modify-write of an entire stale collection when an action changes one record. [App Groups](https://developer.apple.com/documentation/xcode/configuring-app-groups), [Shared data](https://developer.apple.com/documentation/technologyoverviews/shared-data).

On return to the app, reconcile external changes without discarding navigation, presented editors, or unsaved drafts. Re-fetch or merge affected data using the existing persistence architecture; rebuilding the whole root view is not a general synchronization strategy. Resolve conflicts deliberately when a draft and widget change the same entity. For SwiftData, establish migration ownership—normally the app—and a recoverable widget state if the store needs migration. Do not delete a failed store or let competing processes independently migrate it. [SwiftData multiprocess guidance](https://developer.apple.com/videos/play/wwdc2026/8017/?time=173).

## Adapt the actual widget surface

Use system content margins; do not transplant app safe-area arithmetic or globally disable margins to fit extra content. In native SwiftUI, `widgetContentMargins` supports selective adaptation. Mark widget backgrounds with the supported container-background API and verify content when the system removes that background. [Widget views and margins](https://developer.apple.com/documentation/widgetkit/creating-views-for-widgets-live-activities-and-watch-complications), [Backgrounds](https://developer.apple.com/documentation/widgetkit/displaying-the-right-widget-background).

Inspect applicable full-color, accented, and vibrant presentations. Brand colors may be replaced; state must remain understandable through text, shape, and hierarchy. Adapt image rendering and accent groups deliberately, and check contrast after system treatment rather than only against app color tokens. Test supported text sizes, localization, long names, VoiceOver labels/order, and distinguishable action targets. Resolve density before imposing a text-size cap. [Rendering modes](https://developer.apple.com/documentation/widgetkit/preparing-widgets-for-additional-contexts-and-appearances), [Accented rendering](https://developer.apple.com/documentation/widgetkit/optimizing-your-widget-for-accented-rendering-mode-and-liquid-glass).

Review sensitive information on exposed surfaces. Use privacy-sensitive redaction and protection appropriate to the content; verify placeholders reveal no private values. [Privacy](https://developer.apple.com/documentation/widgetkit/creating-a-widget-extension).

## Verify arrival, execution, and return

Route widget taps to the relevant content, with recovery for missing entities or authentication. Use one root `widgetURL` and supported per-item links where appropriate; verify family/OS availability. Test cold launch and warm return without overwriting an active draft. [Deep links](https://developer.apple.com/documentation/widgetkit/linking-to-specific-app-scenes-from-your-widget-or-live-activity).

Preview representative families, appearances, and entries, then install and exercise the actual widget. Check extension reads with the app inactive, successful and failed actions, repeated taps, app-to-widget and widget-to-app updates, date rollover where relevant, and data retained after relaunch. Include locked/privacy behavior when affected. Previews establish layout evidence; they do not establish signing, shared-store access, system scheduling, or multiprocess correctness. Report simulator/device conditions and remaining gaps using [Polish and verification](polish-and-verification.md).
