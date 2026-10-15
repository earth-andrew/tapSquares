# 3_autogenerate_abm

**tapSquares_ABM_generator.nlogox** — a second NetLogo model, sharing the same underlying engine as `tapSquares_template.nlogox`, but with no human players: every agent on the board chooses its actions using the fitted weights from `2_extract_behavior/`.

**promote_r_output.sh** — copies `agent_behavior_weights.csv`, `agent_behavior_reference.csv`, and `sessionList_ABM.csv` from a game version's `r_pipeline/` into its `abm/`. This is the deliberate hand-off point between stage 2 and stage 3: nothing in `abm/` changes until you run this, so a fresh model fit doesn't silently overwrite what the ABM is currently being tested against.

Usage: `./promote_r_output.sh game_to_abm_workflows/<game>/v1`

This step needs your game's CSVs (from `1_build_a_game/`, already in place via symlinks) plus a promoted fit from `2_extract_behavior/`. See `guides/tapSquares_R_ABM_Pipeline_Guide.docx`, Part 0 Quick Start and Part 2.
