# tapSquares game-to-ABM pipeline

tapSquares is a HubNet template for multiplayer land-use games in NetLogo. This repo packages three shared, game-agnostic tools around it:

1. **A NetLogo/HubNet game template** — the human-playable multiplayer game engine.
2. **An R behavior-extraction script** — fits a choice model to logged play sessions.
3. **A NetLogo ABM generator** — replays that fitted model as autonomous agents on the same board logic.

Four example games built on this pipeline are included: **CropRaider** (elephant crop-raiding), **Cut the Creep** (invasive lantana), **Crouching Tiger** (human-tiger conflict), and **PES** (payments for ecosystem services).

**Start here:** `guides/tapSquares_Overview.docx` is a one-page map that routes you to the right guide for what you want to do (run a game, build one, extract behavior, generate an ABM, customize it, or troubleshoot).

## Repo layout

```
pipeline_core/v1/          the shared engine, organized by workflow stage (see its own README.md)
  1_build_a_game/            the human-hosted game engine, and a blank starter kit for a new game
  2_extract_behavior/        the R notebook that fits a behavior model to session logs
  3_autogenerate_abm/        the autonomous-agent engine, and the script that promotes R output into it
  consistency_checks/        static checkers that catch drift between the three stages above
  CHANGELOG.md                dated history of fixes to the shared engine

game_to_abm_workflows/<game>/v1/     one folder per example game (see its own README.md)
  game/                the authoritative copy of that game's content — CSVs, template, game details.nls.
                        This is the only place you edit a game's content.
  abm/                  the ABM test folder. Its CSVs/template/game-details are symlinks back to game/
                        (edit game/, abm/ updates automatically). Also holds the ABM generator itself
                        and the three files promoted in from r_pipeline/.
  r_pipeline/            the R notebook's working folder. Its CSVs are symlinks back to game/;
                        sample_sessions/ is a symlink to synthetic_sessions/. Knitting the notebook here
                        writes agent_behavior_weights.csv, agent_behavior_reference.csv, and
                        sessionList_ABM.csv, which stay in r_pipeline/ until you promote them.
  synthetic_sessions/    ready-made synthetic session logs for this game (see MANIFEST.csv in each),
                        used to fit a first working model without needing real playtest data.

guides/            tapSquares_Overview.docx (start here), the Startup Guide, the R/ABM Pipeline
                   Guide, and one builder guide per game.
```

## Why some files are symlinks and some aren't

Within a game's `v1/` folder, `abm/` and `r_pipeline/` symlink back to `game/` for anything that has to match exactly — a game's CSVs, template, and `game details.nls` genuinely only exist once, in `game/`. Editing a file in `game/` is immediately visible in both `abm/` and `r_pipeline/`; you never need to copy a game-content change anywhere.

The R notebook's three output files are the deliberate exception. They're real, separate files in `r_pipeline/`, not symlinked into `abm/`, so a fresh knit doesn't silently overwrite what the ABM is currently testing against. Run `pipeline_core/v1/3_autogenerate_abm/promote_r_output.sh game_to_abm_workflows/<game>/v1` to copy them across once you're happy with a knit — see the R/ABM Pipeline Guide, Quick Start.

`abm/tapSquares_ABM_generator.nlogox`, `game/tapSquares_template.nlogox`, and `r_pipeline/tapSquares_decision_model.Rmd` are real per-game copies of the shared engine in `pipeline_core/v1/`, not symlinks — this lets a game's copy be tested independently before a shared-engine change is rolled out to every game.

## Quick start with an included game

1. Open `game_to_abm_workflows/<game>/v1/game/tapSquares_template.nlogox` in NetLogo to run the human multiplayer game (see the Startup Guide).
2. To build an ABM from the included synthetic data: knit `game_to_abm_workflows/<game>/v1/r_pipeline/tapSquares_decision_model.Rmd`, then run `pipeline_core/v1/3_autogenerate_abm/promote_r_output.sh game_to_abm_workflows/<game>/v1`, then open `game_to_abm_workflows/<game>/v1/abm/tapSquares_ABM_generator.nlogox` (see the R/ABM Pipeline Guide).

## Starting a new game

A game's content doesn't need to know anything about this repo's folder structure — the Builder Guides teach the game-building mechanics on their own, using a real game as a worked example, and `pipeline_core/v1/1_build_a_game/game_builder_starter/` has a blank set of every core file to copy as your starting point. The `game_to_abm_workflows/<game>/v1/` layout above only matters once you're ready to use the R pipeline and ABM generator on a game you've built.

## What's not in this repo

Actual gameplay-run logs (from NetLogo's BehaviorSpace) and R's knitted HTML report aren't checked in — they're regenerated by using the tools, not part of the pipeline itself. `synthetic_sessions/` ships instead, so every game has ready-to-use session data without anyone needing to run a live playtest first.
