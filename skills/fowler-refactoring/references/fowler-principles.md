# Fowler Principles and Source Boundary

## Table of contents

- [Use the primary-source boundary](#use-the-primary-source-boundary)
- [Apply the Fowler-derived foundation](#apply-the-fowler-derived-foundation)
- [Apply additional engineering safeguards](#apply-additional-engineering-safeguards)
- [Use terminology carefully](#use-terminology-carefully)
- [Consult the primary sources](#consult-the-primary-sources)

## Use the primary-source boundary

Base this skill primarily on Martin Fowler's *Refactoring* material and the official catalog at `refactoring.com`. Paraphrase concepts and mechanics; do not reproduce catalog prose or book text.

Attribute only the principles in the next section to Fowler's published material. Treat the safeguards in the following section as this skill's modern operational extensions, even when they are compatible with Fowler's approach.

## Apply the Fowler-derived foundation

### Preserve observable behavior

Treat refactoring as restructuring that improves understandability and ease of modification while keeping observable behavior unchanged. Do not use “refactoring” as a synonym for rewriting, feature development, or bug fixing.

Define “observable” from the affected system's real consumers. Include published interfaces and any behavior callers can detect, not only returned values.

### Move through small transformations

Break a design change into behavior-preserving steps small enough to understand, verify, and reverse independently. Prefer a sequence of modest edits over a single large rewrite.

Keep the code in a working state as often as practical. Use frequent tests or equivalent checks to reveal mistakes close to the step that introduced them.

### Wear one hat at a time

Separate the refactoring hat from the adding-function hat. While refactoring, keep behavior stable and treat a newly failing test as evidence of a mistake or an invalid baseline assumption. When adding or correcting behavior, label that work separately and use tests appropriate to the changed contract.

Switch hats when necessary, but establish an explicit verification boundary between them.

### Use smells as investigation prompts

Use smells to locate areas worth examining, then confirm the local design cost and context before changing code. Do not convert a smell list into an automatic rewrite checklist.

Treat this “prompt, not verdict” formulation as the skill's operational interpretation of Fowler's smell-oriented diagnosis, not as a quotation.

### Refactor for economic and comprehension value

Improve code when clearer design is likely to make present or future work easier, safer, or cheaper. Avoid polishing code solely to express personal taste.

Move newly acquired understanding into names, functions, responsibilities, and boundaries so the next reader does not need to reconstruct the same mental model.

### Prefer gradual improvement

Leave touched code easier to understand and change, but do not attempt to perfect an entire codebase in one pass. Keep scope connected to current evidence and expected value.

### Use tools without depending on them

Use reliable IDE or language-server refactorings when available. Still inspect the result and verify behavior. When automation is unavailable, rely on smaller manual steps and more frequent checks.

### Treat published interfaces as observable behavior

Change an internal interface only when all callers can be updated safely. Treat a published interface itself as part of observable behavior; require compatibility handling or explicit authorization before changing it.

## Apply additional engineering safeguards

Do not attribute the following rules specifically to Fowler. Apply them to make autonomous repository work safer:

- Record a command-level baseline and distinguish pre-existing failures from regressions.
- Inspect version-control status and preserve unrelated uncommitted work.
- Use characterization tests to capture legacy behavior when focused tests are absent and the behavior can be observed safely.
- Protect schemas, persistence, serialization, protocols, authentication, authorization, concurrency, binary compatibility, and operational side effects behind explicit approval gates.
- Protect generated, vendored, migration, snapshot, lock, and third-party files from incidental edits.
- Reuse repository-provided build and verification commands rather than installing tools or changing configuration by default.
- Require representative measurements before optimization-driven restructuring.
- Stop or reduce scope when verification cannot support a credible behavior-preservation claim.
- Prefer repository-native architecture and language idioms over a universal design prescription.
- Report suspected defects separately instead of silently correcting them during structural cleanup.

## Use terminology carefully

Use the current second-edition catalog name when practical and mention a familiar alias only for navigation, such as “Extract Function (often called Extract Method).”

Call a change a refactoring only when its observable contract remains stable. Call an authorized contract change a feature, bug fix, migration, compatibility change, or optimization as appropriate.

Avoid claiming that Fowler requires a specific test framework, object-oriented architecture, commit strategy, code metric, or tool. Adapt the process to the repository's language and conventions.

## Consult the primary sources

Use these primary sources to verify attribution and catalog names:

- [Refactoring.com home and definition](https://refactoring.com/)
- [Official catalog of refactorings](https://refactoring.com/catalog/)
- [Martin Fowler's Refactoring book page](https://martinfowler.com/books/refactoring.html)
- [Workflows of Refactoring and the two-hats discussion](https://martinfowler.com/articles/workflowsOfRefactoring/)
- [Preparatory Refactoring example](https://martinfowler.com/articles/preparatory-refactoring-example.html)
- [Changing interfaces and published-interface caution](https://martinfowler.com/bliki/IsChangingInterfacesRefactoring.html)

When a proposed attribution is not supported by these or another primary Fowler source, present it as an additional safeguard or omit the attribution.
