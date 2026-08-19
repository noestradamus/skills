# Operational Refactoring Catalog

Use this compact guide to choose and verify a transformation. Confirm language-specific mechanics with repository idioms and tools. These entries are original operational summaries, not reproductions of Fowler's catalog.

## Contents

- [Extracting and inlining](#extracting-and-inlining)
- [Naming and declarations](#naming-and-declarations)
- [Data and responsibility boundaries](#data-and-responsibility-boundaries)
- [Conditional logic](#conditional-logic)
- [Queries, modifiers, and cleanup](#queries-modifiers-and-cleanup)
- [Hierarchy and delegation](#hierarchy-and-delegation)

## Extracting and inlining

### [Extract Function](https://refactoring.com/catalog/extractFunction.html) (alias: Extract Method)

- **Signals:** A routine mixes intentions, repeats a coherent fragment, or forces readers to decode low-level steps.
- **Preconditions:** Identify inputs, outputs, mutations, exception paths, receiver/closure binding, and non-local control flow such as `await`, `yield`, `break`, `continue`, deferred cleanup, transactions, and resource lifetime.
- **Preserve:** Results, mutation and I/O order, exception type/timing, evaluation count, and visibility.
- **Failure modes:** Reordering side effects, changing closure or receiver binding, broad parameter lists, or extraction that only moves confusion.
- **Verify:** Exercise normal, boundary, exceptional, and side-effect-order cases; run type/build checks for signature mistakes.

### [Inline Function](https://refactoring.com/catalog/inlineFunction.html) (alias: Inline Method)

- **Signals:** A function adds indirection without a meaningful name or hides a flow that is clearer at the call site.
- **Preconditions:** Find every caller and confirm overriding, dispatch, recursion, callback identity, or public use is absent or preserved.
- **Preserve:** Evaluation order, receiver binding, return/control flow, and callable identity when observable.
- **Failure modes:** Duplicating complex logic, changing early returns, breaking overrides, or removing an externally used symbol.
- **Verify:** Test all callers and dispatch variants; search again for references before removal.

### [Extract Variable](https://refactoring.com/catalog/extractVariable.html)

- **Signals:** A dense expression repeats or obscures an intermediate concept.
- **Preconditions:** Confirm the expression is safe to evaluate at the chosen point and exactly as often as before.
- **Preserve:** Value, type, evaluation count, lazy behavior, exceptions, and side-effect order.
- **Failure modes:** Hoisting across a mutation, eagerly evaluating a lazy branch, or caching a time-varying value.
- **Verify:** Cover branch, null/empty, exception, and side-effect cases; inspect the diff for moved evaluation.

## Naming and declarations

### [Rename Variable](https://refactoring.com/catalog/renameVariable.html)

- **Signals:** A local or parameter name misstates purpose or hides a domain concept.
- **Preconditions:** Resolve lexical scope, shadowing, capture, destructuring, templates, macros, and string-based lookup.
- **Preserve:** Binding, scope, value, evaluation, and externally serialized names.
- **Failure modes:** Text-only replacement, new shadowing, missed generated/template use, or wire-name changes.
- **Verify:** Prefer semantic rename support; search old/new names and run focused type, build, and caller checks.

### [Rename Field](https://refactoring.com/catalog/renameField.html)

- **Signals:** A stored member's name misstates ownership, units, lifecycle, or meaning.
- **Preconditions:** Find reflection, serialization, persistence, dependency injection, templates, and public access.
- **Preserve:** Storage/wire names, visibility, defaults, aliasing, compatibility, and field identity where observable.
- **Failure modes:** Schema drift, missed dynamic references, duplicate fields, or unauthorized public renaming.
- **Verify:** Run construction, caller, serialization, persistence, reflection, and compatibility checks.

### [Change Function Declaration](https://refactoring.com/catalog/changeFunctionDeclaration.html) (aliases include Rename Function and Rename Method)

- **Signals:** A function name or parameter list obscures its contract, includes consistently unused data, or orders concepts poorly.
- **Preconditions:** Inventory callers, overrides, interfaces, callbacks, reflection, binary consumers, and default-argument semantics.
- **Preserve:** Public contract unless authorized, argument evaluation order, defaults, dispatch, and compatibility.
- **Failure modes:** Missed callers, ambiguous overloads, changed defaults, callback mismatch, or unauthorized API breakage.
- **Verify:** Compile/type-check implementations and callers; test defaults, overload/dispatch paths, dynamic references, and shims.

## Data and responsibility boundaries

### [Encapsulate Variable](https://refactoring.com/catalog/encapsulateVariable.html)

- **Signals:** Direct access prevents controlled mutation, tracing, or later representation changes.
- **Preconditions:** Locate every read/write and determine whether identity, aliasing, mutation timing, or concurrency is observable.
- **Preserve:** Stored values, access timing, aliasing, thread-safety, initialization, and external names.
- **Failure modes:** Returning copies instead of references, adding validation, changing lock boundaries, or triggering initialization early.
- **Verify:** Test read/write paths, identity-sensitive behavior, initialization, serialization, and concurrent access where relevant.

### [Move Function](https://refactoring.com/catalog/moveFunction.html) (alias: Move Method)

- **Signals:** A function depends more on another module's data or belongs with the responsibility it serves.
- **Preconditions:** Map callers, visibility, cyclic-dependency risk, receiver context, extension hooks, and packaging rules.
- **Preserve:** Callable contract, dispatch, side effects, dependency direction, and compatibility.
- **Failure modes:** New cycles, changed receiver binding, duplicated old/new logic, or broken imports and mocks.
- **Verify:** Run caller and module-boundary tests; inspect dependency direction; retain and test a shim when needed.

### [Move Field](https://refactoring.com/catalog/moveField.html)

- **Signals:** A field is read or changed primarily by another responsibility or makes data travel awkwardly.
- **Preconditions:** Trace construction, ownership, aliases, persistence mapping, serialization, equality, copying, and concurrency.
- **Preserve:** Value lifecycle, identity, defaults, storage/wire format, mutation timing, and access compatibility.
- **Failure modes:** Split sources of truth, stale caches, changed construction order, schema drift, or locking changes.
- **Verify:** Test construction, mutation, copy/equality, persistence round trips, serialization, and concurrency as applicable.

### [Extract Class](https://refactoring.com/catalog/extractClass.html)

- **Signals:** One class has distinct reasons to change or a cohesive subset of fields/functions with another responsibility.
- **Preconditions:** Identify ownership, lifecycle, invariants, public surface, and a safe delegation boundary.
- **Preserve:** Original API, lifecycle, identity, side effects, serialization, and collaboration order.
- **Failure modes:** Creating a data bag, bidirectional coupling, leaking the new class, or changing initialization and persistence.
- **Verify:** Test through the original facade first, then focused collaborator tests; inspect dependency direction.

### [Inline Class](https://refactoring.com/catalog/inlineClass.html)

- **Signals:** A class no longer carries enough responsibility to justify its indirection.
- **Preconditions:** Confirm it has no independent lifecycle, subtype role, public consumers, serialization identity, or framework registration.
- **Preserve:** Existing facade/API, construction, identity when observable, and behavior order.
- **Failure modes:** Bloated destination, missed dynamic construction, broken dependency injection, or lost extension seam.
- **Verify:** Search construction/registration sites; test former clients and serialization or injection boundaries.

### [Introduce Parameter Object](https://refactoring.com/catalog/introduceParameterObject.html)

- **Signals:** The same related values travel together through several declarations or embody a shared concept.
- **Preconditions:** Establish value semantics, optional/default behavior, call-site compatibility, and serialization impact.
- **Preserve:** Accepted values, defaults, argument evaluation, public signatures unless authorized, and wire formats.
- **Failure modes:** Creating a miscellaneous bag, moving behavior prematurely, or breaking callers and serializers.
- **Verify:** Test old and migrated call paths, defaults, equality/value behavior, and serialization; use a shim when required.

### [Replace Primitive with Object](https://refactoring.com/catalog/replacePrimitiveWithObject.html)

- **Signals:** A primitive carries domain rules, formatting, parsing, units, or repeated validation.
- **Preconditions:** Define conversion, equality, ordering, nullability, storage, serialization, and interoperability boundaries.
- **Preserve:** Accepted inputs, representation at external boundaries, comparisons, errors, and round trips.
- **Failure modes:** Stricter validation, changed equality/hash behavior, unit errors, or a leaked wire-shape change.
- **Verify:** Use boundary/property tests for conversion and equality; test persistence and serialization round trips.

## Conditional logic

### [Replace Conditional with Polymorphism](https://refactoring.com/catalog/replaceConditionalWithPolymorphism.html)

- **Signals:** Behavior repeatedly branches on a stable variant and each variant has cohesive rules.
- **Preconditions:** Confirm variants and dispatch are stable enough, construction is controllable, and abstraction pays for itself.
- **Preserve:** Branch selection, fallbacks, side-effect order, exceptions, and result types.
- **Failure modes:** Speculative hierarchy, lost default case, changed dispatch precedence, or scattered construction logic.
- **Verify:** Run a case matrix for every variant, default, boundary, and error; compare results and ordered effects.

### [Replace Nested Conditional with Guard Clauses](https://refactoring.com/catalog/replaceNestedConditionalWithGuardClauses.html)

- **Signals:** Deep nesting obscures exceptional, invalid, or early-exit cases.
- **Preconditions:** Map predicate order, short-circuiting, mutations, cleanup/finally behavior, and return paths.
- **Preserve:** Predicate evaluation count/order, returned values, exceptions, and mandatory cleanup.
- **Failure modes:** Reordered side effects, skipped cleanup, eager evaluation, or altered fall-through.
- **Verify:** Use branch/path tests with effect tracing; include cleanup and exception cases.

### [Decompose Conditional](https://refactoring.com/catalog/decomposeConditional.html)

- **Signals:** A condition or branch body hides a domain decision behind dense mechanics.
- **Preconditions:** Identify captured state and whether extraction changes when or how often expressions run.
- **Preserve:** Boolean result, short-circuit behavior, branch effects, exceptions, and evaluation order.
- **Failure modes:** Extracted predicates mutate state, capture stale data, or evaluate previously skipped expressions.
- **Verify:** Test truth-table cases, short-circuit sentinels, side effects, and exceptions.

### [Consolidate Conditional Expression](https://refactoring.com/catalog/consolidateConditionalExpression.html)

- **Signals:** Several checks lead to the same outcome and together express one decision.
- **Preconditions:** Prove outcomes and intervening effects are equivalent; preserve short-circuit semantics.
- **Preserve:** Which checks execute, their order, the shared outcome, exceptions, and side effects.
- **Failure modes:** Combining superficially similar branches with different effects or changing eager/lazy evaluation.
- **Verify:** Build a truth table and effect log for each predicate combination and exceptional path.

## Queries, modifiers, and cleanup

### [Separate Query from Modifier](https://refactoring.com/catalog/separateQueryFromModifier.html)

- **Signals:** A call both returns information and changes state, surprising callers or preventing safe reuse.
- **Preconditions:** Find callers relying on combined timing, atomicity, locking, I/O, or exactly-once behavior.
- **Preserve:** Returned value, mutation count/order, transactional boundary, and concurrency semantics.
- **Failure modes:** Duplicate work, race windows, lost atomicity, or callers invoking only half of the protocol.
- **Verify:** Test state before/after, call counts, failure/rollback, transactions, and concurrent interleavings where relevant.

### [Replace Temp with Query](https://refactoring.com/catalog/replaceTempWithQuery.html)

- **Signals:** A temporary blocks extraction or duplicates a derivation with a clear conceptual name.
- **Preconditions:** Prove recomputation is pure, stable, inexpensive enough, and not identity- or time-sensitive.
- **Preserve:** Value, evaluation count when observable, performance constraints, exceptions, and identity.
- **Failure modes:** Recomputing I/O or expensive work, reading changed state, or returning new identities.
- **Verify:** Test result equivalence and call counts; benchmark material cost; retain the temporary when purity or cost is uncertain.

### [Remove Dead Code](https://refactoring.com/catalog/removeDeadCode.html)

- **Signals:** Static and repository evidence show a declaration, branch, or compatibility path is unreachable or unused.
- **Preconditions:** Check reflection, dynamic loading, configuration, flags, plugins, external consumers, migrations, and rollback paths.
- **Preserve:** Build/package contents, public compatibility, runtime discovery, load-time effects, and operational rollback.
- **Failure modes:** Removing dynamically referenced or dormant compatibility code, registration effects, or generated callers.
- **Verify:** Search code/config/docs, run build/package checks, exercise discovery, and review public exports.

## Hierarchy and delegation

### [Pull Up Field](https://refactoring.com/catalog/pullUpField.html)

- **Signals:** Sibling types duplicate a field that represents the same state in their common contract.
- **Preconditions:** Prove type, semantics, visibility, initialization, persistence, and invariants match.
- **Preserve:** State value, layout when contractual, construction order, visibility, and serialization.
- **Failure modes:** Merging coincidentally named state, hiding initialization differences, or changing schema/layout.
- **Verify:** Test every subtype's construction, mutation, serialization, and compatibility boundaries.

### [Pull Up Method](https://refactoring.com/catalog/pullUpMethod.html)

- **Signals:** Sibling types implement genuinely identical behavior that belongs in the parent contract.
- **Preconditions:** Prove semantics, dependencies, visibility, dispatch, and subtype preconditions match.
- **Preserve:** Dispatch results, receiver semantics, exceptions, and subtype-specific behavior.
- **Failure modes:** Pulling up merely similar logic, introducing type checks, or changing override precedence.
- **Verify:** Run contract tests for every subtype and explicit dispatch/override tests.

### [Push Down Field](https://refactoring.com/catalog/pushDownField.html)

- **Signals:** Parent state is meaningful only to a subset of subtypes and burdens the general contract.
- **Preconditions:** Find all field users, reflective access, serialization, and parent-typed assumptions.
- **Preserve:** State behavior for applicable subtypes and authorized compatibility surfaces.
- **Failure modes:** Breaking persistence, reflection, siblings, parent construction, or binary/layout compatibility.
- **Verify:** Test each subtype, construction, persistence/serialization, and parent-polymorphic clients.

### [Push Down Method](https://refactoring.com/catalog/pushDownMethod.html)

- **Signals:** Parent behavior is valid only for a subset of subtypes or exposes an inappropriate responsibility.
- **Preconditions:** Find all calls through parent types, overrides, interface promises, reflection, and framework hooks.
- **Preserve:** Behavior for applicable subtypes and any authorized common contract.
- **Failure modes:** Violating substitutability, breaking parent-typed callers, or duplicating divergent implementations.
- **Verify:** Compile/type-check clients; run subtype contracts, dispatch tests, and framework integration checks.

### [Replace Superclass with Delegate](https://refactoring.com/catalog/replaceSuperclassWithDelegate.html)

- **Signals:** Inheritance exposes unwanted parent behavior, violates substitutability, or exists mainly for reuse.
- **Preconditions:** Map public/protected surfaces, override rules, identity, lifecycle, construction, framework requirements, and compatibility.
- **Preserve:** Public behavior, dispatch results, identity, lifecycle, exceptions, and framework integration.
- **Failure modes:** Forwarding gaps, changed self/receiver semantics, recursion, equality differences, or broken hooks.
- **Verify:** Use contract, dispatch, identity/equality, construction, and framework integration tests.

### [Replace Subclass with Delegate](https://refactoring.com/catalog/replaceSubclassWithDelegate.html)

- **Signals:** Subclass variation is only one dimension, changes dynamically, or conflicts with another inheritance need.
- **Preconditions:** Map variant construction, dispatch, shared state, identity, factories, and all subtype consumers.
- **Preserve:** Variant selection, public behavior, state sharing, identity, and lifecycle.
- **Failure modes:** Split state, forwarding omissions, changed factory behavior, or an exposed internal delegate.
- **Verify:** Run every variant's contract, factory, state, identity, and integration tests.

### [Replace Delegation with Inheritance](https://refactoring.com/catalog/replaceDelegationWithInheritance.html) — legacy catalog technique

- **Signals:** A delegate is the stable substitutable identity, forwarding dominates the host, and a true is-a relationship is demonstrated.
- **Preconditions:** Confirm single-inheritance constraints, substitutability, lifecycle, visibility, identity, framework rules, and long-term stability.
- **Preserve:** Forwarded behavior, override results, identity/equality, construction, exceptions, and compatibility.
- **Failure modes:** Reuse-only inheritance, fragile coupling, name conflicts, lost composition flexibility, or speculative hierarchy.
- **Verify:** Run contract tests for both roles, dispatch/override, identity/equality, construction, and framework integration.
- **Attribution note:** This page remains on the official site but is not listed as a current second-edition catalog card. Identify it as legacy; otherwise describe the reverse move as an additional design adjustment.
