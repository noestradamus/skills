# iOS and iPadOS

Platform guidance checked 2026-09-07. Before choosing release-specific controls or effects, resolve the minimum iOS version and the installed Expo, React Native, and navigator support. Use [Interaction and state](interaction-and-state.md) for shared flow mechanics and [Motion](motion.md) for custom animation.

## Native behavior, product identity

Prefer established controls for ordinary input, selection, navigation, and system tasks. Customize hierarchy, type, imagery, shapes, and color roles to express the product. Apple permits custom fonts and colors; their legibility and accessibility behavior still need implementation. A custom control inherits responsibility for semantics, hit testing, feedback, and adaptation. [Typography](https://developer.apple.com/design/human-interface-guidelines/typography), [Color](https://developer.apple.com/design/human-interface-guidelines/color).

Choose list containment by the content relationship: grouped settings, uninterrupted reading, and image collections need different treatments. Use a spacing scale for consistency while respecting system margins, text metrics, and optical alignment. A universal eight-point arithmetic rule is not a substitute for these judgments.

## Navigation and presentation

Keep destinations distinct from contextual actions. Tabs suit stable top-level areas; choose their count from the information structure and avoid hidden overflow where possible. Concise, understandable labels matter more than an arbitrary one-word requirement. Current iPadOS guidance permits a tab bar and toolbar together, so judge their composition by usable space and task relevance. Preserve the navigator's native interactive back behavior when customizing its appearance. [Tab bars](https://developer.apple.com/design/human-interface-guidelines/tab-bars), [Toolbars](https://developer.apple.com/design/human-interface-guidelines/toolbars).

Choose a sheet for a scoped task related to the current context. iOS sheets can be modal or nonmodal; a formatting panel that affects selected content differs from a blocking editor. Longer work may need a full screen. Match detents to usable content and keyboard space instead of assigning every sheet half-screen height. On iPad, consider whether a popover, sidebar, or supporting pane better preserves context. [Sheets](https://developer.apple.com/design/human-interface-guidelines/sheets).

## Geometry and adaptation

Let backgrounds and artwork extend to the edges while positioning important content using current safe areas and system guides. Avoid storing notch, home-indicator, toolbar, or keyboard heights as layout constants. Check which container already handles insets before adding padding. A bottom action must remain reachable when input or validation increases the screen's occupied space. [Layout](https://developer.apple.com/design/human-interface-guidelines/layout).

Design iPad layouts for resizable windows, including narrow windows. Reveal supporting content and constrain reading widths as space grows; retain a recognizable hierarchy as panes disappear. Choose layout transitions from whether the content fits, not merely whether the device is called an iPad. Current window behaviors and available navigation presentations depend on the supported OS and framework.

## Accessible text and controls

Use **44×44pt as a comfortable custom-control target default**, with enough separation to avoid ambiguous hits; the visible icon can be smaller. Native compact controls are not automatically violations. Current Apple tables distinguish 44pt default control size from smaller minima, so report measured usability and the applicable component guidance rather than asserting a universal 44pt platform mandate. [Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility).

Use semantic text roles and support the user's text size. The 17pt body default is not a requirement that every caption or label use 17pt. With larger text, grow rows, reflow trailing controls, and preserve important content. Custom fonts need scaling and appropriate script coverage. An ordinary `xxxLarge` cap excludes larger accessibility categories; solve layout problems before limiting scaling. [Typography](https://developer.apple.com/design/human-interface-guidelines/typography).

Check VoiceOver grouping, names, values, and change announcements in the native app. Preserve useful native semantics instead of layering redundant labels over them. Hardware-keyboard navigation and VoiceOver are separate experiences. Standard iPad shortcuts and Full Keyboard Access should remain usable. [VoiceOver](https://developer.apple.com/design/human-interface-guidelines/voiceover), [Keyboards](https://developer.apple.com/design/human-interface-guidelines/keyboards).

## Appearance and localization

Use semantic foreground/background roles and test custom colors in light, dark, and increased contrast. Glass and translucency require contrast checks over actual scrolling content; adopt release-specific material through supported components. Supply stable alternatives when transparency or motion is reduced. [Color](https://developer.apple.com/design/human-interface-guidelines/color), [Reduced Motion](https://developer.apple.com/help/app-store-connect/manage-app-accessibility/reduced-motion-evaluation-criteria).

Use leading/trailing alignment and locale-aware formatting. Check custom navigation icons in RTL; mirror directional meaning while preserving photographs and literal physical directions. [Right to left](https://developer.apple.com/design/human-interface-guidelines/right-to-left).

## Targeted verification

Select checks affected by the change:

- Small phone with large accessibility text; reachable controls and readable content.
- Keyboard open, final input, and validation; correct insets and sheet height.
- Native back gesture, modal presentation, and dismissal.
- Narrow/wide iPad window; preserved hierarchy and usable keyboard interaction.
- VoiceOver, relevant appearance settings, and long/RTL content.

Report what ran on native runtime, what was inspected, and what remains unverified.
