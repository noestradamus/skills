# Operational Refactoring Catalog

Use this as a decision aid, not a checklist. Confirm a concrete design problem, select the smallest suitable transformation, preserve the named invariant, and verify immediately. Follow the linked official catalog pages for names and high-level sketches; use the guidance below as original, repository-oriented safety instructions.

## Table of contents

- [Apply the catalog safely](#apply-the-catalog-safely)
- [Extract Function or Method](#extract-function-or-method)
- [Inline Function](#inline-function)
- [Extract Variable](#extract-variable)
- [Rename Variable, Function, or Field](#rename-variable-function-or-field)
- [Change Function Declaration](#change-function-declaration)
- [Encapsulate Variable](#encapsulate-variable)
- [Move Function or Field](#move-function-or-field)
- [Extract Class](#extract-class)
- [Inline Class](#inline-class)
- [Introduce Parameter Object](#introduce-parameter-object)
- [Replace Primitive with Object](#replace-primitive-with-object)
- [Replace Conditional with Polymorphism](#replace-conditional-with-polymorphism)
- [Replace Nested Conditional with Guard Clauses](#replace-nested-conditional-with-guard-clauses)
- [Decompose Conditional](#decompose-conditional)
- [Consolidate Conditional Expression](#consolidate-conditional-expression)
- [Separate Query from Modifier](#separate-query-from-modifier)
- [Replace Temporary Variable with Query](#replace-temporary-variable-with-query)
- [Remove Dead Code](#remove-dead-code)
- [Pull Up or Push Down Members](#pull-up-or-push-down-members)
- [Replace Inheritance with Delegation, or the Reverse](#replace-inheritance-with-delegation-or-the-reverse)

## Apply the catalog safely

- Start from evidence in the target repository; do not force code to match a catalog entry.
- Prefer local, private transformations before cross-module or published-interface changes.
- Preserve evaluation order, evaluation count, short-circuiting, mutation, exceptions, resource cleanup, asynchronous scheduling, and concurrency unless proved irrelevant.
- Apply one technique at a time when possible. Verify before composing it with another technique.
- Use current catalog names where practical. Treat familiar older names as aliases, not separate mechanics.
- Escalate any transformation that touches a protected boundary defined in `SKILL.md`.

## [Extract Function or Method](https://refactoring.com/catalog/extractFunction.html)

- **Signals:** Isolate a coherent responsibility, explain a non-obvious block through a name, shorten a routine, or prepare duplicated logic for comparison.
- **Preconditions:** Understand every input, output, mutation, early exit, exception, closure capture, and resource boundary in the selected block.
- **Keep invariant:** Preserve execution order, evaluation count, return behavior, mutation, I/O, exceptions, asynchronous behavior, and relevant stack-trace expectations.
- **Common failure modes:** Move an expression earlier or later; change receiver or closure binding; lose an early return; alter `await`, cleanup, transaction, or exception scope; create a parameter list that obscures rather than clarifies.
- **Verify:** Exercise each branch and error path of the extracted block; inspect call sites; run type or compile checks plus focused behavioral tests.

## [Inline Function](https://refactoring.com/catalog/inlineFunction.html)

- **Signals:** Remove a misleading name, a needless forwarding layer, or an abstraction whose body is clearer than its indirection.
- **Preconditions:** Find all callers, overrides, callbacks, reflective uses, and dispatch behavior. Confirm inlining will not create harmful duplication.
- **Keep invariant:** Preserve binding, dispatch, argument evaluation, defaults, exceptions, and side effects at every caller.
- **Common failure modes:** Evaluate an argument more than once; bypass an override; alter visibility or receiver context; duplicate logic that will diverge.
- **Verify:** Test every distinct caller shape and subtype path; search for stale references; run static checks that resolve bindings.

## [Extract Variable](https://refactoring.com/catalog/extractVariable.html)

- **Signals:** Name an important intermediate concept, clarify a dense expression, or expose repeated subexpressions for reasoning.
- **Preconditions:** Determine whether the expression is pure, expensive, lazy, nondeterministic, exception-throwing, or state-dependent.
- **Keep invariant:** Evaluate the expression the same number of times and at the same logical point unless equivalence is proved.
- **Common failure modes:** Cache a value that previously changed; force lazy work eagerly; move an exception or side effect; shadow another name.
- **Verify:** Cover changing inputs, exceptional values, and side-effect counts; inspect generated or optimized code only when performance is contractual.

## [Rename Variable](https://refactoring.com/catalog/renameVariable.html), Function, or [Field](https://refactoring.com/catalog/renameField.html)

- **Signals:** Clarify purpose, units, lifecycle, ownership, domain meaning, or side effects; remove a misleading or overloaded term.
- **Preconditions:** Locate static and dynamic references, including reflection, templates, configuration, dependency injection, serialization, ORM mappings, scripts, and documentation used as an interface. Treat function renaming as a form of Change Function Declaration.
- **Keep invariant:** Preserve binding, visibility, wire names, serialized keys, public symbols, and compatibility.
- **Common failure modes:** Miss a string-based reference; change a JSON, database, or protocol name; create shadowing; rename only part of an overload or interface family; break external callers.
- **Verify:** Use symbol-aware rename tooling when reliable; search for old and new names; run compile or type checks; test serialization and external boundaries. Require authorization or a compatibility plan for published names.

## [Change Function Declaration](https://refactoring.com/catalog/changeFunctionDeclaration.html)

- **Signals:** Improve an unclear function name, parameter order, parameter list, return shape, or calling contract; prepare a more cohesive API.
- **Preconditions:** Identify every caller, implementation, override, callback registration, default, named argument, foreign-function boundary, and published consumer.
- **Keep invariant:** Preserve results, side effects, defaults, overload resolution, calling convention, and compatibility unless separately authorized.
- **Common failure modes:** Reorder positional arguments incorrectly; alter default evaluation; break named callers, reflection, binary compatibility, callbacks, mocks, or generated clients.
- **Verify:** Update and test all callers atomically; run interface or contract tests; inspect public declarations and generated bindings. Stop for authorization when callers are not all under control.

## [Encapsulate Variable](https://refactoring.com/catalog/encapsulateVariable.html)

- **Signals:** Control access to shared or mutable state, create a seam for validation or observation, or reduce direct coupling to representation.
- **Preconditions:** Find every read, write, initialization path, alias, thread or task interaction, and serialization mechanism.
- **Keep invariant:** Preserve initialization order, accepted values, mutation timing, visibility, identity, and thread-safety semantics.
- **Common failure modes:** Add recursive accessors; change eager to lazy initialization; introduce synchronization or races; bypass deserialization or framework injection; alter field visibility relied on externally.
- **Verify:** Test initialization, reads, writes, invalid values, serialization, reflection, and concurrency where relevant; search for remaining direct access.

## [Move Function](https://refactoring.com/catalog/moveFunction.html) or [Field](https://refactoring.com/catalog/moveField.html)

- **Signals:** Put behavior near the data it primarily uses, clarify ownership, reduce feature envy, or improve dependency direction.
- **Preconditions:** Identify the true owner, required collaborators, receiver semantics, lifecycle, visibility, overrides, initialization, and module dependencies.
- **Keep invariant:** Preserve dispatch, state ownership, object identity, initialization order, exceptions, serialization, and public access paths.
- **Common failure modes:** Create dependency cycles; move logic to a generic utility with weaker cohesion; change receiver or protected access; duplicate state; break framework discovery or serialization.
- **Verify:** Exercise all call paths and subtype behavior; inspect dependency graphs or imports; test lifecycle and persistence boundaries; retain a delegating facade only when compatibility requires it.

## [Extract Class](https://refactoring.com/catalog/extractClass.html)

- **Signals:** Separate two responsibilities, isolate a cohesive field-and-function cluster, clarify lifecycle, or reduce reasons for one class or module to change.
- **Preconditions:** Establish the extracted responsibility's invariants, ownership, identity, construction, mutation, and interaction with the remaining type.
- **Keep invariant:** Preserve the original public contract, state transitions, object identity where observable, serialization, equality, and resource lifecycle.
- **Common failure modes:** Create an anemic data holder; split an invariant across objects; add circular dependencies; leak a new public type; change equality, copying, or persistence semantics.
- **Verify:** Run contract tests through the original entry points; test construction, mutation, serialization, equality, and cleanup; inspect whether coupling actually decreased.

## [Inline Class](https://refactoring.com/catalog/inlineClass.html)

- **Signals:** Remove a type that no longer has an independent responsibility or whose indirection costs more than it clarifies.
- **Preconditions:** Confirm the class has no external, reflective, serialized, framework, identity, or lifecycle role and that the receiving type remains cohesive.
- **Keep invariant:** Preserve callers, state transitions, identity, serialization, equality, construction, and disposal behavior.
- **Common failure modes:** Break a published type; overload the receiving class; lose a framework hook; merge lifecycles that were intentionally separate.
- **Verify:** Test all consumers and construction paths; inspect runtime registration and serialization; compare the resulting responsibility count and dependency direction.

## [Introduce Parameter Object](https://refactoring.com/catalog/introduceParameterObject.html)

- **Signals:** Group a stable set of parameters that travel together, express a domain concept, or reduce repeated argument-order mistakes.
- **Preconditions:** Confirm the parameters form one cohesive concept and share compatible optionality, validation, ownership, and lifecycle.
- **Keep invariant:** Preserve accepted values, defaults, nullability, argument meaning, serialization, and caller-visible errors.
- **Common failure modes:** Create a grab-bag object; add coupling between unrelated callers; validate earlier than before; change absent-versus-null semantics; break published APIs.
- **Verify:** Test every caller pattern, default, invalid value, and serialization boundary; use a compatibility overload or staged migration only when authorized and necessary.

## [Replace Primitive with Object](https://refactoring.com/catalog/replacePrimitiveWithObject.html)

- **Signals:** Represent a domain value with units, formatting, validation, parsing, or behavior that is repeated around a primitive.
- **Preconditions:** Define value semantics, accepted range, nullability, equality, ordering, hashing, serialization, persistence mapping, and performance sensitivity.
- **Keep invariant:** Preserve accepted inputs, outputs, wire format, equality behavior, ordering, errors, and storage representation unless separately authorized.
- **Common failure modes:** Reject formerly accepted values; change null or empty semantics; alter JSON or database mapping; introduce identity where value semantics are expected; add costly allocation on a hot path.
- **Verify:** Cover boundary values, parsing, formatting, equality, hashing, collections, serialization, persistence, and representative performance when relevant.

## [Replace Conditional with Polymorphism](https://refactoring.com/catalog/replaceConditionalWithPolymorphism.html)

- **Signals:** Replace repeated branching by stable variant or type when each variant owns meaningfully different behavior and future changes currently scatter across switches.
- **Preconditions:** Confirm the variant boundary is stable, all cases are known, default behavior is defined, and polymorphism fits the repository's language and architecture.
- **Keep invariant:** Preserve case selection, result, side-effect order, exceptions, state transitions, fallbacks, and exhaustive handling.
- **Common failure modes:** Replace one clear switch with many tiny types; lose a default case; change construction or dependency injection; move shared logic into duplicated overrides; force object orientation where data-oriented code is clearer.
- **Verify:** Run the same contract suite against every variant; cover unknown or default cases; compare side effects and error paths; inspect whether change locality improved.

## [Replace Nested Conditional with Guard Clauses](https://refactoring.com/catalog/replaceNestedConditionalWithGuardClauses.html)

- **Signals:** Flatten exceptional, invalid, or terminal cases that obscure the main path through deep nesting.
- **Preconditions:** Confirm each guard is terminal for the routine or scope and determine the required predicate evaluation order and cleanup behavior.
- **Keep invariant:** Preserve short-circuiting, predicate order, returned values, exceptions, mutation, logging, and `finally` or deferred cleanup.
- **Common failure modes:** Reorder side-effectful predicates; return before required cleanup; change which error wins; detach an `else` from its intended condition; alter transaction scope.
- **Verify:** Exercise every guard, the main path, combined conditions, side-effect order, and cleanup paths; use a truth table when interactions are subtle.

## [Decompose Conditional](https://refactoring.com/catalog/decomposeConditional.html)

- **Signals:** Name a complex condition or branch, separate decision logic from consequences, or expose domain intent.
- **Preconditions:** Understand short-circuit behavior, repeated expressions, side effects, exceptions, closure capture, and data dependencies.
- **Keep invariant:** Preserve predicate order and count, branch selection, lazy evaluation, state changes, and errors.
- **Common failure modes:** Evaluate both sides eagerly; move a state-dependent check; call a nondeterministic function twice; extract names that misstate edge cases.
- **Verify:** Cover the condition's truth table, boundary inputs, side-effect counts, and each branch's error path.

## [Consolidate Conditional Expression](https://refactoring.com/catalog/consolidateConditionalExpression.html)

- **Signals:** Combine adjacent checks that produce the same outcome for the same conceptual reason.
- **Preconditions:** Prove the checks belong to one decision and that combining them preserves predicate order, diagnostics, and side effects.
- **Keep invariant:** Preserve short-circuiting, evaluation count, selected outcome, logging, metrics, and exception precedence.
- **Common failure modes:** Hide distinct business reasons; skip a diagnostic side effect; reorder an expensive or throwing check; make future exceptions harder to add safely.
- **Verify:** Exercise all individual and combined truth cases; assert observable diagnostics or counters when they are contractual; inspect readability after consolidation.

## [Separate Query from Modifier](https://refactoring.com/catalog/separateQueryFromModifier.html)

- **Signals:** Split a routine whose returned information is entangled with a hidden mutation, making callers difficult to reason about or reuse.
- **Preconditions:** Determine atomicity, transaction scope, concurrency, caching, cost, and whether the query can remain accurate between the split calls.
- **Keep invariant:** Preserve the returned value, mutation count, ordering, authorization, transactionality, and race behavior.
- **Common failure modes:** Introduce a time-of-check/time-of-use race; perform expensive work twice; split one atomic operation; let callers forget the modifier; change audit or event ordering.
- **Verify:** Test state before and after, call counts, failures between the two operations, transaction behavior, and concurrent access. Avoid the split when atomicity is essential.

## [Replace Temporary Variable with Query](https://refactoring.com/catalog/replaceTempWithQuery.html)

- **Signals:** Expose a derived value through a named query, enable extraction, or remove a temporary that obscures data flow.
- **Preconditions:** Determine purity, cost, nondeterminism, mutation dependencies, exception timing, and whether the original temporary intentionally cached a value.
- **Keep invariant:** Preserve evaluation count and timing, result, exceptions, and performance characteristics that are part of the contract.
- **Common failure modes:** Recompute expensive work; observe changed mutable state; repeat I/O or randomness; move an exception; hide an important snapshot in time.
- **Verify:** Assert result and call counts; test mutation between uses; benchmark representative work before accepting additional computation on a hot path.

## [Remove Dead Code](https://refactoring.com/catalog/removeDeadCode.html)

- **Signals:** Remove unreachable branches, unused private symbols, obsolete paths, or abandoned compatibility code that no longer serves a supported consumer.
- **Preconditions:** Prove non-use across static references, dynamic imports, reflection, dependency injection, registration, feature flags, configuration, templates, serialization, external callers, scripts, and generated code.
- **Keep invariant:** Preserve every reachable supported behavior and compatibility promise.
- **Common failure modes:** Trust one text search; remove a plugin hook, scheduled entry point, migration aid, CLI command, serialized name, or externally called symbol; delete code hidden behind rarely used configuration.
- **Verify:** Combine symbol search, configuration and registration review, build and tests, integration coverage, and public documentation inspection. Defer deletion when usage cannot be ruled out credibly.

## [Pull Up](https://refactoring.com/catalog/pullUpMethod.html) or [Push Down](https://refactoring.com/catalog/pushDownMethod.html) Members

- **Signals:** Pull up genuinely identical behavior or state shared by siblings; push down behavior or state that applies only to specific subtypes.
- **Preconditions:** Understand subtype contracts, override resolution, visibility, field initialization, state ownership, equality, serialization, and binary compatibility.
- **Keep invariant:** Preserve dynamic dispatch, subtype behavior, field values, construction order, public surface, and framework integration.
- **Common failure modes:** Generalize behavior that only appears identical; create shared mutable state; change shadowing or overload resolution; violate substitutability; break serialized layouts or ORM mappings.
- **Verify:** Run the base contract against every subtype; inspect override resolution; test construction, serialization, and reflection; cover clients typed as both base and concrete classes.

## [Replace Inheritance with Delegation](https://refactoring.com/catalog/replaceSuperclassWithDelegate.html), or the Reverse

- **Signals:** Replace inheritance when the relationship is not a true substitutable “is-a,” inherited API leaks, or composition gives clearer control. Consider [Replace Delegation with Inheritance](https://refactoring.com/catalog/replaceDelegationWithInheritance.html) only when the delegating type genuinely satisfies the delegate's full stable contract and forwarding dominates the class.
- **Preconditions:** Define substitutability, exposed type relationships, method resolution, protected hooks, construction, lifecycle, identity, equality, serialization, framework expectations, and every consumer.
- **Keep invariant:** Preserve public behavior, type-dependent behavior where contractual, dispatch, state, exceptions, construction, cleanup, serialization, and compatibility.
- **Common failure modes:** Break `is-a` checks, framework discovery, protected extension points, binary compatibility, equality, or serialization; create excessive forwarding; inherit operations the subtype cannot honor.
- **Verify:** Run a shared contract suite across old and new structures; test type checks, factories, dependency injection, serialization, equality, lifecycle, and all public operations. Treat published hierarchies as high risk and require explicit authorization.
