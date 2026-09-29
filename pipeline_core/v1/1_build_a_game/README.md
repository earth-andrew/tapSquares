# 1_build_a_game

**tapSquares_template.nlogox** — the human-hosted, HubNet multiplayer game engine. Generic across every game: it reads whatever CSVs and `game details.nls` it's pointed at and renders that game's rules, board, and player interface.

**game_builder_starter/** — a blank starting point for a new game: every core CSV with just its header row (or one example row, for `sessionList.csv`, where the format needs a live example), and a blank `game details.nls` with the three hook procedures stubbed out. Copy this folder to start building.

Building a game means filling in these files. The `*_Builder_Guide.docx` guides (in `guides/` at the repo root) walk through that process stage by stage, using a real game as a worked example — start with whichever example is closest to what you're building, or the Elephant/CropRaider guide if none is close, since it explains the shared engine most fully.

Once you have a working game, see `guides/tapSquares_Overview.docx` for what to do next (extract behavior, autogenerate an ABM, etc.).
