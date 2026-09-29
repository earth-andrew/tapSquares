# pipeline_core/v1

First reconciled version. Prior to this, the three shared files (template,
ABM generator, R behavior-extraction script) had each independently forked
inside individual game folders, with fixes made in one game's copy never
propagating to the others. This version merges what was found.

## tapSquares_template.nlogox
Adopted as-is from the copy shared by Lantana Stage 6 / Tiger / PES's
"updated to v1.2" build (md5 `47ce9a2...`) -- these three had already
converged on an identical, current copy. The CropRaider base folder still
had a stale pre-fix copy sitting alongside it (md5 `7d32f0b9...`); not
carried forward.

Confirmed: the core template already logs `ownedBy`, `village`, and
`shared?` unconditionally into every STATE| line, regardless of whether a
game's own `patchPropertyList` lists them (see ~line 2210-2220). This
closes the land-ownership logging gap that would otherwise exist in
3 of the 4 games' hand-authored `patchPropertyList`s.

## tapSquares_ABM_generator.nlogox
Adopted from Lantana's v23 (not v22, which was the version otherwise most
widely copied but is missing a real fix). v23 is a strict superset of v22
-- 30 lines added, nothing removed or changed -- adding support for R's
"bare identifier" dummy-coding convention for boolean predictors (e.g.
`hasResource` -> `hasResourceTRUE`/`hasResourceFALSE`), as distinct from
the backtick-quoted form R uses for predictor names with special
characters (tapSquares' `?`-suffixed booleans). Both forms now resolve.

CropRaider, Tiger, and PES's own v22 copies had each independently
diverged in other, smaller ways (confirmed by md5 -- 3 distinct hashes
across 4 copies); those changes were not individually reconciled into
this version and should be re-examined if a specific game's ABM behavior
regresses against what it had before.

## tapSquares_decision_model.Rmd
Reconciled from three diverged copies (CropRaider/PES shared one,
untouched; Lantana and Tiger had each diverged independently). Changes
from the CropRaider/PES baseline:

1. Round/phase (or whatever a game calls its counter) are no longer
   unconditionally excluded from candidate predictors. A new, optional
   per-game `variableRoles.csv` can opt a counter in and choose its
   encoding (numeric, cyclical with a period, or categorical) so a real
   cyclical/seasonal effect can be tested and modeled in a way that
   extrapolates to round values never seen in training. Default (no
   config, or not listed) is unchanged: excluded.
2. Ownership variables (`ownedBy`, `village`) get explicit "unassigned"
   factor-level handling via the same config, rather than being treated
   as a plain number on a continuous scale.
3. Kept from the Lantana branch: `excluded_predictors`, a simple
   named-variable dropout list for real predictors you want excluded
   from a specific fit.
4. New: if `sessionList.csv` is present in the working directory, the
   export step now writes `sessionList_ABM.csv` itself -- copying every
   column and adding the three that point at this notebook's own outputs
   (`agent_behavior_weights.csv`, `agent_behavior_reference.csv`,
   `outcomePlotList.csv`). This used to be a manual, error-prone edit.
5. `log_paths` default changed to the sample_sessions/ folder-glob
   pattern (was: a single hardcoded file in the CropRaider/PES copy;
   Tiger/Lantana had already made this change independently).

**Not yet run against real data** -- see the file's own header for the
honesty-check convention this project uses. Should be knit-tested against
at least one real session log before being treated as validated.

## New in this version (not present anywhere before)
- `variableRoles_TEMPLATE.csv` -- the per-game config described above.
- `game_details_REFERENCE_cropraider.nls` -- kept as a structural
  reference (globals / patches-own / three setup procedures / per-
  mechanic procedures pattern) for building a new game's
  `game details.nls`. Content is CropRaider-specific and should never be
  copied wholesale into another game.
- `promote_r_output.sh` -- copies a game version's r_pipeline/ output
  into its abm/ folder. Nothing in abm/ changes until this is run.

## Fixes since first draft of this version
- `tapSquares_decision_model.Rmd`: the `MANIFEST.csv` file that
  documents each synthetic session set was being globbed and parsed as
  if it were a session log itself (it lives in the same folder). Log
  path selection now excludes it by name.
- `tapSquares_decision_model.Rmd`: ownership variables (`ownedBy`,
  `village`) are now factor-encoded using their raw value as the level
  text (e.g. "0", "1", "2") instead of relabeling the sentinel to the
  word "unassigned". The relabeled version caused a crash on the ABM
  side (`Nothing named VILLAGEUNASSIGNED has been defined`) because R's
  dummy-coded coefficient name (`village` + level, e.g.
  "villageunassigned") had no way to be mapped back to a real patch
  value without the ABM generator separately knowing the
  `unassignedValue` config -- unnecessary coupling. Keeping the raw
  value as the level avoids the whole problem.
- `tapSquares_ABM_generator.nlogox`, `get-feature-value`: added a
  general fallback for categorical (non-boolean) dummy-coded predictor
  names -- previously only booleans (`TRUE`/`FALSE` suffix) and an
  exact bare-variable match were handled, so any other factor-coded
  feature (ownership variables, or a categorical counter if a game
  opts one in via `variableRoles.csv`) crashed the run with "Nothing
  named ... has been defined." Now resolves by peeling the longest
  plausible variable-name prefix off the feature name and comparing
  the remainder to that variable's current value as text. A feature
  that still can't be resolved at all (game changed since the model
  was fit, etc.) is now treated as 0 with a one-time printed note,
  never a crash -- this is also the concrete fix for the "ABM
  shouldn't shut down on an unrecognized value" requirement from the
  very start of this project.

## Fixes since testing began
- `tapSquares_ABM_generator.nlogox`, `get-feature-value`: the new
  categorical-dummy-coding fallback used `report` directly inside a
  `carefully` block, which NetLogo doesn't allow ("not in a
  TO-REPORT"). Fixed by setting a result variable inside `carefully`
  and reporting it afterward, outside the block -- the same pattern
  the pre-existing code already used elsewhere in this function.
- `tapSquares_ABM_generator.nlogox`, `get-feature-value`: the
  backtick-quoted branch (for predictors like `` `water?`TRUE ``)
  assumed the quoted name always resolves to a genuine NetLogo
  boolean and called `ifelse-value` directly on it -- crashed with
  "IFELSE-VALUE expected ... TRUE/FALSE but got the number 0" when a
  backtick-quoted predictor turned out to be non-boolean at runtime
  (backtick-quoting only means the name needed quoting, e.g. its
  trailing "?", not that it's boolean). Now checks `is-boolean?`
  first and falls back to a plain text comparison (matching the
  general categorical case) when it isn't.

## Performance fix
- `tapSquares_ABM_generator.nlogox`, `get-feature-value`: was doing
  live `runresult`/`carefully` classification of every feature name on
  every single call (every scored feature x every candidate action x
  every agent x every tick) -- including failed probing attempts,
  which are the most expensive case in NetLogo. Split into
  `classify-feature-name` (the one-time-per-distinct-name
  classification, now cached in a `table:` keyed by feature name) and
  a lean `get-feature-value` that, on a cache hit, does exactly one
  live value lookup. Added the `table` extension for this. Classifying
  a feature name is a structural property of the variable it refers
  to (boolean vs. categorical, which candidate name resolves) and
  never changes mid-run, so caching it is safe -- only the live value
  lookup needs to re-run every call.

## UI/workflow improvements
- `tapSquares_ABM_generator.nlogox`: `go` used to run the entire game
  to completion in a single click (an internal `while` loop advancing
  every round/phase). Restructured to advance exactly one round/phase
  per call and call `tick`, with the Go button now `forever="true"` --
  NetLogo's native forever-button behavior (click to start repeating,
  click again to pause) is the play/pause control, no custom pause
  logic needed. `setup` now calls `reset-ticks`.
- Added a `ticks` monitor next to the buttons, and a `numTimesteps`
  slider alongside `patches_game`/`numAgents` -- an ABM-specific cap
  on how many rounds/phases to simulate, independent of (and can be
  set higher or lower than) the game's own authored `numRounds`;
  whichever cap is reached first stops the run.
- **REVERTED, was wrong:** briefly removed the early patch-
  coloring/imaging pass in `setup` (the one before
  `run-spatial-functions`/`run-non-spatial-functions`) as an assumed
  redundancy. It is not redundant: it's what actually spawns
  displayTurtles (elephants, crops, etc.) via `update-patch-image`'s
  countMeasure-driven sprout logic, and round_play=0 non-spatial
  functions like CropRaider's `assign-elephants` depend on those
  turtles already existing. Removing it caused elephants to spawn
  with no herd assigned, crashing `move-elephants` ("MOVE-TO expected
  ... but got the number 0") the first time it ran post-setup.
  Restored. The brown-screen report is still open and was never
  actually explained by this -- back to investigating it separately,
  now with a screenshot requested from the user to distinguish
  "whole board flat brown" from "scattered brown patches mixed with
  normal ones," which point to different causes.

## Brown-screen bug -- root cause found and fixed
Confirmed via a Command Center dump comparing a broken vs. a working
Setup: on the broken run, `count actions`/`landStates`/`landDisplays`/
`ICs`/`spatialFunctions`/`nonSpatialFunctions` were ALL 0, despite
their source files existing and being found (`file-exists?` true,
filenames correct). Combined with the user's observation that it only
happens when `patches_game`/`numAgents`/`numTimesteps` are changed off
their defaults before Setup, and works again on an immediate retry:
`resize-world` clears every turtle whenever the requested world size
actually differs from the world's current size (documented NetLogo
behavior) -- and `setup` was calling `resize-world` AFTER the six
`read-*-file` procedures had already created their data-holding
turtles from those CSVs. Any real resize wiped them all out, silently
(no error) -- `setup` completed and looked successful, just with
nothing actually loaded, hence a board with no landState images or
land-cover turtles to draw: brown. A same-size retry's `resize-world`
call is a no-op, so the turtles survive the second time -- matching
every symptom reported (first-click-only, fixed by a retry, only
triggered by changing patches_game/numAgents/numTimesteps, root cause
unrelated to which specific game). Fixed by moving `resize-world`/
`set-patch-size` to run BEFORE the read-*-file calls.

Also audited the full widget layout against the rule "everything a
button uses should sit above it" -- already consistent, no widget
repositioning needed; this was purely an internal procedure-ordering
bug, not a layout one.

## Widget reordering for visual dependency cues
`sessionID` sat above "1. Read Session File", implying it was needed
for that step when it's actually only read by "2. Initialize
Session" (`prepare-session`, the Read Session File button's own
procedure, only uses `sessionParameters`). Reordered so each widget
sits directly above the first thing that reads it: sessionParameters
-> "1. Read Session File" -> sessionID -> patches_game/numAgents/
numTimesteps sliders -> "2. Initialize Session" -> "3. Setup" ->
ticks monitor -> "4. Go".

## Synthetic-data generator fix: boolean detection wasn't naming-convention-safe
`generate_synthetic_sessions.py`'s `gen_value` only treated a patch property
as boolean when its name ended in `?` (tapSquares' usual convention). This
missed real booleans that don't follow it -- confirmed live: Crouching
Tiger's `arable` is set via `set arable true` in `game details.nls` with no
`?`. Synthesizing it as a random number meant R fit it as a numeric
predictor, and the ABM crashed at runtime (`* expected input to be a number
but got the TRUE/FALSE false instead`) multiplying a weight by the real
(boolean) value.

Fixed with `parse_boolean_props(game_dir, candidate_props)`: scans
`game details.nls` and the three function-list CSVs for a literal
`set <prop> true` or `set <prop> false` assignment (case-insensitive),
independent of naming convention. `gen_value` now treats a property as
boolean if it ends in `?` OR is in this scanned set. Not exhaustive (a
boolean only ever set via a computed expression, never a literal, would
still be missed), but catches real cases the naming heuristic can't.

Regenerated synthetic_sessions/ for all four games. The scan additionally
caught properties in every other game that would have hit this same crash
later, had they been swept for treatment/inclusion: Crouching Tiger
(`arable`, `attacked?`, `cropped`, `fenced?` -- `cropped` in particular has
no `?` at all), Cut the Creep (`degraded`, `hasResource`), PES (`hasCanola`,
`hasFlower`, `hasGrass`).

## setup() was silently skipping phase-2 round_play=0 functions
Crouching Tiger reported: no animals ever placed on the board. Traced to
`setup`: the human template only ever reaches `currentPhase = 2` during
setup via a SECOND land-confirmation transition -- village land confirms
at phase 1, and only if the game ALSO uses private land does `currentPhase`
increment to 2 for a second `run-non-spatial-functions`/
`run-spatial-functions` call when private land is confirmed (see
`advance-to-next-round` Case 1 then Case 2 in `tapSquares_template.nlogox`).
A game with a round_play=0 function scheduled for phase 2 depends on that
second call -- Crouching Tiger's initial animal placement
(`nonSpatialFunctionList.csv` row 1: `round_play=0, phase=2`) is exactly
this. The ABM generator's `setup` auto-assigns village/private land in one
shot (no interactive transitions) and only ever called these procedures
once, at phase 1 -- silently skipping every phase-2 setup-time function,
no error, confirmed live (empty board, no animal turtles).

Fixed: `setup` now makes a second call to `run-non-spatial-functions`/
`run-spatial-functions` at `currentPhase = 2`, but only when a game uses
BOTH `chooseVillageLand?` and `choosePrivateLand?` -- matching exactly
which games' human template flow ever reaches phase 2 during setup (a
game using only one of the two, or neither, never does, and correctly
still gets just the one phase-1 call). Propagated to all four games.

## Real bug, not cosmetic: the ABM was still stopping on the game's own numRounds
Crouching Tiger reported the ABM "exiting" (a "Run setup first." dialog)
after 5 or 6 steps despite `numTimesteps` being set much higher (90). My
first instinct was to treat this as a UX annoyance and quiet the dialog --
wrong instinct, caught before making the change. The actual problem: two
places still hard-stopped the run once `currentRound > numRounds` (the
GAME's own authored round count, e.g. Crouching Tiger's `numRounds=3`,
`numPhases=2` = 6 steps), regardless of `numTimesteps`:
- `advance-to-next-round` called `end-game` and `stop` the moment
  `currentRound > numRounds`.
- `go`'s precondition required `currentRound <= numRounds` in addition to
  `currentRound <= numTimesteps`.

This directly contradicted a design decision already built into
`round-eligible?` (see its own comment, a few hundred lines up): a
function or action's `round_play` list is treated as "eligible from its
listed round onward," not an exact match, specifically so the ABM can run
PAST the round range the game file's author happened to list, to test
behavior at round values the human game never reached. `numTimesteps`
(the slider) was always meant to be the one thing controlling how long an
ABM run lasts, independent of the underlying game's own round/phase
structure -- this is the same requirement from the very start of this
project (round/year counters shouldn't hard-fail or artificially cap the
ABM). The numRounds-based stop meant `numTimesteps` only ever mattered
when set LOWER than the game's own numRounds x numPhases -- set higher,
it was silently ignored.

Fixed: removed the `currentRound > numRounds` stop from
`advance-to-next-round` entirely (currentRound now just keeps
incrementing, matching what `round-eligible?` already assumed). `go`'s
stopping condition is now `ticks >= numTimesteps` alone -- ticks is
NetLogo's own counter of completed go-calls, so this is exact and
round/phase-agnostic, and the "Run setup first." dialog no longer appears
at the end of a normal run (a clean "run complete." + `end-game` fires
instead, from inside `go` itself, once `numTimesteps` is reached).
Propagated to all four games.

## Reverted: numTimesteps removed, run length is numRounds again
Everything in the two sections above this one (the numRounds-based stop
being "wrong," numTimesteps as the sole run-length control, the
"numRounds is now inert" framing) has been undone at the user's explicit
request. On reflection, numTimesteps was added reactively this same day
(one of three quick UX asks: pause button, tick monitor, timesteps
slider) without thinking through what it actually meant for a game's own
authored numRounds/numPhases to stop mattering -- exactly the kind of
under-considered interface addition the "slider vs. sessionList.csv"
principle below exists to prevent.

Final decision: the ABM runs for exactly as many rounds as the game
itself was authored for (numRounds, sessionList.csv) -- same as a human
playthrough, no separate ABM-only run-length concept. `numTimesteps` is
removed from the interface (slider widget deleted) and from the code
entirely (no global, no references). `advance-to-next-round` again calls
`end-game`/`stop` once `currentRound > numRounds`. Want a longer or
shorter ABM run? Increase/decrease `numRounds` in `sessionList.csv` --
the same file edit that would change how long the human game runs, kept
consistent on purpose. The `ticks` monitor and the Go/Pause forever
button both stay (those were fine independently of numTimesteps).
Propagated to all four games.

## Design principle: interface slider vs. sessionList.csv parameter
Follow-up question from the numRounds bug/revert above: given
patches_game/numAgents are sliders but numRounds/numPhases aren't, what's
the actual rule for which parameters belong on the interface vs. in
sessionList.csv?

**A parameter belongs on the interface only if no game-content file
(actionList.csv/spatialFunctionList.csv/nonSpatialFunctionList.csv's
round_play/phase columns, or any function's expression) is authored
assuming a fixed value for it.** Varying a parameter that content doesn't
depend on (patches_game, numAgents) safely stress-tests the model outside
the human game's original conditions -- board size and population don't
change what any round_play/phase column means. Varying a parameter that
content DOES depend on desynchronizes the ABM from what its own game
files mean, silently -- numPhases and numRounds both fall in this
category: every round_play/phase column in a game's CSVs is authored
against specific values of both (this is exactly why Crouching Tiger's
phase-2 round_play=0 functions only make sense at numPhases=2 combined
with both land-choice flags being true, and why the ABM's run length
tracks numRounds the same way a human playthrough's does).

By this rule: numPhases AND numRounds both stay sessionList.csv-only,
permanently -- real, structural state, not interface controls. A shorter
or longer ABM run is a sessionList.csv edit (numRounds), same file, same
mechanism a human game's length would be changed by -- not a separate
ABM-only concept layered on top (see the numTimesteps revert, above, for
why that was tried and undone). Commented in the ABM generator's
globals[] block, next to numRounds/numPhases's declaration, so this
reasoning is visible in the file itself, not just here.

## Real bug: reference action was "most common," not always "do nothing" -- silently excluded whichever action won that coin flip
Crouching Tiger reported: tiger attacks working, but agents never build
fences, ever, across many rounds. Confirmed via
`agent_behavior_reference.csv`: actionID 4 (buildFence) was the fitted
reference/baseline category for this session. A multinomial logit's
reference level always scores exactly 0 -- no fitted coefficients, no
state-dependence, by construction (`score-action-for-agent` in the ABM
generator returns a hardcoded 0 the moment `candidateActionID =
referenceActionID`, confirmed at that line). The ABM's own greedy
selection (`choose-actions-for-agent`) picks actions by comparing every
action's fitted score against `-99`'s ("do nothing") fitted score --
correct and intentional (see the "Fixes since first draft" section,
above, on why margin-over-do-nothing replaced a flat threshold). But that
comparison is only mathematically sound when `-99` IS the reference:
then every real action's score directly equals its own log-odds relative
to doing nothing. Pick anything else as reference (buildFence, here) and
that one action gets permanently pinned to 0 while `-99` gets real,
comparatively favorable fitted coefficients -- so the reference action
loses to "do nothing" identically on every patch, every round, forever,
for a reason with nothing to do with real behavior.

Root cause of WHY buildFence became the reference: the Rmd picked the
reference category as `most_common_action` -- whichever actionID
appeared most often in the training data. Crouching Tiger's synthetic
data assigns actions via near-uniform random choice (no real behavioral
signal), so which action happens to be "most common" is essentially a
coin flip baked into sampling noise -- and whichever one wins that flip
gets silently, permanently excluded from every ABM agent's choices for
the rest of the run. This isn't Crouching-Tiger-specific or
synthetic-data-specific in principle -- it's a structural bug that could
silently zero out ANY action, in ANY game, any time "most common" doesn't
happen to land on -99.

Fixed in `tapSquares_decision_model.Rmd`: the reference category is now
always `-99` when it's present anywhere in a session's action data
(falls back to most-frequent-real-action only if `-99` never appears at
all, e.g. every player acted every single turn). This makes the
reference-selection logic agree with what the ABM's scoring code already
assumes. Propagated to all four games.

**Action required to actually fix a game already showing this**: the R
notebook has to be re-knit (Step 9's export) to regenerate
`agent_behavior_weights.csv`/`agent_behavior_reference.csv` with the
corrected reference category, then `promote_r_output.sh` re-run to carry
those into `abm/`, before re-testing in NetLogo. Neither of us can verify
this end-to-end without an R interpreter -- still an open item (see
"Known gaps," below: R script never knit-tested).

## CropRaider "plus PA" content merge: missing shapes found and recovered
Following the earlier CropRaider content swap (action 4/defendCrop,
protected areas, fine mechanic -- see the "plus PA" merge, above),
`check_shape_drift.py` found 4 imageName values referenced by the new
content with no matching shape anywhere in `tapSquares_template.nlogox`:
`defendCrop`, `defended`, `fine`, `protected` (a near-match,
`protectedsign`, already existed but under a different name -- turned
out to be unrelated, not a renamed duplicate).

Root cause, confirmed by file timestamps rather than assumed: the
CSVs referencing these shapes were last saved 2026-08-14 18:04-18:05; the
`tapSquares_template_v1.2.nlogox` that shipped alongside them in the
"elephant game plus PA" source folder was saved *later*,
2026-08-17 08:29 -- and that later save is the one missing the shapes.
Best-supported explanation: the shapes were added and tested live in
NetLogo's Shapes Editor in the original Aug 14 session (explaining why
the user's own memory of a working version was correct), but that
session's changes were never written to the copy that ended up in this
source folder -- a later save (the 17th) came from a stale copy without
them and overwrote whatever had the shapes.

Recovered from a version the user located and uploaded
(`tapSquares_template_v1.2-add94905.nlogox`) which DID have all 4 shapes.
That uploaded file was an OLDER base than pipeline_core/v1's current
template on the code side (missing the later unconditional
ownedBy/village/shared? STATE-logging fix) -- confirmed by diffing the
code section before merging, specifically so the older file wasn't
wholesale-adopted and didn't reintroduce an already-fixed bug. Only the
4 `<shape>` blocks were extracted and inserted into the current,
already-reconciled template, in their correct alphabetical position.
Propagated identically to all four games (all five copies now share one
md5 hash again). `check_shape_drift.py` confirms zero drift across all
four games afterward.

## Follow-up: shape fix missed the ABM generator entirely
My first pass only added the 4 shapes to `tapSquares_template.nlogox`
(the human-game file) and reported it fixed -- CropRaider's ABM still
crashed identically. Real oversight: `tapSquares_ABM_generator.nlogox`
is a SEPARATE .nlogox file with its own independently embedded shapes
library. NetLogo files are self-contained -- neither file reads shapes
from the other at runtime -- so fixing one does nothing for the other,
even though they sit right next to each other and it's easy to assume
"the shapes" are one shared thing. Applied the identical 4-shape merge to
`tapSquares_ABM_generator.nlogox`, propagated to all four games.
`check_shape_drift.py` updated to check BOTH files from now on (see
below) specifically so this exact miss can't happen silently again.

## New checker: check_shape_drift.py
Same spirit as `check_patchproperty_drift.py`, applied to a different
class of silent gap: NetLogo does NOT fall back to a default shape for
an `imageName` it doesn't recognize -- `set shape` to an undefined name
is a hard runtime error ("X is not a currently defined shape"), thrown
the first time that specific value is actually drawn. Since that only
happens when a patch/action/turtle actually reaches that particular
state, a missing shape can sit undetected through plenty of real testing
and only surface much later on a board/session combination that finally
exercises it -- exactly what happened with CropRaider's `protected`
shape, confirmed via file timestamps rather than assumed to be a user
testing gap.

Usage: `python3 check_shape_drift.py <path to games/<game>/v1/game>` --
parses every `<shape name="...">` in that game's
`tapSquares_template.nlogox` and cross-checks it against every
`imageName` referenced in `actionList.csv`/`stateList.csv`/
`turtleList.csv`/`scoringFunction.csv`. Run this any time a game's
content changes, before ever opening NetLogo.

## Real bug: R's write_csv() turned a blank sessionList.csv column into the literal text "NA"
Cut the Creep crashed at `update-patch-color`: `Nothing named NA has been
defined`, in `runresult patch_color_property`. Traced to
`sessionList_ABM.csv`: `patch_color_property` was the literal 3-character
string `"NA"`, not blank. Cut the Creep's own `sessionList.csv` leaves
that column genuinely blank on purpose (no property-driven patch
shading, just the flat default color) -- but the R export step's
`export-sessionlist-abm` chunk does `read_csv("sessionList.csv")` (which
reads a blank cell as R's `NA`) then `write_csv(session_list,
"sessionList_ABM.csv")` with readr's default `na = "NA"`, serializing
that NA straight back out as the text "NA". The ABM generator's generic
CSV-driven config loader has no way to tell "the text NA" apart from a
real value someone meant to set, so it dutifully tries to `runresult
"NA"` as a NetLogo expression.

Fixed: `write_csv(session_list, "sessionList_ABM.csv", na = "")` --
keeps a blank cell blank through the whole round-trip. Propagated to all
four games. Checked all four games' already-generated
`sessionList_ABM.csv` for this: only Cut the Creep actually has it right
now (CropRaider and Crouching Tiger both have real, non-blank
patch_color_property values, so they never hit this path; PES hasn't
been knit yet and will get the fix automatically). Cut the Creep needs a
re-knit to pick up the corrected export.

Noted but NOT fixed, no live evidence yet: `agent_behavior_weights.csv`'s
`weight` column could in principle also end up `NA` (a coefficient R
couldn't estimate, e.g. from collinearity) and hit a related but
DIFFERENT failure -- `weight` has to be numeric downstream
(`read-from-string`/`weightVal` in `score-action-for-agent`), so blanking
it via `na=""` wouldn't be the right fix there; it would need real
handling (skip the row, or default to 0) rather than a CSV-serialization
tweak. Left alone since nothing has actually triggered it yet.

## REVERTED: transparencyTurtles removed entirely, not kept as a placeholder
The fix below (adding transparencyTurtles to the ABM generator as an
inert load-safety global) was undone at the user's request once its
"not read anywhere" status was confirmed: they'd rather delete genuinely
dead config than carry a placeholder just to satisfy a generic loader.
Removed: the global from the ABM generator (all four games), the global
from PES's own tapSquares_template.nlogox, and the column from PES's own
sessionList.csv. `check_session_column_drift.py` confirms PES still
checks clean with it gone (52 columns now, all matched). Process note
for future work: check whether something is actually functional before
adding a placeholder for it, rather than assuming "keep it, just make it
load-safe" is the right call by default.

## PES crash: sessionList.csv column with no matching global
PES failed at Setup: `Nothing named TRANSPARENCYTURTLES has been
defined`, inside `set-game-parameters`'s generic column-driven loader.
Root cause confirmed by checking `pes game exmaple/abm/
tapSquares_ABM_standalone_v22.nlogox` (an older, per-game ABM build the
user pointed at): `transparencyTurtles` is a REAL `sessionList.csv`
column, but per that file's own comment, it's "kept for load-safety;
not read anywhere -- per-turtle transparency is driven by
turtleList.csv's transparent? column instead, same as tapSquares." So
this isn't an unfinished feature needing real implementation -- it's an
inert placeholder global that has to exist purely so
`set-game-parameters`'s generic `run "set <column> <value>"` doesn't
crash on that column. The actual transparency mechanism the user
remembered building is the standard `transparent?` column in
`turtleList.csv`, already fully supported by the shared template/ABM
generator (`landDisplays-own`/`displayTurtles-own transparent?`,
`palette:set-transparency` calls in `update-patch-image`).

Fixed: added `transparencyTurtles` to the ABM generator's `globals[]`
block (comment matches the explanation above). Propagated to all four
games -- harmless for the other three, since an unused declared global
does nothing unless a matching sessionList.csv column tries to set it.

## New checker: check_session_column_drift.py
Same bug class as the shape-drift and patchPropertyList-drift checks:
`set-game-parameters` generically does `run "set <column> <value>"` for
EVERY column in a game's `sessionList.csv`, so any column without a
matching global crashes Setup immediately, the first time that game's
session file is ever read -- exactly what happened with PES's
`transparencyTurtles`. `check_session_column_drift.py` cross-checks
every `sessionList.csv` column against: (1) the ABM generator's own
`globals[]` block, (2) widget-backed variables (sliders, the `sessionID`
input) that are deliberately not redeclared there, and (3) the game's
own `game details.nls` `globals[]` block, which NetLogo's `__includes`
merges into the same namespace. (First draft of this script only checked
source (1) and flagged dozens of false positives -- every game-specific
parameter declared in its own `game details.nls`, plus `sessionID` --
before sources (2) and (3) were added; all four games check clean now
that it accounts for all three.)

Usage: `python3 check_session_column_drift.py <path to games/<game>/v1/game>`.

## Known gaps, not yet addressed in this version
- **Brown/uncategorized patches, seen across multiple games, ABM runs
  only.** Traced to two distinct causes, neither a bug in the shared
  ABM generator code (`set-initial-conditions` is unchanged from
  tapSquares itself): (1) CropRaider's initial conditions give full
  coverage but some patches legitimately end up with low/zero
  vegetation and no land-cover turtles, and `stateList.csv` has no
  "bare ground" entry for that case, so it falls through to the raw
  base color instead of a defined image. (2) Cut the Creep's
  `initialConditionList.csv` probabilities only sum to ~0.55, so a
  real fraction of the board can end up matching no condition at all.
  Parked at the user's request -- pick back up either as a shared
  "always render something, never the raw fallback color" safety net
  in the ABM generator, or as a per-game `stateList.csv`/
  `initialConditionList.csv` content fix (probably both).
- No build-time check yet that a game's `patchPropertyList` actually
  covers every custom patches-own variable its own game logic reads/sets
  (beyond the ownership variables, which the template now logs
  unconditionally). Planned as a separate checker script.
- The ABM generator does not yet degrade gracefully when it encounters,
  at runtime, a categorical/ownership level it never saw during model
  fitting (a new agent, an unassigned patch in a game where none were
  unassigned during training, etc.). This is real work still to do on
  the NetLogo side, not solved by the R-script changes above.
- Cut the Creep and Crouching Tiger have no `outcomePlotList.csv` yet
  (CropRaider and PES do) -- needed before stage-3 ABM testing can run
  for those two games.

## 2026-09-29 -- Repo restructure for a new-user-facing layout
Not a functional change -- no tool's behavior changed, only where files
live and how the folders are named. Done ahead of publishing to GitHub,
after the R/ABM Pipeline Guide's "How It Works" box and the lack of any
document routing a new user to the right guide both turned out to be
real, separate points of confusion (see conversation history).

- `pipeline_core/v1/` split into four subfolders matching the actual
  workflow order: `1_build_a_game/`, `2_extract_behavior/`,
  `3_autogenerate_abm/`, and `consistency_checks/` (the three drift
  checkers, since they check consistency *across* the other three
  stages rather than belonging to any one of them). Each subfolder has
  its own short README; `pipeline_core/v1/README.md` explains the data
  flow between them (game content is read directly, unchanged, by both
  stage 2 and stage 3; stage 2's fitted-model output has to be
  explicitly promoted into stage 3 via `promote_r_output.sh`).
- Added `1_build_a_game/game_builder_starter/` -- blank versions (header
  row only, or header + one example row where the format needs it) of
  every core CSV plus a blank `game details.nls`, generated from the
  *current* template, not the older v1.2 blanks previously living in
  the earth-andrew/tapSquares repo (those predate this version's shape
  fixes and would hand a new builder a stale starting point).
- `games/` renamed to `game_to_abm_workflows/`, to make clear on sight
  that each game folder inside it is a complete, working example of
  all three stages together, not just game content. Its own new
  `README.md` explains the `game/`/`abm/`/`r_pipeline/`/
  `synthetic_sessions/` layout. All internal symlinks are relative and
  were unaffected by the rename (verified after the fact).
- Usage comments in `promote_r_output.sh`, `generate_synthetic_sessions.py`,
  and the three checker scripts updated to reference
  `game_to_abm_workflows/` instead of `games/`. Older references inside
  this changelog's earlier, dated entries were left as-is -- they were
  accurate descriptions of the repo at the time they were written.
- Added `guides/tapSquares_Overview.docx`, a one-page routing table
  ("I want to... / go to...") since no single document previously told
  a new user which guide covered what they were trying to do.
