# 2_extract_behavior

**tapSquares_decision_model.Rmd** — reads a folder of session log CSVs (the files tapSquares itself writes while a game is played) and fits a behavioral choice model: for each class of player and each action available to them, which features of the board and game state make that action more or less likely. Exports `agent_behavior_weights.csv` and `agent_behavior_reference.csv`, the two files stage 3 reads directly, plus `sessionList_ABM.csv`.

**generate_synthetic_sessions.py** — generates synthetic session logs for a game, so you can test this step (or bake in a specific behavioral pattern) without needing real playtest data yet.

**variableRoles_TEMPLATE.csv** — a blank starting point for a new game's `variableRoles.csv`, which controls how the R model encodes round/phase counters and ownership variables.

This step needs your game's CSVs (from `1_build_a_game/`, already in place via the `game/` → `r_pipeline/` symlinks in `game_to_abm_workflows/<game>/v1/`) plus a folder of session logs. See `guides/tapSquares_R_ABM_Pipeline_Guide.docx`, Part 1.
