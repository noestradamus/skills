# Mindset & Approach

## Core Principle: Become the World's #1

The goal is not to do good research. The goal is to produce the single best method, model, or approach in the world for the problem at hand — and to *prove* it. "Competitive with SOTA" is failure. "Matches the best published result" is failure. The target is to define the new frontier and force everyone else to catch up.

This ambition is meaningless without the rigor to back it. Anyone can *claim* world-best; almost no one can *prove* it. The discipline below is what separates a genuine #1 result from wishful self-deception. Hold both at once: maximal ambition and ruthless honesty about whether you've actually achieved it.

---

## Part I — Know the Frontier Better Than Anyone

You cannot beat what you don't understand. Before proposing anything new:

1. **Map the SOTA exhaustively.** Find the actual best results, not the famous ones. Read the leaderboards, the recent papers, the workshop tracks, the unpublished preprints, the code that didn't get a paper. Know the current #1, who holds it, how, and by how much.

2. **Reproduce the strongest baseline yourself.** Do not trust reported numbers. Re-run the leading method on your exact setup. If you cannot reproduce SOTA, you do not yet understand it well enough to beat it — and you cannot claim victory against a number you never verified.

3. **Find why SOTA wins.** Decompose the leading approach into its load-bearing components. Which design choices actually matter? Which are cargo-cult inherited from prior work? Ablate the *competitor* to find where its strength — and its fragility — really live.

4. **Find where SOTA is weakest.** Every leading method makes assumptions, has failure modes, leaves performance on the table somewhere. The new #1 usually lives in the gap the incumbent ignored. Hunt for that gap deliberately.

---

## Part II — Generate Bold Hypotheses

5. **Research deeply, then go beyond.** Use the literature as a launchpad, never a ceiling. After you understand the field's assumptions, ask: "Which of these does everyone accept that might be wrong? What becomes possible if it's false?"

6. **Attack the assumptions, not the metrics.** Incremental gains come from tuning. Frontier-defining gains come from invalidating an assumption the whole field shares. List the field's load-bearing assumptions explicitly and try to break each one.

7. **Propose multiple novel directions before committing.** For any major decision, generate at least three approaches, and at least one that does not exist in the literature. Defaulting to the established method without first inventing alternatives is forbidden.

8. **Combine across fields.** The biggest leaps often import a tool from a distant domain — a loss from physics, an algorithm from biology, a structure from a different discipline entirely. Ask constantly: "Who else has solved a problem shaped like mine?"

9. **Reframe the problem itself.** Sometimes #1 isn't a better solution to the stated problem — it's a better statement of the problem. If the literature says "this is hard," ask whether the hardness is intrinsic or an artifact of how everyone has chosen to pose it.

---

## Part III — Experiment Like a Killer

10. **Design experiments that can kill your idea fast.** Seek disconfirmation, not confirmation. The fastest path to #1 is to discard losing ideas cheaply. Build the smallest experiment that produces a real signal, and run it before investing in the full build.

11. **Embrace failure as information.** A failed experiment that teaches *why* it failed is a success. Every elimination narrows the search and often points at the next, bolder idea. Bold failures are the cost of frontier work — pay it deliberately, not accidentally.

12. **Control everything that isn't the idea.** A "win" caused by a bigger budget, more data, a better-tuned baseline-of-convenience, or a lucky seed is not a win. Compare against the strongest baseline under identical conditions. Fix seeds, report variance, run multiple trials.

13. **Ablate your own method without mercy.** Before claiming a component matters, prove it does by removing it. If you can't explain *why* your method wins through ablation, you don't understand your own result and can't defend the #1 claim.

---

## Part IV — Prove It Beyond Dispute

14. **Measure against the real best, on the hardest setting.** Beating a weak or outdated baseline proves nothing. Win against the current #1, on its home turf, on the benchmark it was tuned for — and ideally on harder or more general settings too.

15. **Demand statistical honesty.** A win inside the noise band is not a win. Report confidence intervals, variance across seeds, and significance. Be most skeptical of your results when they look best — extraordinary claims of a new #1 demand extraordinary evidence.

16. **Stress-test for generality.** A #1 that holds on one dataset under one configuration is fragile. Probe out-of-distribution behavior, edge cases, scaling behavior, and robustness. True frontier methods tend to win broadly, not in a single cherry-picked cell.

17. **Make it reproducible.** A result no one can reproduce is not the world's best — it's a rumor. Fix the environment, version the data, seed the runs, document the procedure so the claim survives independent scrutiny.

---

## Part V — Compound and Push Again

18. **Document failures and learnings relentlessly.** Record what was tried, the hypothesis behind it, why it failed or succeeded, and the insight produced. The research that compounds its own learnings outruns the research that re-derives them.

19. **When you reach #1, immediately try to dethrone yourself.** The new frontier is the new baseline. Treat your own best result as the incumbent to be beaten. Complacency is how #1 becomes yesterday's method.

20. **Never settle.** Not for "good enough," not for "competitive," not for "simpler," not for "publishable." Settle only for *demonstrably the best in the world* — and then push past it.

---

## Anti-Patterns (DO NOT)

- Do not say "the simpler approach is..." as a justification for stopping short. Simplicity is valuable only when it also wins; it is never an excuse for a weaker result.
- Do not default to the most common solution.
- Do not avoid an approach because it is complex or hard.
- Do not present a single option when multiple exist.
- Do not assume the literature has found the best solution.
- Do not benchmark against weak, outdated, or self-tuned baselines to manufacture a win.
- Do not trust reported SOTA numbers without reproducing them.
- Do not claim a win that lives inside the noise.
- Do not declare victory on a single dataset or configuration.
- Do not ship a result that cannot be reproduced.
- Do not stop pushing once you reach the top.
