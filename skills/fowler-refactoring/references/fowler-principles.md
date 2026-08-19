# Fowler Principles and Attribution

Use this reference to ground decisions and keep attribution precise. Paraphrase the sources; do not copy catalog prose or mechanics into output.

## Fowler-derived foundation

1. **Preserve observable behavior.** Treat refactoring as changing internal structure to make code easier to understand and modify without changing what observers can detect. Fowler deliberately leaves the exact boundary informal, so define the contract-relevant observables for the repository.
2. **Compose small transformations.** Keep the program working while a sequence of individually small refactorings produces a larger design improvement.
3. **Verify continuously.** Work from a stable, tested state and run tests after small changes so a regression points to a narrow step.
4. **Keep the two hats separate.** Distinguish refactoring from adding function. Switch as often as needed, but do not mix both intentions in one change. Fowler credits the metaphor to Kent Beck.
5. **Investigate smells.** Use a smell as an inexpensive signal of a possible deeper design problem. Inspect context before deciding that change is warranted; a smell is not proof of a defect. Fowler credits the term to Kent Beck.
6. **Refactor for an economic reason.** Improve structure when it reduces the cost of understanding or a likely change. Do not chase abstract cleanliness detached from use.
7. **Improve gradually.** Leave touched code clearer without trying to perfect an entire codebase in one pass or disappearing into a cleanup excursion.
8. **Keep optimization distinct.** Similar code transformations may support optimization, but optimization intentionally changes performance. Profile before and after it rather than presenting it as behavior-preserving refactoring.
9. **Protect published interfaces.** Changing all reachable callers can be part of a refactoring, but a published interface is observable and may have consumers that cannot be updated together.
10. **Apply concepts across languages.** Adapt the transformations to the language and project rather than copying the JavaScript form of the second-edition examples.

## Additional autonomous-agent safeguards

The following requirements extend Fowler's foundation for safe repository operation. Do not attribute them specifically to Fowler unless a primary source is added:

- Inspect local agent instructions, repository status, and unrelated modifications before editing.
- Record exact baseline commands and distinguish pre-existing failures.
- Gate public APIs, schemas, serialized formats, protocols, security boundaries, concurrency semantics, and contractual timing behind explicit user authorization.
- Use characterization tests when current legacy behavior lacks focused coverage.
- Exclude generated, vendored, migration, snapshot, and third-party code by default.
- Require representative measurement before optimization-driven restructuring.
- Preserve toolchain, dependency, configuration, and lockfile state unless a change is necessary and authorized.
- Stop when behavior-preservation evidence is unavailable; report residual risk instead of overstating confidence.
- Preserve suspected bugs during structural work and escalate security, privacy, corruption, or data-loss concerns separately.
- Capture the relevant pre-edit diff and keep characterization tests within the user's authorized file scope.
- Reject speculative abstraction unless a demonstrated present need justifies its cost.

## Primary sources

- [Refactoring.com: definition, small transformations, language applicability, and official catalog](https://refactoring.com/)
- [Definition of Refactoring: noun and verb definitions](https://martinfowler.com/bliki/DefinitionOfRefactoring.html)
- [Refactoring Boundary: the deliberately informal observable-behavior boundary](https://martinfowler.com/bliki/RefactoringBoundary.html)
- [Catalog of Refactorings: current names, aliases, and categories](https://refactoring.com/catalog/)
- [Code Smell: smells as surface indications that require deeper judgment](https://martinfowler.com/bliki/CodeSmell.html)
- [Workflows of Refactoring: the two hats, stable tests, gradual improvement, and economic motivation](https://martinfowler.com/articles/workflowsOfRefactoring/)
- [Is Changing Interfaces Refactoring?: caller updates and behavior preservation](https://martinfowler.com/bliki/IsChangingInterfacesRefactoring.html)
- [Published Interface: why external consumers require greater care](https://martinfowler.com/bliki/PublishedInterface.html)
- [Is Optimization Refactoring?: profile before and after optimization](https://martinfowler.com/bliki/IsOptimizationRefactoring.html)
- [Opportunistic Refactoring: small improvements and avoiding rabbit holes](https://martinfowler.com/bliki/OpportunisticRefactoring.html)
- [Yagni: avoiding complexity for presumptive future needs](https://martinfowler.com/bliki/Yagni.html)
- [Refactoring Malapropism: refactoring versus general restructuring](https://martinfowler.com/bliki/RefactoringMalapropism.html)
- [Refactoring book page: controlled, small, behavior-preserving transformations](https://martinfowler.com/books/refactoring.html)

## Attribution rules

- Say “Fowler defines,” “Fowler describes,” or “Fowler's catalog names” only when a linked primary source supports the claim.
- Credit the two-hats metaphor and the term code smell to Kent Beck when naming their origins; say Fowler documents and uses them.
- Credit YAGNI to Extreme Programming and, when discussing the phrase's origin, to Kent Beck and Chet Hendrickson; Fowler documents the principle.
- Use current second-edition catalog names where possible and mention older names only as aliases.
- Label repository safety, compatibility, characterization, benchmarking, and authorization rules as agent safeguards or modern adaptations.
- Describe rollback boundaries as an agent safeguard; Fowler supports small steps, but “reversible” is not a catalog promise.
- Prefer original operational summaries. Link to the catalog instead of reproducing its entries.
