# Appendix C — final acceptance checklist (measured)

| # | Item | Done | Evidence |
|---|---|---|---|
| 1 | S0 calibration bag exists and measured TF replaces placeholder values | ⬜ | calibration_report.json + measured_tf.yaml in configs/sensors/ |
| 2 | Final dataset split and all evaluation bags are frozen | ⬜ | 0 recorded bags (target ~45); splits.json yes |
| 3 | All final bags have metadata | ⬜ | 0/0 |
| 4 | Selected scenes have ground-truth 3D positions | ⬜ | 0 scenes (>= 15) |
| 5 | S2 has real-data fusion ablation and error tables | ⬜ | 0 object-method rows (>= 170 instances x 4 methods) |
| 6 | S3 has a second detector baseline and real-data CLIP test | ⬜ | detectors: []; CLIP pairs: 0 |
| 7 | S3 reports seen/unseen precision, recall and F1 | ⬜ | 0 annotated appearances (~260-300) |
| 8 | S4 reports relation accuracy and temporal-event accuracy | ⬜ | 0 annotated relations (>= 250) |
| 9 | S5 has >= 200 labeled queries and four configuration comparisons | ⬜ | 0 queries (0 checked); 0 configurations |
| 10 | S5 reports hallucination catch / correction metrics | ⬜ |  |
| 11 | S6 has >= 30 real tracking sequences | ⬜ | 0 sequences |
| 12 | S6 has >= 60 action safety trials | ✅ | 60 trials |
| 13 | S7 has >= 30 end-to-end tasks with failure-stage logging | ⬜ | 0 tasks |
| 14 | All final metrics include numerator/denominator or sample size | ✅ | built in: stats.rate() prints 'x % (k/n)' |
| 15 | Key results include easy/medium/hard conditions | ⬜ |  |
| 16 | All thresholds/configurations/prompts are frozen and versioned | ⬜ | S3 frozen prompts, S4 frozen thresholds, S2 frozen fusion config |
| 17 | One-command pipeline run works on a clean setup | ⬜ | python -m src.evaluation.run_all (+ smoke test) |
| 18 | Final dashboard shows perception, 3D, tracking, graph, reasoning proof and action | ✅ | demo/app.py (existing) |
| 19 | Final README explains data, commands, configurations and expected outputs | ✅ | eval/README.md |
| 20 | Failure cases are documented, not hidden | ⬜ |  |
