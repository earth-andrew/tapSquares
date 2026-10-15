# Test scenarios with known ground truth (parameter set A01)

Four sets of simulated sessions (54 each, 9 players per session, the same mix of player kinds every time) made by `../simulation/simulate_scenarios.py`. Game settings are parameter set A01 (`../param_screening/README.md`), the same as `../game/sessionList.csv`. The scenarios differ only in what players respond to. Logs are gzip-compressed; the notebook reads `.csv.gz` directly.

Treatments, crossed in every scenario: `p_fine` 0.02 / 0.05 / 0.08, `defendCost` 2 / 5 / 8, `pa_size` 8 / 14 (how much land is protected). `fine` is fixed at 2. Players' personal limit on expected fines spans the expected-fine range of those `p_fine` levels, so the assumed response shows up inside the range.

| scenario | players respond to | expected from the notebook |
|---|---|---|
| `fine_only` | the expected fine (p_fine x fine) | **p_fine used** (through patch choice); defendCost weak; pa_size not used |
| `cost_only` | the cost of defending | **defendCost used**; p_fine not used; pa_size not used |
| `both` | both | **p_fine and defendCost used**; pa_size not used |
| `neither` | neither | **p_fine not used** (false-positive control); defendCost weak (a dearer defend action uses more of the turn's effort even for players who ignore the cost); pa_size not used |

`pa_size` changes how much protected land exists, so the share of planting on protected land moves with it even where no one responds (0.14 vs 0.19 in `fine_only`). That is land supply, not behavior; the notebook should not accept it as a treatment. Each folder has `ground_truth_treatments.csv` and `ground_truth_persons.csv`.

**Check on the generated data** (manifests): share of planting on protected land by `p_fine` 0.02 / 0.05 / 0.08 is 0.22 / 0.17 / 0.09 in `fine_only` (0.21 / 0.18 / 0.10 in `both`) and flat in `cost_only` and `neither`. Mean defends per session by `defendCost` 2 / 5 / 8 is 67 / 32 / 13 in `cost_only` (61 / 31 / 12 in `both`) and 63 / 61 / 51 in `fine_only` (the budget effect).

**To run one:** in the notebook's Settings chunk set `session_dir <- "../simulated_scenarios/fine_only"` (or another folder) and Knit. Compare `treatment_report.csv` and `choice_treatment_report.csv` with the table. Run each scenario on its own, since the notebook treats everything in `session_dir` as one dataset. The Python stand-in has not been run on these A01 datasets; the earlier scenario set it was run on is replaced.
