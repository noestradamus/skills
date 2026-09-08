# Designing an informative comparison

Consult the sections that affect the current decision. These are conditional design choices, not a checklist to apply to every pilot.

## Reduce the experiment without removing the question

Identify what must remain for the method's proposed advantage to appear. Examples include enough training to learn the mechanism, a horizon long enough to expose accumulated error, a grid that retains important spatial structure, rare cases relevant to the decision, or sizes where asymptotic behavior matters.

Choose the sample or operating regime before comparing outcomes and explain why it is informative. A tiny case can prove local correctness while saying little about deployment accuracy or scaling. Preserve that distinction in the result. A candidate that loses on small inputs is not thereby disproved on large inputs; conversely, a small-case gain is not evidence of large-scale performance.

Treat existing results used to select a candidate as development evidence. Do not present a subsequently selected favorable slice as an untouched evaluation. If the available data or budget cannot discriminate between approaches, use the pilot to establish feasibility or identify the needed experiment, without claiming to have answered effectiveness.

## Choose a comparator for the decision

Use an existing working approach, an appropriate standard method, or an analytical reference. Verify that it is correctly configured and plausible for the stated task. Compare identical cases, information access, scoring, and relevant constraints. A published score from another setup is context, not a controlled local baseline.

Decide which tradeoff is being tested: quality at fixed cost, cost at fixed quality, or attainable quality under actual project constraints. Match tuning opportunity appropriately and record reused pretrained resources. Equal epochs, parameter counts, or nominal hardware time are not automatically the right comparison. If the comparator is broken, repair or replace it transparently before interpreting a candidate's advantage.

## Predictive ML and forecasting

Choose splits that represent the intended use: future periods, new subjects, new locations, or independent experiments. Inspect feature availability at the actual prediction cutoff, including release delays, target-derived features, overlapping label windows, and repeated identities. Select exclusion gaps from the information overlap and forecast horizon rather than guessing a fixed gap.

Fit learned preprocessing on training data; carry the learned transform into evaluation. Use development data for tuning and keep evaluation from influencing model choices. [scikit-learn: data leakage and preprocessing](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage).

A random row split is not justified merely by dataset size. Preserve relevant group or temporal structure; record the unit the result generalizes to. [scikit-learn: grouped data](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-iterators-for-grouped-data) and [time series](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-of-time-series-data).

Check domain semantics that affect comparison: units, coordinates, masks, time zones, forecast issue time versus valid time, and observed versus forecast inputs. Apply the same valid-case definition and metric aggregation to candidate and comparator; report exclusions rather than silently dropping difficult cases. Verify product-specific semantics against official source specifications when relevant.

## Numerical and scientific methods

Use a known solution, a suitably accurate independent reference, or an invariant to check the property the implementation claims. Specify the relevant tolerance, precision, discretization, and operating regime before measuring a performance advantage. If the question is speed at equal accuracy, ensure both methods meet that accuracy.

Distinguish solution error from equation residual: a small residual does not alone establish an accurate solution for an ill-conditioned problem. Choose an error notion relevant to the application, including scale-aware absolute or relative error. [LAPACK Users' Guide: measuring errors](https://www.netlib.org/lapack/lug/node75.html).

Include setup, iterations, convergence failures, and resource costs when they affect the decision. A conservation check can support a structural property without validating forecast skill or physical realism. Record which property each check establishes.

## Algorithm and implementation benchmarks

Verify equivalent outputs or the required approximation quality before interpreting timing. Make input sizes and distributions representative of the intended decision. Distinguish preprocessing/setup from repeated-query or steady-state cost, including amortization only when the target workload actually reuses it.

Record the measurement scope, repeats, and relevant machine/runtime conditions. Account for warmup, caches, garbage collection, and asynchronous completion when applicable. Use a timing tool suited to the runtime; for Python microbenchmarks, understand that `timeit` excludes setup and normally disables garbage collection. [Python: timeit](https://docs.python.org/3/library/timeit.html).

Retain raw timings and describe the chosen summary. Small timing differences on a busy machine may be inconclusive. Repeat appropriately; do not selectively report a favorable repetition or generalize a microbenchmark beyond its measured scope.

## Variability and conclusion strength

Identify relevant variation: sampled cases, initialization, data ordering, tuning choices, or environmental timing. Pair candidate and comparator outcomes on the same cases or seeds where appropriate. Plan repetitions according to the decision and cost; do not prescribe a universal seed count or significance threshold. [Bouthillier et al., Accounting for Variance in Machine Learning Benchmarks](https://arxiv.org/abs/2103.03098).

Report per-case or per-run results when useful. Any uncertainty estimate must match the sampling or dependence structure: repeated pixels, overlapping windows, folds, or measurements from one subject are not automatically independent trials. If available evidence is too small or dependent for a defensible interval, report descriptive variation and the unresolved uncertainty instead.

One deterministic check may establish correctness for its tested case. One stochastic run cannot establish stability across runs. An inconclusive small gain is not permission to search seeds; state what additional independent evidence would clarify the decision. Keep conclusions limited to the tested population, regime, adaptations, and resource conditions.
