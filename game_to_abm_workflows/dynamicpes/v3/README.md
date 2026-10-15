# dynamicpes v3

The v1 game on the v3 engine. Game content (CSVs, `game details.nls`) is unchanged from v1.

- `game/tapSquares_template.nlogox`, `abm/tapSquares_ABM_generator.nlogox`, `r_pipeline/tapSquares_decision_model.Rmd` are the v3 engine files (kept in step by `python3 pipeline_core/v3/sync_core_to_games.py`).
- `game/variableRoles.csv` gains `numPlayers` as `not_treatment`; declare this game's own treatments there (role `session_parameter`) if it has any.
- `synthetic_sessions/` was regenerated with PLAYER lines (entered name = person ID). These are random-play logs: they have no `landChoices`, so the notebook skips the patch-choice model and says so.
- **Stale until re-knit:** `abm/agent_behavior_weights.csv`, `agent_behavior_reference.csv`, `sessionList_ABM.csv` (and the copies in `r_pipeline/`) were fitted to v1 logs. They load, but knit `r_pipeline/tapSquares_decision_model.Rmd` (Knit, not Run All) to refresh them; the last step of the knit copies results into `abm/`.
- Not yet run in NetLogo or R with the v3 engine.
- The ABM's interface keeps this game's own defaults (`patches_game` 21, `numAgents` 7, session 1, smaller patch size), which the sync tool preserves.
