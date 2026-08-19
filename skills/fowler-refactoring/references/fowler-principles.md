# Fowler Principles and Source Boundary

## Contents

- [Use the source boundary](#use-the-source-boundary)
- [Apply Fowler-derived foundations](#apply-fowler-derived-foundations)
- [Apply the additional safeguards](#apply-the-additional-safeguards)
- [Define observable behavior](#define-observable-behavior)
- [Wear one hat at a time](#wear-one-hat-at-a-time)
- [Use smells as diagnostic signals](#use-smells-as-diagnostic-signals)
- [Prefer the smallest sufficient change](#prefer-the-smallest-sufficient-change)
- [Keep a fast feedback loop](#keep-a-fast-feedback-loop)
- [Separate refactoring from optimization](#separate-refactoring-from-optimization)
- [Avoid speculative design](#avoid-speculative-design)
- [Use catalog terminology responsibly](#use-catalog-terminology-responsibly)
- [Primary sources](#primary-sources)

## Use the source boundary

Use Martin Fowler's *Refactoring* material and the official catalog as the conceptual foundation. Paraphrase the ideas and mechanics in original language. Use catalog names as navigational labels, not as permission to reproduce the book or catalog text.

Attribute only the principles verified by the primary sources listed below. Label repository, compatibility, security, concurrency, and agent-operating controls as safeguards added by this skill unless a primary source explicitly supports the attribution.

Do not treat every item on `refactoring.com` as equally current. Prefer the second-edition catalog and Fowler's own articles. When an older alias or non-catalog technique appears, label it accurately.

## Apply Fowler-derived foundations

Apply these foundations as Fowler-derived:

1. **Preserve observable behavior.** Change internal structure to improve comprehension and future modification cost without intentionally changing what the software does from an observer's perspective.
2. **Use small transformations.** Reach a substantial redesign through a sequence of limited changes rather than one large rewrite.
3. **Keep the program working.** Verify often enough that a failure can be associated with the most recent small step.
4. **Separate the two hats.** Refactor under a behavior-preserving constraint. Add or change behavior under a different mode with different tests and acceptance.
5. **Investigate smells.** Treat a smell as a visible clue that may point to a deeper design problem; inspect context before acting.
6. **Choose named transformations deliberately.** Use the catalog to reason about intent, preconditions, mechanics, inverses, and safe sequencing.
7. **Apply the ideas across languages.** Translate the intent into the target language's idioms instead of copying JavaScript- or class-specific forms.
8. **Use tools as assistance, not proof.** Accept IDE automation when useful, but rely on small steps and tests to detect mistakes.
9. **Distinguish optimization from refactoring.** Judge refactoring by design improvement and optimization by measured runtime effect.
10. **Improve code that needs to change.** Favor refactoring where clearer structure lowers the cost or risk of current and likely work, not as a ritual applied indiscriminately.

Do not overstate the foundation. Fowler's catalog does not guarantee that a named transformation is appropriate in every context, nor does a code smell prove that code is defective.

## Apply the additional safeguards

Apply these controls as modern operational safeguards introduced by this skill:

- Inventory public APIs, schemas, serialization, protocols, side effects, security decisions, concurrency behavior, numerical behavior, and timing-sensitive contracts before editing.
- Inspect repository and directory instructions before choosing tools or files.
- Record version-control status and preserve unrelated uncommitted work.
- Detect project-provided build and verification commands instead of imposing a package manager, test framework, or architecture.
- Record pre-existing failures and compare the same checks after editing.
- Use characterization tests when legacy behavior is important but insufficiently documented.
- Escalate changes to public, persistence, protocol, security, concurrency, and performance boundaries.
- Protect generated, vendored, migration, snapshot, configuration, and lock files unless explicitly included.
- Review the final diff for accidental behavior changes and excessive churn.
- Stop when verification cannot support a credible behavior-preservation claim.

Do not attribute these safeguards to Fowler merely because they are compatible with his approach.

## Define observable behavior

Define observation from the perspective of all relevant consumers, not only a unit test or function return value.

Include applicable:

- return values, yielded values, emitted events, rendered output, and ordering;
- exceptions, error values, status codes, messages, and failure timing relied upon by callers;
- state mutation, persistence, network calls, file operations, logging, metrics, and other side effects;
- the number, order, parameters, and retry behavior of external calls;
- public names, signatures, overloads, defaults, keyword arguments, exports, binary interfaces, and extension points;
- serialized field names, encodings, schemas, migrations, wire formats, and database representations;
- authorization, authentication, validation, sanitization, redaction, and audit behavior;
- transaction, lock, atomicity, thread-safety, async, cancellation, and scheduling semantics;
- precision, rounding, units, locale, timezone, collation, randomization, and deterministic ordering;
- startup, shutdown, cleanup, resource lifetime, and externally meaningful timing or performance limits.

Exclude purely internal representation details only after confirming that no reflection, plugin system, serializer, framework convention, test seam, or external consumer observes them.

## Wear one hat at a time

Label the current mode before editing:

- **Refactoring hat:** Preserve behavior. Keep existing behavior tests green. Add characterization only to describe current behavior.
- **Behavior-change hat:** Change requirements, fix a bug, or add a feature. Add or update tests to express the intended new behavior.

For a mixed request:

1. Define the desired behavior change separately.
2. Refactor only enough to make the change safer or clearer.
3. Verify that the preparatory refactor preserves behavior.
4. Mark the hat switch explicitly.
5. Implement the behavior change with new acceptance evidence.
6. Refactor the resulting code again only after the new behavior is working.
7. Report the phases separately, even when they share one branch.

Do not call a combined structural and semantic rewrite “a refactor.”

## Use smells as diagnostic signals

Use a smell to start an investigation. Ask:

- Does the code make the requested change difficult, risky, or repetitive?
- Does the code combine responsibilities that change for different reasons?
- Does duplication represent the same rule, or only similar-looking syntax?
- Does indirection convey a useful concept, or merely force navigation?
- Does a long routine contain coherent units, or is it long because the algorithm is inherently sequential?
- Does a conditional encode stable variants, transient workflow, or essential ordering?
- Does data belong with the behavior that operates on it?
- Does inheritance express substitutability, or only code reuse?
- Is coupling accidental, or required by the domain or runtime?
- Will a proposed abstraction reduce current complexity, or merely relocate it?

Leave the code unchanged when the investigation does not reveal a meaningful design problem.

## Prefer the smallest sufficient change

Select the least powerful transformation that resolves the demonstrated problem.

Prefer:

- a precise rename over a new abstraction;
- an extracted variable over an extracted function when only one expression is unclear;
- an extracted function over a new class when ownership remains local;
- a moved function over a new service when an existing module already owns the data;
- a guard clause over polymorphism when nesting is the only problem;
- limited duplication over a misleading generic framework;
- a compatibility-preserving facade over an unauthorized public API break.

Sequence larger changes through enabling transformations. Keep each intermediate state valid and understandable.

## Keep a fast feedback loop

Run the cheapest check that can detect the likely mistake after each meaningful step. Expand verification as the change reaches broader boundaries.

Prefer this cadence:

1. Parse, compile, or type-check the touched unit when available.
2. Run the narrowest test or example that exercises the changed path.
3. Run nearby module or package tests after a coherent group.
4. Run broader integration, contract, build, or full-suite checks before handoff.
5. Add specialized checks for persistence, concurrency, security, compatibility, or performance when those boundaries are involved.

Use a failure as evidence about the latest step. Avoid stacking multiple uncertain transformations before checking.

## Separate refactoring from optimization

Treat an optimization goal as a separate objective even when it uses a familiar refactoring transformation.

Before optimization-driven restructuring:

1. Define the user-visible performance problem and representative workload.
2. Measure the current behavior with a profiler or benchmark.
3. Record environment, variance, warm-up, data size, and relevant resource use.
4. Make one bounded change.
5. Measure again under comparable conditions.
6. Retain the change only when the evidence supports the intended trade-off.
7. Re-run behavior checks because faster code can still be incorrect.

Do not infer performance improvement from fewer lines, fewer allocations guessed from source, a different data structure, or successful compilation.

## Avoid speculative design

Introduce an abstraction only when current evidence supports its responsibility and boundary.

Reject or defer an abstraction when it:

- exists only for an imagined future variant;
- combines code that looks similar but follows different rules;
- exposes more public surface than it removes;
- requires generic types, configuration, inheritance, factories, or dependency injection disproportionate to the problem;
- hides control flow, side effects, or data ownership;
- makes ordinary navigation harder;
- duplicates an established repository convention;
- cannot be verified independently.

Leave a clear local implementation when it is cheaper to understand and change.

## Use catalog terminology responsibly

Use the official second-edition names where available. Mention an established alias only to help repository search or user recognition.

Treat the operational notes in [refactoring-catalog.md](refactoring-catalog.md) as original safety guidance, not as a substitute for Fowler's full catalog. Follow the official page for terminology and conceptual orientation; follow repository evidence for whether and how to apply the technique.

Do not reproduce catalog examples, motivations, or step sequences verbatim.

## Primary sources

Use these primary sources:

- [Refactoring overview and definition](https://refactoring.com/)
- [Official catalog of refactorings](https://refactoring.com/catalog/)
- [Martin Fowler: Definition of Refactoring](https://martinfowler.com/bliki/DefinitionOfRefactoring.html)
- [Martin Fowler: Code Smell](https://martinfowler.com/bliki/CodeSmell.html)
- [Martin Fowler: An Example of Preparatory Refactoring — The Two Hats](https://martinfowler.com/articles/preparatory-refactoring-example.html#TheTwoHats)
- [Martin Fowler: Workflows of Refactoring](https://martinfowler.com/articles/workflowsOfRefactoring/)
- [Martin Fowler: Is Optimization Refactoring](https://martinfowler.com/bliki/IsOptimizationRefactoring.html)
- [Martin Fowler: Self-Testing Code](https://martinfowler.com/bliki/SelfTestingCode.html)
- [Martin Fowler: Unit Test — Speed](https://martinfowler.com/bliki/UnitTest.html#speed)
- [Martin Fowler: The Second Edition of Refactoring](https://martinfowler.com/articles/refactoring-2nd-ed.html)
