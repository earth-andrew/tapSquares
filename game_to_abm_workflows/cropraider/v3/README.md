# cropRaider v3

Elephant crop-raiding on the v3 engine (`pipeline_core/v3`). **Not yet run in NetLogo or R**: the statistics were prototyped in Python stand-ins, and the `.nlogox` and `.Rmd` edits were checked only by XML parsing and bracket balance. Test in this order: play the game, run the ABM, knit the notebook.

## Game settings (parameter set A01)
Chosen by `param_screening/` to avoid dominated decisions (see its README for the evidence and caveats).

| setting | value | where |
|---|---|---|
| `p_fine` (treatment) | 0.02 / 0.05 / 0.08 | `game/sessionList.csv` |
| `defendCost` (treatment) | 2 / 5 / 8 | `game/sessionList.csv` |
| `paSoilBonus`, `pa_size`, `endowment`, `rainFactorMin`, `cropR` | 0.72, 11, 10, 0.45, 0.35 | `game/sessionList.csv` |
| `growCrop` effort | 4 | `game/actionList.csv` |
| `elephantNeedsTurn` | 1.5 | `game/game details.nls` |
| elephant herd probability | 0.05 | `game/initialConditionList.csv` (row 3) |

`game/sessionList.csv` has one game per sessionID: **0 = practice** (1 round x 4 phases, rain `1 1 0 0`, with `*_practice.csv` copies of the non-spatial-function and info-screen files so the round summary shows at phase 4) and **1-9 = the treatment games** (`p_fine` x `defendCost`). `gameID` equals `sessionID`. The previous sessionList is kept as `sessionList_before_A01.csv`.

`game/cropRaider_player_guide.pdf` is a two-sided handout (rules, costs and benefits, elephant behavior, and the table of games). It was built from `sessionList.csv`; rebuild it if you change the settings.

## Folders
- `game/` -- authoritative game content, the v3 template, `variableRoles.csv` (declares `p_fine`, `defendCost`, `fine` as session parameters; `sessionID`, `gameID`, `numRounds`, `numPhases`, `numPlayers` as `not_treatment`; `cropOwner` as `player_reference`).
- `abm/`, `r_pipeline/` -- symlinks back to `game/` for content, plus the ABM generator and the notebook. `r_pipeline/sample_sessions` points at `../simulated_scenarios/both`; set `session_dir` in the notebook's Settings chunk to use another folder.
- `simulated_scenarios/` -- four datasets (54 sessions each) with known ground truth about which treatments matter: `fine_only`, `cost_only`, `both`, `neither`. See its README for the expected result of each. Made by `simulation/simulate_scenarios.py` (about 30 s).
- `simulated_sessions_expanded/` -- an older 54-session pool of 33 people in 11 player types (gzipped), made under the pre-A01 settings (`p_fine` 0.05-0.2, `endowment` 12). Useful for checking class recovery against `ground_truth_persons.csv`.
- `simulation/` -- the Python stand-in for the game and the simulators. `param_screening/` -- the dominance screening and its results.

## What to check after knitting
`treatment_report.csv` and `choice_treatment_report.csv` against the scenario table; `person_classes.csv` against the ground-truth persons file; the "Where each class acts" page of `dataset_guide.pdf`; the widgets Step 10 adds to the ABM (patch-choice-only treatments are inert for ABM agents, because the ABM does not use patch choice yet).

## Stale until re-knit
`abm/` and `r_pipeline/` hold outputs (weights, class files, treatment ranges, `sessionList_ABM.csv`) from earlier knits on earlier data.

## Known limits
The ABM does not use `agent_patch_choice_weights.csv` yet. Treatment responses in the simulated data are assumed, not estimated. The stand-in model has an 8x8 map and 4 players. The earlier v2 write-up is in `../v2/README.md`.
