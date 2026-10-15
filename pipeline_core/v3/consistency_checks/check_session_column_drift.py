#!/usr/bin/env python3
"""
Flags sessionList.csv columns that have no matching global declared in
tapSquares_ABM_generator.nlogox. set-game-parameters (in the ABM
generator) generically does `run "set <column> <value>"` for EVERY
column in a game's sessionList.csv row -- a column with no matching
global crashes Setup immediately ("Nothing named <COLUMN> has been
defined"), the very first time that game's session file is read. Same
spirit as check_patchproperty_drift.py / check_shape_drift.py: a static,
best-effort text-search check, not a real NetLogo parser.

Three sources of "already handled, don't flag" globals:
  1. Every name declared inside the ABM generator's globals[] block.
  2. Widget-backed variables (sliders like patches_game/numAgents, the
     sessionID input) -- deliberately NOT redeclared in globals[] (see
     the comment there), but still real globals once the widget exists.
  3. Every name declared inside the game's OWN game details.nls globals[]
     block -- NetLogo's __includes merges those into the same namespace,
     so a game-specific parameter set there (e.g. CropRaider's
     fractionWater) is just as real as one declared in the ABM generator.

Usage:
  python3 check_session_column_drift.py <path to game_to_abm_workflows/<game>/v1/game>
"""
import csv
import os
import re
import sys


def parse_declared_globals(abm_path):
    text = open(abm_path, encoding="utf-8", errors="ignore").read()
    m = re.search(r"globals\s*\[(.*?)\n\]", text, re.S)
    if not m:
        return set()
    body = m.group(1)
    body = re.sub(r";.*", "", body)  # strip ;; comments
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_\?]*", body))


def parse_widget_variables(abm_path):
    # sliders AND inputs are both widget-backed globals, deliberately not
    # redeclared in globals[] (see the comment there) -- sessionID is an
    # <input>, patches_game/numAgents are <slider>s.
    text = open(abm_path, encoding="utf-8", errors="ignore").read()
    names = set(re.findall(r'<slider[^>]*\bvariable="([^"]+)"', text))
    names |= set(re.findall(r'<input[^>]*\bvariable="([^"]+)"', text))
    return names


def parse_game_details_globals(game_dir):
    # game details.nls's own globals[] block merges into the running
    # model's global namespace via NetLogo's __includes -- a column set
    # there (e.g. CropRaider's fractionWater) is just as "declared" as
    # one in the ABM generator itself, so this has to count too or every
    # game-specific parameter false-positives as missing.
    path = os.path.join(game_dir, "game details.nls")
    if not os.path.exists(path):
        return set()
    text = open(path, encoding="utf-8", errors="ignore").read()
    m = re.search(r"globals\s*\[(.*?)\n\]", text, re.S)
    if not m:
        return set()
    body = re.sub(r";.*", "", m.group(1))
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_\?]*", body))


def parse_sessionlist_columns(session_path):
    with open(session_path, newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        header = next(reader)
    return [c.strip() for c in header if c.strip()]


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 check_session_column_drift.py <path to game_to_abm_workflows/<game>/v1/game>")
        sys.exit(1)

    game_dir = sys.argv[1]
    session_path = os.path.join(game_dir, "sessionList.csv")
    abm_path = os.path.join(os.path.dirname(game_dir), "abm", "tapSquares_ABM_generator.nlogox")

    if not os.path.exists(session_path):
        print(f"No sessionList.csv found at {session_path}")
        sys.exit(1)
    if not os.path.exists(abm_path):
        print(f"No tapSquares_ABM_generator.nlogox found at {abm_path}")
        sys.exit(1)

    declared = (parse_declared_globals(abm_path)
                | parse_widget_variables(abm_path)
                | parse_game_details_globals(game_dir))
    columns = parse_sessionlist_columns(session_path)

    missing = [c for c in columns if c not in declared]

    print(f"sessionList.csv has {len(columns)} column(s). "
          f"{len(declared)} global/slider name(s) known to the ABM generator.\n")

    if missing:
        print("MISSING GLOBALS -- sessionList.csv column(s) with no matching global in "
              "tapSquares_ABM_generator.nlogox (will crash Setup the moment the session "
              "file is read):")
        for c in missing:
            print(f"  - \"{c}\"")
    else:
        print("No drift found: every sessionList.csv column has a matching global (or "
              "slider) in the ABM generator.")


if __name__ == "__main__":
    main()
