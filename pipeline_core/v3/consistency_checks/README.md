# consistency_checks

Static, best-effort checkers that catch drift between the three stages — a game-content change that quietly breaks something in extraction or the ABM before you find out the hard way, mid-session, in NetLogo. Each takes a path to one game's `game/` folder (in `game_to_abm_workflows/<game>/v1/game`) and prints what it finds; none of them modify anything.

**check_patchproperty_drift.py** — flags a patches-own variable a game's logic reads/sets that's missing from `patchPropertyList` in `game details.nls` (so `2_extract_behavior/` never sees it).

**check_shape_drift.py** — flags an `imageName` referenced in a game's CSVs with no matching `<shape>` defined in the template and/or the ABM generator (they each have their own independent shape library — a fix to one does not cover the other).

**check_session_column_drift.py** — flags a `sessionList.csv` column with no matching global anywhere the ABM generator can find it, which crashes Setup the moment the session file is read.

Run any of these after editing a game's content, before handing it to stage 2 or 3.
