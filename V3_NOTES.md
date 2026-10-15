# v3: where people act, treatments, and a consistent package

v3 is the current version of the engine and of all four games. v1 and v2 are unchanged earlier versions. **Nothing here has been run in NetLogo or R**; the `.nlogox` and `.Rmd` files were checked by XML parsing and bracket balance, and the statistics were prototyped in Python.

## What is in v3
- `pipeline_core/v3/` -- the engine. The game template logs a `landChoices` property and a state for the first phase of play; entered player names are the person IDs. The R notebook diagnoses treatments, models patch choice (Steps 6b, 6c), forms classes by recursive splitting, writes a PDF guide, and promotes its output into `abm/` itself (Step 10). The ABM generator shows a slider, switch or chooser per treatment. Full list: `pipeline_core/v3/CHANGELOG.md`.
- `game_to_abm_workflows/<game>/v3/` for **cropraider**, **crouchingtiger**, **cutthecreep** and **dynamicpes**. The last three are the v1 games on the v3 engine; cropraider also has parameter set A01, a practice game plus nine treatment games, four scenario datasets with known ground truth, parameter screening, and a printable player guide (see its README).
- `pipeline_core/v3/sync_core_to_games.py` -- keeps each game's three engine files identical to the core. Edit the engine only in `pipeline_core/v3`, then run `python3 pipeline_core/v3/sync_core_to_games.py` (add `--check` to report drift without changing anything). It keeps each game's own ABM interface (so treatment sliders and per-game defaults survive) unless you pass `--reset-widgets`.

## Before you commit
1. `python3 pipeline_core/v3/sync_core_to_games.py --check` should say all copies match.
2. Re-knit cropraider's notebook so `abm/` and `r_pipeline/` hold outputs from the current settings, and check the ABM loads. The other three games' outputs are from v1 logs until you knit them.
3. If you change `game/sessionList.csv`, regenerate `game/cropRaider_player_guide.pdf` (the table on its back page comes from that file).

## What to put in git
- Add: `pipeline_core/v3`, `game_to_abm_workflows/*/v3`, the root `README.md`, `V3_NOTES.md`, `game_to_abm_workflows/README.md`, `.gitignore`.
- `.gitignore` already skips knitted HTML, ABM run logs, `__pycache__` and `*.bak`.
- Size: cropraider v3's `simulated_scenarios/` is about 33 MB and `simulated_sessions_expanded/` about 8 MB (gzipped). Both can be rebuilt (`simulation/simulate_scenarios.py`, `simulation/simulate_expanded.py`), so ignoring them is an option, but `r_pipeline/sample_sessions` points into `simulated_scenarios/both`, so keep that folder if you want the example to run on clone.
- v2 is an intermediate version whose changes are all in v3. Its cropraider folder is about 160 MB, mostly simulated pools, so I would leave it out of the push (or keep it local).
- The folders use symlinks (`abm/` and `r_pipeline/` back to `game/`). On Windows, cloning them needs Developer Mode or `git config core.symlinks true`.
- The Word guides in `guides/` still describe v1 paths.

## Not done
- The ABM does not use patch-choice weights yet (it still scores every action on every patch), so treatments that act only through patch choice, such as `p_fine`, move nothing for ABM agents.
- The ABM does not evaluate `a:b` crossing features yet.
- The other three games' treatments are undeclared (their `variableRoles.csv` has only the defaults and `numPlayers`).
- No automated tests: the knit and the ABM load are the tests, and the cropraider scenario datasets are the known-answer check.
