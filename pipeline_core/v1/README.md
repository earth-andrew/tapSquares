# pipeline_core/v1

The shared, game-agnostic engine behind every game in `game_to_abm_workflows/`. Nothing in here is specific to any one game — it's organized by workflow stage, in the order you'd actually use it:

```
1_build_a_game/        the human-hosted game engine + a blank starter kit for a new game
2_extract_behavior/     the R script that turns session logs into a fitted behavior model
3_autogenerate_abm/     the autonomous-agent engine that runs that fitted model
consistency_checks/     static checkers that catch drift between all of the above
CHANGELOG.md            dated history of fixes to the shared engine
```

## How data flows between the stages

```
1_build_a_game/                 →  your game's CSVs, template, and game details.nls
   (game content you author)       ────────────────────────────────────────────┐
                                                                                 │
                                    used AS-IS, unchanged, by BOTH:             │
                                                                                 ▼
                          2_extract_behavior/                    3_autogenerate_abm/
                          (fits a model to session logs,          (runs autonomous agents
                           using your game's CSVs for context)     using your game's CSVs
                                    │                                directly)
                                    │                                    ▲
                                    ▼                                    │
                     agent_behavior_weights.csv                         │
                     agent_behavior_reference.csv        ───promote────►│
                     sessionList_ABM.csv                  (see below)
```

Concretely: your game's content (from stage 1) is read directly by both stage 2 and stage 3 — nothing about it changes between them. Stage 2's own output (the three files above) is what has to be explicitly carried over to stage 3, because a fresh model fit shouldn't silently overwrite what the ABM is currently being tested against. That hand-off is `3_autogenerate_abm/promote_r_output.sh`.

This is exactly how each folder in `game_to_abm_workflows/<game>/v1/` is organized: `game/` (stage 1 output), `r_pipeline/` (stage 2, reading `game/` directly), `abm/` (stage 3, also reading `game/` directly, plus the promoted output from `r_pipeline/`). See that folder's own README and the R/ABM Pipeline Guide for the mechanics (symlinks, `promote_r_output.sh`, etc.) in full detail.

## Starting a new game

`1_build_a_game/game_builder_starter/` has an empty version of every core CSV (headers only, or headers plus one example row where the format isn't obvious) and a blank `game details.nls`, matching the current engine exactly. Copy that folder as your starting point, and follow one of the `*_Builder_Guide.docx` guides in `guides/` — they walk through filling these files in, stage by stage, using a real game as the worked example. You don't need anything from `2_extract_behavior/` or `3_autogenerate_abm/` until you have a working game and want to fit a behavior model or run an ABM on it.
