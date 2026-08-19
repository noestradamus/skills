# Operational Refactoring Catalog

Use this reference as a compact decision aid. Read only the entries relevant to the diagnosed problem. Follow the linked official catalog page for the technique's canonical name and conceptual orientation.

Keep every application behavior-preserving. Treat the signals below as reasons to investigate, not automatic instructions to refactor. The operational safeguards and verification notes are original guidance for autonomous agents and do not reproduce Fowler's catalog mechanics.

## Contents

- [Functions and expressions](#functions-and-expressions)
  - [Extract Function](#extract-function)
  - [Inline Function](#inline-function)
  - [Extract Variable](#extract-variable)
  - [Rename Variable, Field, or Function](#rename-variable-field-or-function)
  - [Change Function Declaration](#change-function-declaration)
- [Data and responsibilities](#data-and-responsibilities)
  - [Encapsulate Variable](#encapsulate-variable)
  - [Move Function or Field](#move-function-or-field)
  - [Extract Class](#extract-class)
  - [Inline Class](#inline-class)
  - [Introduce Parameter Object](#introduce-parameter-object)
  - [Replace Primitive with Object](#replace-primitive-with-object)
- [Conditional logic](#conditional-logic)
  - [Decompose Conditional](#decompose-conditional)
  - [Consolidate Conditional Expression](#consolidate-conditional-expression)
  - [Replace Nested Conditional with Guard Clauses](#replace-nested-conditional-with-guard-clauses)
  - [Replace Conditional with Polymorphism](#replace-conditional-with-polymorphism)
- [Queries and derived values](#queries-and-derived-values)
  - [Separate Query from Modifier](#separate-query-from-modifier)
  - [Replace Temp with Query](#replace-temp-with-query)
- [Removal and hierarchies](#removal-and-hierarchies)
  - [Remove Dead Code](#remove-dead-code)
  - [Pull Up Members](#pull-up-members)
  - [Push Down Members](#push-down-members)
  - [Replace Superclass with Delegate](#replace-superclass-with-delegate)
  - [Replace Subclass with Delegate](#replace-subclass-with-delegate)
  - [Consider inheritance in place of delegation](#consider-inheritance-in-place-of-delegation)
- [Selection rules](#selection-rules)

## Functions and expressions

### Extract Function

Official catalog: [Extract Function](https://refactoring.com/catalog/extractFunction.html)

- **Use when:** Identify a coherent fragment with a nameable purpose, mixed abstraction levels, repeated explanation comments, or logic that must be reused or tested through a clearer seam.
- **Require:** Map every input, output, mutation, early exit, exception, async boundary, resource, transaction, and captured variable. Confirm that extraction improves understanding rather than creating parameter plumbing.
- **Preserve:** Keep evaluation order, execution count, mutation timing, return or yield behavior, thrown errors, cleanup, short-circuiting, and async scheduling unchanged.
- **Avoid:** Do not extract across hidden control flow, turn one readable algorithm into many tiny navigation hops, capture mutable state accidentally, or introduce a public helper without need.
- **Verify:** Run focused tests for normal, boundary, and exceptional paths. Check side-effect order and call count when relevant. Compile or type-check every changed caller.

### Inline Function

Official catalog: [Inline Function](https://refactoring.com/catalog/inlineFunction.html)

- **Use when:** Remove an indirection that adds no useful name, policy, reuse, override point, or test seam, or undo an extraction that made the flow harder to follow.
- **Require:** Prove that the function is not an external API, override, callback, registration target, reflection target, monkey-patch seam, instrumentation point, or independently meaningful concept.
- **Preserve:** Keep argument evaluation, defaults, dispatch, exceptions, side effects, and single-versus-repeated evaluation unchanged.
- **Avoid:** Do not duplicate a complex expression at many call sites, inline an expensive or stateful operation more than once, or erase a stable architectural boundary.
- **Verify:** Find all callers and dynamic references. Run caller-focused tests and static checks. Compare generated or runtime registrations when the framework discovers functions indirectly.

### Extract Variable

Official catalog: [Extract Variable](https://refactoring.com/catalog/extractVariable.html)

- **Use when:** Name a complex expression, expose units or intent, separate sub-calculations, or make a conditional easier to inspect.
- **Require:** Determine whether the expression is pure and stable. Keep the declaration at the same effective evaluation point when the expression can throw, mutate, read time, read random state, perform I/O, or observe changing data.
- **Preserve:** Keep evaluation count, timing, precision, null behavior, short-circuiting, and exceptions unchanged.
- **Avoid:** Do not hoist work into paths that previously skipped it, cache a value that previously changed between uses, or add a vague name that obscures the underlying rule.
- **Verify:** Exercise every branch that controls evaluation. Check numeric boundaries, null cases, and side-effect counts. Use the type checker to catch scope or inference changes.

### Rename Variable, Field, or Function

Official catalog: [Rename Variable](https://refactoring.com/catalog/renameVariable.html), [Rename Field](https://refactoring.com/catalog/renameField.html), and [Change Function Declaration](https://refactoring.com/catalog/changeFunctionDeclaration.html)

- **Use when:** Replace a misleading, ambiguous, outdated, unitless, or responsibility-obscuring name with one that communicates current intent.
- **Require:** Search declarations and all static and dynamic uses, including reflection, serialization, ORM mappings, templates, configuration, dependency injection, plugin registries, command names, metrics, logs, and external documentation.
- **Preserve:** Keep exported names, wire names, persisted fields, command surfaces, and compatibility aliases unchanged unless the user explicitly authorizes a contract migration.
- **Avoid:** Do not perform broad vocabulary churn, rename unrelated symbols for consistency, create collisions, or silently change externally observed identifiers.
- **Verify:** Run repository-wide symbol search after the rename, then compile, type-check, and test. Add contract or serialization checks when the old name crosses a boundary.

### Change Function Declaration

Official catalog: [Change Function Declaration](https://refactoring.com/catalog/changeFunctionDeclaration.html)

- **Use when:** Improve a function name, parameter list, defaults, or calling convention so the declaration better expresses its responsibility.
- **Require:** Identify every caller, override, interface implementation, callback registration, foreign-function boundary, overload, default, keyword argument, variadic use, decorator, and external consumer.
- **Preserve:** Keep accepted calls, argument evaluation order, default semantics, return values, errors, source compatibility, and binary compatibility within the authorized contract.
- **Avoid:** Do not change a public signature without authorization. Do not combine renaming, parameter reordering, default changes, and behavior changes in one opaque step.
- **Verify:** Change one declaration aspect at a time. Compile or type-check all callers, run interface and contract tests, and retain a compatibility shim only when explicitly required.

## Data and responsibilities

### Encapsulate Variable

Official catalog: [Encapsulate Variable](https://refactoring.com/catalog/encapsulateVariable.html)

- **Use when:** Centralize access to shared or mutable state so later changes can control validation, copying, synchronization, or observation.
- **Require:** Find every read and write, including framework injection, reflection, direct field access, tests, serialization, and concurrent access. Decide whether callers currently receive a shared reference or a copy.
- **Preserve:** Keep value, identity, mutability, aliasing, write timing, visibility across threads, and error behavior unchanged.
- **Avoid:** Do not accidentally return a copy, add validation, change synchronization, hide required mutation, or create recursive accessors.
- **Verify:** Test reads, writes, identity-sensitive behavior, and invalid states already accepted. Use race or concurrency checks when access crosses threads or tasks.

### Move Function or Field

Official catalog: [Move Function](https://refactoring.com/catalog/moveFunction.html) and [Move Field](https://refactoring.com/catalog/moveField.html)

- **Use when:** Place behavior with the data it uses most, clarify ownership, reduce cross-module knowledge, or restore the repository's intended dependency direction.
- **Require:** Map dependencies, visibility, lifecycle, initialization order, ownership, serialization, persistence mapping, subclass access, and runtime registration. Confirm the target is the natural owner.
- **Preserve:** Keep call paths, public facades, state identity, initialization, side effects, exceptions, and persisted or serialized representation unchanged.
- **Avoid:** Do not create import cycles, widen visibility, duplicate state, move behavior across a process or trust boundary, or introduce a generic service merely to host moved code.
- **Verify:** Run import or dependency checks, startup and initialization tests, focused behavior tests, and serialization or persistence tests when fields move.

### Extract Class

Official catalog: [Extract Class](https://refactoring.com/catalog/extractClass.html)

- **Use when:** Separate a cohesive responsibility that has its own data, invariants, collaborators, or reason to change from an overloaded class or module.
- **Require:** Identify a stable responsibility boundary and decide ownership, lifecycle, construction, visibility, and mutation flow. Confirm that a smaller extraction would not solve the problem.
- **Preserve:** Keep the original public facade, object identity where observable, equality, state synchronization, construction order, serialization, persistence, and side effects unchanged.
- **Avoid:** Do not create an anemic wrapper, circular dependency, duplicate state, pass-through class, or fragment that forces readers to bounce between files without gaining a concept.
- **Verify:** Exercise behavior through the original public surface, test state transitions and identity, and run persistence or serialization round trips when the original type crossed those boundaries.

### Inline Class

Official catalog: [Inline Class](https://refactoring.com/catalog/inlineClass.html)

- **Use when:** Remove a class or module that no longer owns a meaningful responsibility and is used almost entirely by one owner.
- **Require:** Prove that no external caller, serializer, ORM, reflection path, dependency-injection registration, plugin, or extension point depends on the separate type.
- **Preserve:** Keep lifecycle, identity, equality, construction, public behavior, and serialized or persisted representation unchanged.
- **Avoid:** Do not erase a useful boundary merely to reduce file count, overload the receiving class, or remove an intentional test seam.
- **Verify:** Search for static and dynamic uses, run construction and lifecycle tests, and verify framework registrations and serialized type information.

### Introduce Parameter Object

Official catalog: [Introduce Parameter Object](https://refactoring.com/catalog/introduceParameterObject.html)

- **Use when:** Group values that repeatedly travel together and represent one coherent concept, range, context, coordinate, or request.
- **Require:** Confirm that the group is stable across call sites. Define ownership, mutability, defaults, validation, units, equality, and serialization before introducing the type.
- **Preserve:** Keep accepted values, null handling, defaults, parameter evaluation order, units, mutation semantics, and public compatibility unchanged.
- **Avoid:** Do not create a grab-bag context object, force unrelated parameters together, add stricter validation, or break callers merely to shorten a signature.
- **Verify:** Test every migrated caller, boundary and default values, mutation or aliasing, and serialization round trips. Keep a compatibility overload only when authorized.

### Replace Primitive with Object

Official catalog: [Replace Primitive with Object](https://refactoring.com/catalog/replacePrimitiveWithObject.html)

- **Use when:** Give a primitive value explicit units, formatting, validation, comparison, or domain behavior that is repeated or easy to misuse.
- **Require:** Define value semantics, accepted inputs, normalization, equality, ordering, nullability, conversion, serialization, persistence, and allocation cost.
- **Preserve:** Keep the current accepted value set, formatting, comparison, hashing, precision, ordering, null behavior, wire form, and persisted form unless separately authorized.
- **Avoid:** Do not introduce stricter validation as a hidden bug fix, change JSON shape, alter equality, add surprising implicit conversions, or allocate heavily on a hot path without measurement.
- **Verify:** Test boundary values, equality and hashing, conversions, formatting, serialization, persistence, and representative performance when the value is created frequently.

## Conditional logic

### Decompose Conditional

Official catalog: [Decompose Conditional](https://refactoring.com/catalog/decomposeConditional.html)

- **Use when:** Name a complex condition or branch so readers can understand the decision and outcomes without decoding low-level expressions.
- **Require:** Map short-circuit behavior, evaluation order, side effects, exceptions, mutable reads, and branch-local scope before extracting predicates or branch functions.
- **Preserve:** Keep branch selection, predicate evaluation count and order, side effects, exceptions, and result values unchanged.
- **Avoid:** Do not evaluate predicates eagerly, move work outside its original branch, conceal important sequencing, or extract names that merely restate syntax.
- **Verify:** Build a truth table for meaningful input combinations. Assert branch result, predicate call order, and side-effect count where subtle.

### Consolidate Conditional Expression

Official catalog: [Consolidate Conditional Expression](https://refactoring.com/catalog/consolidateConditionalExpression.html)

- **Use when:** Combine separate checks that produce the same outcome and represent one conceptual decision.
- **Require:** Confirm that the conditions truly share one outcome and do not carry distinct logging, metrics, errors, mutation, or diagnostic meaning.
- **Preserve:** Keep short-circuit order, evaluation count, exceptions, side effects, and the exact outcome for every combination.
- **Avoid:** Do not merge conditions that only look similar, erase distinct business reasons, or reorder stateful predicates.
- **Verify:** Test the truth table, especially cases where multiple conditions are true. Instrument predicate order or call count when effects exist.

### Replace Nested Conditional with Guard Clauses

Official catalog: [Replace Nested Conditional with Guard Clauses](https://refactoring.com/catalog/replaceNestedConditionalWithGuardClauses.html)

- **Use when:** Expose exceptional, invalid, or early-exit cases and leave the primary path less deeply nested.
- **Require:** Identify cleanup, `finally` or defer behavior, transactions, locks, resource lifetime, post-condition code, and mutations shared by all exits.
- **Preserve:** Keep exit order, return or throw values, cleanup, logging, mutation, transaction outcome, and resource release unchanged.
- **Avoid:** Do not bypass shared cleanup, move an exit before a required side effect, duplicate finalization, or turn a deliberately staged workflow into scattered returns.
- **Verify:** Exercise every exit and the main path. Assert cleanup, transaction, lock, and side-effect behavior for each route.

### Replace Conditional with Polymorphism

Official catalog: [Replace Conditional with Polymorphism](https://refactoring.com/catalog/replaceConditionalWithPolymorphism.html)

- **Use when:** Replace repeated behavior-switching on a stable variant or type with dispatch owned by those variants.
- **Require:** Confirm a stable variation axis, meaningful type boundary, controlled creation or lookup, and enough repeated branching to justify added types.
- **Preserve:** Keep behavior for every variant, default or unknown cases, construction, serialization, errors, side effects, ordering, and public type contracts unchanged.
- **Avoid:** Do not create a class explosion for one simple conditional, hide conditions in factories, force transient workflow states into inheritance, or change external type codes.
- **Verify:** Run contract tests for every variant and the fallback path. Test factories, deserialization, registration, and integration points that select the implementation.

## Queries and derived values

### Separate Query from Modifier

Official catalog: [Separate Query from Modifier](https://refactoring.com/catalog/separateQueryFromModifier.html)

- **Use when:** Split a function that both returns information and changes state so callers can reason about observation and mutation separately.
- **Require:** Identify which result depends on the mutation, how many times callers invoke the function, and whether separating calls introduces a race or inconsistent intermediate state.
- **Preserve:** Keep the returned value, mutation timing, mutation count, errors, atomicity, and ordering as observed by every caller.
- **Avoid:** Do not leave hidden mutation in the query, call the modifier twice, omit it at a caller, or split an operation whose atomicity is part of the contract.
- **Verify:** Assert state before and after, result values, invocation counts, and caller order. Add concurrency or transaction tests when separation creates a time window.

### Replace Temp with Query

Official catalog: [Replace Temp with Query](https://refactoring.com/catalog/replaceTempWithQuery.html)

- **Use when:** Replace a local derived value with a function or property that clarifies meaning and enables extraction or movement.
- **Require:** Prove that recomputation is pure and stable, or preserve a single computed value internally. Measure cost when the expression is nontrivial or hot.
- **Preserve:** Keep the value at each use, evaluation count when observable, exceptions, side effects, precision, and performance constraints.
- **Avoid:** Do not recompute changing state, repeat I/O, random, time, allocation, or expensive work, or turn a transparent local into hidden global access.
- **Verify:** Test repeated uses under mutable state, exceptions, and boundary inputs. Benchmark before and after when recomputation may matter.

## Removal and hierarchies

### Remove Dead Code

Official catalog: [Remove Dead Code](https://refactoring.com/catalog/removeDeadCode.html)

- **Use when:** Remove code proven unreachable, unused, obsolete, or replaced within the agreed compatibility window.
- **Require:** Check static references, reflection, dynamic imports, framework conventions, registration, dependency injection, templates, feature flags, build tags, plugins, scripts, serialization, external callers, documentation, and generated sources.
- **Preserve:** Keep every reachable behavior, supported entry point, compatibility path, migration path, configuration option, and externally referenced name unchanged.
- **Avoid:** Do not rely on one text search, delete code merely because tests miss it, remove disabled recovery paths, or edit generated or vendored output instead of its source.
- **Verify:** Run reference and registry searches, package or application builds, tests that cover startup and optional paths, and API or artifact inspection. Defer removal when dynamic use cannot be excluded.

### Pull Up Members

Official catalog: [Pull Up Method](https://refactoring.com/catalog/pullUpMethod.html) and [Pull Up Field](https://refactoring.com/catalog/pullUpField.html)

- **Use when:** Move genuinely identical or equivalent behavior or state from sibling subtypes to the shared superclass that owns the common contract.
- **Require:** Confirm semantic equivalence, compatible dependencies, initialization, visibility, generic types, annotations, serialization, and override behavior across all subtypes.
- **Preserve:** Keep dynamic dispatch, subtype results, initialization order, field layout where observable, annotations, and serialized or persisted representation unchanged.
- **Avoid:** Do not force subtly different rules into one base implementation, widen public or protected surface, or create conditionals in the superclass to recover subtype differences.
- **Verify:** Run the base contract against every subtype, plus construction, override, serialization, and persistence tests.

### Push Down Members

Official catalog: [Push Down Method](https://refactoring.com/catalog/pushDownMethod.html) and [Push Down Field](https://refactoring.com/catalog/pushDownField.html)

- **Use when:** Move behavior or state used only by a subset of subtypes out of an overly broad superclass.
- **Require:** Prove that base-typed callers, reflection, serialization, dependency injection, generated code, and other subtypes do not require the member.
- **Preserve:** Keep behavior for owning subtypes, base contracts, dispatch, initialization, and external compatibility unchanged.
- **Avoid:** Do not break substitutability, remove a public base member without authorization, duplicate divergent copies, or expose subtype details to callers.
- **Verify:** Test every subtype and base-typed use, compile all consumers, and inspect serialized type metadata or framework registrations.

### Replace Superclass with Delegate

Official catalog: [Replace Superclass with Delegate](https://refactoring.com/catalog/replaceSuperclassWithDelegate.html)

- **Use when:** Replace inheritance used mainly for implementation reuse where the subclass is not safely substitutable for the superclass.
- **Require:** Inventory inherited public surface, protected hooks, overrides, identity, equality, construction, serialization, framework requirements, and every place the subtype is accepted as the superclass.
- **Preserve:** Keep supported operations, dispatch results, errors, lifecycle, identity-sensitive behavior, and external contracts through delegation or a compatibility facade.
- **Avoid:** Do not expose the whole delegate, duplicate inherited logic, change type compatibility without authorization, or replace one tight coupling with a pass-through wrapper.
- **Verify:** Run superclass contract tests against the replacement surface, compile base-typed consumers, and test construction, equality, serialization, and framework integration.

### Replace Subclass with Delegate

Official catalog: [Replace Subclass with Delegate](https://refactoring.com/catalog/replaceSubclassWithDelegate.html)

- **Use when:** Replace a subclass hierarchy that models optional roles, multiple changing dimensions, or awkward combinations better represented through composition.
- **Require:** Map construction, factories, type checks, overrides, serialization, persistence discriminators, extension points, and clients that depend on concrete subtype identity.
- **Preserve:** Keep behavior for every former subtype, selection logic, default behavior, type codes on external boundaries, and lifecycle unchanged.
- **Avoid:** Do not move the same conditional into a delegate selector, create a delegate per trivial difference, or silently change public subtype relationships.
- **Verify:** Run variant contract tests, factory and deserialization tests, type-boundary compatibility checks, and integration tests for every supported combination.

### Consider inheritance in place of delegation

Treat this as an additional design adjustment, not as a current second-edition Fowler catalog entry.

- **Use when:** Consider replacing repetitive delegation only when the receiving type has a stable, genuine substitutability relationship with the proposed base type and inheritance materially simplifies the present design.
- **Require:** Prove the `is-a` contract, base-class stability, permitted extension mechanism, method-resolution behavior, construction rules, state ownership, and compatibility with the language's inheritance model.
- **Preserve:** Keep every delegated behavior, error, side effect, lifecycle, public contract, and extension point unchanged.
- **Avoid:** Do not inherit solely for code reuse, expose unwanted base operations, create a fragile base-class dependency, or alter dynamic dispatch without explicit authorization.
- **Verify:** Run the complete base contract against the new subtype, test override interactions, compile all polymorphic consumers, and inspect serialization and framework behavior.

## Selection rules

Choose the least structural technique that solves the evidenced problem:

- Clarify one expression with **Extract Variable** before extracting a function.
- Clarify one coherent block with **Extract Function** before extracting a class.
- Improve ownership with **Move Function or Field** before inventing a new service.
- Reduce nesting with **Guard Clauses** or **Decompose Conditional** before introducing polymorphism.
- Consolidate duplication only after proving shared semantics and change reasons.
- Preserve a public facade when internal movement can solve the problem without a contract change.
- Prefer no change when preconditions cannot be established or verification cannot protect the invariant.
