# SwiftUI implementation

Technical guidance checked 2026-10-23. Use with [iOS](ios.md) for platform behavior, [Interaction and state](interaction-and-state.md) for flow decisions, and [WidgetKit](widgetkit.md) for extension surfaces. SwiftUI implementation does not imply an architecture migration or a different visual identity.

## Resolve the actual build context

Inspect the workspace/project or its generator, app and extension targets, schemes, deployment targets, selected SDK, Swift language/concurrency settings, and dependencies before proposing APIs. Determine which target compiles each shared file. Modify generated projects through their established source configuration.

An SDK's available API and the oldest supported runtime are separate constraints. Check declarations against the installed SDK; use availability guards and a usable fallback when a feature requires a newer runtime. A runtime guard cannot teach an older compiler an unknown API. Do not raise deployment targets merely to simplify a visual change. [Availability](https://developer.apple.com/documentation/xcode/running-code-on-a-specific-version/).

## Preserve ownership, identity, and drafts

Keep one source of truth for committed data and make editing ownership explicit. In an Observation-based project, `@State` can own an observable model's lifetime, while `@Bindable` supplies editable bindings; consuming an observable value does not automatically require either wrapper. SwiftUI Observation starts at iOS 17. Preserve suitable `ObservableObject`, `@StateObject`, and `@ObservedObject` patterns in existing or earlier-target code. A screen polish is not a reason to replace the persistence layer or observation system. [Model data](https://developer.apple.com/documentation/swiftui/managing-model-data-in-your-app), [Incremental adoption](https://developer.apple.com/documentation/swiftui/migrating-from-the-observable-object-protocol-to-the-observable-macro).

Use stable entity identifiers in dynamic lists and presentation state. Avoid changing a root `.id` to force a refresh: view identity determines state lifetime, so this can discard navigation, focus, and an editor's local state. Diagnose the missing observation or refresh boundary instead. Conditional branches also affect identity; choose them deliberately where state must survive. [Identity and lifetime](https://developer.apple.com/videos/play/wwdc2021/10022/).

For cancelable editors, distinguish an editable draft from the saved object. Directly binding every field to persistent properties can make Cancel misleading; select a draft/commit strategy that fits the existing store. Decide when saving occurs, how errors retain edits, and what survives backgrounding or termination. A `@State` value alone is not durable storage. Reconcile external updates without rebuilding the entire interface; define how an incoming change interacts with a dirty draft.

## Keep navigation state intentional

Use the existing navigation abstraction. When programmatic navigation, deep links, or restoration are needed, a data-driven `NavigationStack` path provides explicit state. Prefer lightweight route values and stable IDs to carrying mutable model snapshots through a path. Keep independent destination histories where the product requires them; do not put an unrelated fresh stack inside every screen. [Navigation state](https://developer.apple.com/documentation/swiftui/understanding-the-navigation-stack).

Bind presentation to the selected item when identity matters. Resolve Save, Cancel, interactive dismissal, validation, and return focus together. Disable dismissal only while losing meaningful work or invalidating an operation; provide a visible exit. For a restored or widget-linked destination, handle missing/deleted records and an intelligible return path. Test the actual back gesture and sheet behavior after custom navigation styling.

## Adapt content and preserve semantics

Let stack, list, form, grid, and scroll containers negotiate available space. Change composition when content cannot fit; `ViewThatFits` selects among preferred alternatives, while custom `Layout` is appropriate when built-in containers cannot express the relationship. Avoid device-name branching and fixed row heights that hide growing text. [Layout](https://developer.apple.com/documentation/swiftui/layout-fundamentals).

Use semantic text roles; scale custom fonts relative to the matching text style. Try wrapping, vertical composition, and reducing secondary content before shrinking essential text or capping Dynamic Type. Inspect long localized strings and accessibility sizes in the intended containers. [Custom fonts](https://developer.apple.com/documentation/swiftui/font/custom(_:size:relativeTo:)).

Keep bottom actions and focused fields inside the usable region. Prefer container safe-area behavior and appropriate insets; limit edge-ignoring treatment to content that should extend there. Inspect keyboard-open validation and scrolling before adding manual keyboard offsets. Use `FocusState` to express field progression, with distinct field identities. Keyboard focus and assistive-technology focus are different systems. [FocusState](https://developer.apple.com/documentation/swiftui/focusstate/), [AccessibilityFocusState](https://developer.apple.com/documentation/swiftui/accessibilityfocusstate).

Use `Button`, `Toggle`, `Picker`, and `NavigationLink` for their semantic actions; style those controls before rebuilding them from tap gestures. Preserve native labels and values when correct. Custom icon/color choices need localized human meanings, selected state, and useful grouping; SF Symbol identifiers or internal token names are not suitable spoken labels. Do not combine a row into one accessibility element if that hides independently actionable controls. Verify traversal and activation with VoiceOver. [Accessibility modifiers](https://developer.apple.com/documentation/swiftui/view-accessibility).

## Own asynchronous work and motion

Attach view-scoped async loading to `.task` or `.task(id:)` when its lifetime should follow that view or request identity. Changing the ID cancels and restarts the task; cancellation is cooperative. Check cancellation and request identity before publishing late results, and avoid converting intentional cancellation into a user-facing error. Work that must survive dismissal belongs to a longer-lived owner with explicit recovery. [View tasks](https://developer.apple.com/documentation/swiftui/view/task(id:name:priority:file:line:_:)), [Cancellation](https://developer.apple.com/documentation/swift/task).

Honor model isolation when applying results. Keep expensive synchronous work out of `body` and UI-isolated execution; `async` alone does not guarantee background execution. Check the project's concurrency settings before prescribing an isolation mechanism. [SwiftUI concurrency](https://developer.apple.com/videos/play/wwdc2025/266/).

Preserve system transitions unless customization serves the task. Scope custom animation to the relevant change and subtree; a broad animation modifier can animate unrelated updates. Read `accessibilityReduceMotion` from the environment and apply the alternative consistently to child transitions, effects, and repeated feedback. State correctness must survive omitted or interrupted animation. Use [Motion](motion.md) for interaction criteria, with SwiftUI APIs rather than React Native recipes. [Animations](https://developer.apple.com/documentation/swiftui/animations), [Reduce Motion](https://developer.apple.com/documentation/swiftui/environmentvalues/accessibilityreducemotion).

## Verify the implemented surface

Use previews with explicit sample states and isolated dependencies; keep preview fixtures out of production stores. Preview success checks the rendered fixture, not the complete app lifecycle. Build the affected scheme/targets and exercise relevant navigation, keyboard, persistence, and interruption behavior in the app. For cross-process changes, include widget-to-app return with an open editor. [Previews](https://developer.apple.com/documentation/xcode/adding-previews-to-your-interface-files).

Report the actual SDK, scheme, runtime, and checks used. Distinguish a preview from simulator interaction, VoiceOver testing, and release-device measurement. Use [Polish and verification](polish-and-verification.md) for evidence limits and stopping criteria.
