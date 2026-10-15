#!/bin/bash
# Promotes a game version's R-pipeline output into its abm/ test folder.
#
# Usage:
#   ./promote_r_output.sh "game_to_abm_workflows/cropraider/v1"
#
# What it does: copies agent_behavior_weights.csv, agent_behavior_reference.csv,
# and sessionList_ABM.csv from <gameversion>/r_pipeline/ into <gameversion>/abm/.
# Nothing in abm/ changes until you run this -- knitting the Rmd alone only
# ever writes into r_pipeline/. This is the deliberate checkpoint: look at
# r_pipeline/'s output first, and only promote it once it looks right.

set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <path to game version folder, e.g. game_to_abm_workflows/cropraider/v1>"
  exit 1
fi

GV="$1"
SRC="$GV/r_pipeline"
DST="$GV/abm"

REQUIRED=("agent_behavior_weights.csv" "agent_behavior_reference.csv" "sessionList_ABM.csv")

for f in "${REQUIRED[@]}"; do
  if [ ! -f "$SRC/$f" ]; then
    echo "Missing $SRC/$f -- knit tapSquares_decision_model.Rmd in $SRC first."
    exit 1
  fi
done

if [ ! -d "$DST" ]; then
  echo "No abm/ folder found at $DST"
  exit 1
fi

for f in "${REQUIRED[@]}"; do
  cp "$SRC/$f" "$DST/$f"
  echo "promoted: $f"
done

# v2: optional informational outputs (copied only if the notebook wrote them)
OPTIONAL=("treatment_report.csv" "agent_behavior_treatment_ranges.csv" "agent_class_shares.csv" "person_classes.csv" "agent_patch_choice_weights.csv")
for f in "${OPTIONAL[@]}"; do
  if [ -f "$SRC/$f" ]; then
    cp "$SRC/$f" "$DST/$f"
    echo "promoted (optional): $f"
  fi
done

# v2: put a widget on the ABM interface for each treatment the fitted behavior responds to
# (slider / switch / chooser). Needs python3; if it is missing, run add_treatment_sliders.py later.
if [ -f "$DST/agent_behavior_treatment_ranges.csv" ] && [ -f "$DST/tapSquares_ABM_generator.nlogox" ]; then
  if command -v python3 >/dev/null 2>&1; then
    python3 "$(cd "$(dirname "$0")" && pwd)/add_treatment_sliders.py" "$GV"
  else
    echo "python3 not found: skipped treatment widgets (run add_treatment_sliders.py later)."
  fi
fi

echo "Done. $DST is now testable against tapSquares_ABM_generator.nlogox in the same folder."
