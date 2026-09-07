# Design direction

Read for a new screen, a redesign, an unresolved hierarchy, or asset direction. For a narrow refinement, retain the established visual system and go directly to the affected decisions.

## Find the decisions that matter

Start with the situation of use: who is doing what, how frequently, with how much attention, on what device, with what content and interruption risk. Translate this into design consequences. A commuter tracking an arrival needs a dominant time and recoverable one-handed actions; a reflective journal can devote more space to composition and writing.

Identify the primary task and the information necessary to complete it. Distinguish navigation, content, actions, and feedback. Choose progressive disclosure for secondary complexity while keeping prerequisites and consequences visible. Do not hide essential actions behind gestures, ornamental icons, or ambiguous overflow menus.

Use real product language and representative content: long names, missing imagery, localized prices, mixed scripts, multiline messages, and actual item counts. Preserve unknown data as unknown rather than replacing it with convincing sample success. Label prototype data and unimplemented behavior appropriately.

## Study references to answer a question

Inspect the supplied references first. For a novel pattern, study relevant shipping products or official platform examples until the uncertainty is resolved. Research should answer a decision such as how a draft survives a sign-in interruption, how dense records stay scannable, or how a sheet behaves with a keyboard. A screen count is not a stopping rule.

Extract hierarchy, relationships between screens, density, control roles, and interaction behavior. A still image does not reveal dismissal, state persistence, gesture physics, or conversion effectiveness. If those matter, examine the flow or mark what remains unknown. Revenue ranking and popularity do not establish usability or suitability.

Record a brief rationale for the adopted pattern. Preserve the user's own identity, content, assets, and explicit reference constraints. Do not copy a reference product's identity or incidental provider watermarks; preserve supplied, authorized brand assets and required integration branding. If browsing or a specialist service is unavailable, use the provided evidence and platform conventions; avoid invented research or mandatory subscriptions.

## Commit to a visual thesis

Describe the chosen direction in a few concrete sentences. Resolve:

- **Hierarchy and composition:** what dominates, where repeated content aligns, which groups share a surface, how the primary action relates to the content.
- **Density and rhythm:** content-led spacing, scan paths, grouping, and room for fingers and text growth. A scale guides repeated relationships; optical adjustments need not be forced onto a grid.
- **Typography:** roles, weight/size contrast, line length, scripts, numeric alignment, and scaling behavior. A distinctive font must support the content and accessibility requirements.
- **Color and material:** semantic meanings, accent roles, theme behavior, elevation, and contrast. Multiple accents can be appropriate when their roles are stable and comprehensible without color alone.
- **Imagery and motion:** whether each serves explanation, recognition, emotion, or feedback; where restraint protects speed and attention.

Offer a small set of meaningfully different directions only when choosing direction is part of the task or the brief leaves a consequential ambiguity. Do not generate cosmetic variants or pause for approval after the user has already chosen the direction.

Concrete directions should lead to different results. A field-service tool might emphasize dense labeled status rows, persistent task context, large practical actions, and quiet transitions. A music journal might use expressive cover imagery, a custom title face, colored annotations, and a spacious editor while retaining native text entry and navigation. A dense tool need not become bland; an expressive product need not make every surface decorative.

## Compose for mobile

Use content and task relationships to choose lists, grouped settings, cards, grids, or full-bleed media. A card earns its container through grouping, interaction, or separation; avoid wrapping every line in another surface. Establish a clear first read, then a secondary scan, then detail.

Place frequent actions where they are reachable without obscuring content or system gestures. Keep contextual actions near their subject; reserve persistent bottom actions for an enduring primary task. Resolve scroll, keyboard, safe areas, loading, and large-text growth before fixing a bottom bar in place. Avoid competing floating controls.

Adapt by available width and task: a compact list-to-detail sequence can become a two-pane layout while preserving selection and navigation context. Increasing font size or rotating the device should not strand the user, hide a focused field, or erase a draft. Avoid uniform shrink-to-fit solutions.

## Define just enough system

Reuse existing tokens and shared components. For new work, define recurring roles for text, spacing, surfaces, actions, borders, icons, and motion as they become real. Separate semantic roles from raw values so themes and states remain consistent. One local exception does not require a new abstraction; a repeated decision should not be reinvented across screens.

Prefer native controls for conventional interactions. Custom components are appropriate for domain-specific interaction or an intentional identity, provided they preserve touch behavior, semantics, focus, keyboard access where applicable, and system preferences. Keep icon families coherent; use meaningful labels when a symbol is not self-explanatory.

## Use assets intentionally

Use supplied or existing assets when they fit. Generate or source imagery only when it improves the requested surface. Establish palette, rendering style, composition, crop, lighting, and theme treatment across a set. Protect subject placement across sizes; provide stable geometry and intentional placeholders during loading.

Choose dimensions and formats for the actual display size and density, with reasonable memory/decode costs. Vector icons generally serve chrome better than raster approximations. Inspect halos, transparency, crop, contrast, legibility, and compression on the destination surface. Decorative imagery should not acquire misleading accessibility labels. Do not require an image-generation tool for a screen that works better without illustration.
