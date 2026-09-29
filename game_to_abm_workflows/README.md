# game_to_abm_workflows

One folder per example game, each a complete, working example of all three pipeline stages together: play the game, extract behavior from session logs, and run an autonomous-agent version of it. If `pipeline_core/` is the generic engine, this is where you see it actually applied.

```
<game>/v1/
  game/               the authoritative copy of this game's content — CSVs, template, game details.nls.
                       The only place to edit this game's content.
  abm/                symlinks back to game/ for content that must match exactly, plus the ABM
                       generator itself and the three files promoted in from r_pipeline/.
  r_pipeline/          symlinks back to game/ for the same reason, plus the R notebook and its
                       working output.
  synthetic_sessions/  ready-made synthetic session logs (see MANIFEST.csv), so there's a working
                       example the moment you clone this — no real playtest needed first.
```

Four games are included: **cropraider** (elephant crop-raiding), **crouchingtiger** (human-tiger conflict), **cutthecreep** (invasive lantana), and **pes** (payments for ecosystem services). Each is a fully worked example — open any one and follow `guides/tapSquares_R_ABM_Pipeline_Guide.docx`'s Quick Start to fit a model and run its ABM immediately.

See `pipeline_core/v1/README.md` for why some of these files are symlinks and some are real copies, and the general data flow between `game/`, `r_pipeline/`, and `abm/`.
