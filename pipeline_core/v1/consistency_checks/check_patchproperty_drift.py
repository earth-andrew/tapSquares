#!/usr/bin/env python3
"""
Flags patches-own variables that a game's own logic reads/sets but that
never get logged, because they're missing from patchPropertyList in
game details.nls. A variable missing from patchPropertyList is
invisible to tapSquares_decision_model.Rmd (Step 3's STATE| parse) --
this is a best-effort static check, not a guarantee, since it works off
text search rather than a real NetLogo parser.

ownedBy / village / shared? are never flagged -- the core template logs
those three unconditionally regardless of patchPropertyList (see
tapSquares_template.nlogox, ~line 2210-2220).

Usage:
  python3 check_patchproperty_drift.py <path to game_to_abm_workflows/<game>/v1/game>
"""
import os
import re
import sys

CORE_LOGGED_UNCONDITIONALLY = {"ownedBy", "village", "shared?"}

# Every other core patches-own variable (declared in the shared template
# itself, not game-specific) -- these are plumbing/mechanism variables,
# not the kind of thing a game would need in patchPropertyList to model
# behavior, so they're excluded from the "should this be logged" check
# even though they're real patches-own variables a game's logic can read.
CORE_MECHANISM_VARS = {
    "inGame?", "selected?", "playerAccess", "selectedBy",
    "landChoices", "currentChoice", "currentEffort",
}


def strip_comments(text):
    # NetLogo line comments start with ;; and run to end of line -- strip
    # before token extraction so comment prose ("True when this patch...")
    # doesn't get mistaken for variable declarations.
    return re.sub(r";;.*", "", text)


def parse_patches_own_block(text):
    m = re.search(r"patches-own\s*\[(.*?)\]", text, re.S)
    if not m:
        return []
    body = strip_comments(m.group(1))
    return re.findall(r"[A-Za-z_][A-Za-z0-9_\?]*", body)


def parse_patch_property_list(text):
    m = re.search(r"patchPropertyList", text)
    if not m:
        return []
    window = text[m.end(): m.end() + 1200]
    close = re.search(r"\)\s*\n|\]\s*\n", window)
    if close:
        window = window[: close.end()]
    return re.findall(r'"([^"]+)"', window)


def variable_referenced(var, haystacks):
    # whole-word match, tolerant of the trailing "?" tapSquares booleans use
    pattern = re.escape(var)
    rx = re.compile(r"(?<![A-Za-z0-9_])" + pattern + r"(?![A-Za-z0-9_])")
    for h in haystacks:
        if rx.search(h):
            return True
    return False


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 check_patchproperty_drift.py <path to game_to_abm_workflows/<game>/v1/game>")
        sys.exit(1)

    game_dir = sys.argv[1]
    gd_path = os.path.join(game_dir, "game details.nls")
    if not os.path.exists(gd_path):
        print(f"No 'game details.nls' found at {gd_path}")
        sys.exit(1)

    gd_text = open(gd_path, encoding="utf-8", errors="ignore").read()
    game_specific_vars = [v for v in parse_patches_own_block(gd_text)
                           if v not in CORE_LOGGED_UNCONDITIONALLY and v not in CORE_MECHANISM_VARS]
    patch_property_list = set(parse_patch_property_list(gd_text))

    other_texts = [strip_comments(gd_text)]
    for fname in ("spatialFunctionList.csv", "nonSpatialFunctionList.csv", "scoringFunction.csv"):
        p = os.path.join(game_dir, fname)
        if os.path.exists(p):
            other_texts.append(open(p, encoding="utf-8", errors="ignore").read())

    print(f"game details.nls declares {len(game_specific_vars)} game-specific patches-own variable(s).")
    print(f"patchPropertyList currently logs {len(patch_property_list)} of them by name.\n")

    flagged = []
    for var in game_specific_vars:
        in_list = var in patch_property_list
        used = variable_referenced(var, other_texts)
        if used and not in_list:
            flagged.append(var)

    if flagged:
        print("POSSIBLE DRIFT -- used by game logic but not in patchPropertyList (won't be logged):")
        for v in flagged:
            print(f"  - {v}")
    else:
        print("No drift found: every game-specific patches-own variable referenced in "
              "game details.nls/spatialFunctionList/nonSpatialFunctionList/scoringFunction "
              "is present in patchPropertyList.")

    unused_and_unlisted = [v for v in game_specific_vars
                            if v not in patch_property_list and v not in flagged]
    if unused_and_unlisted:
        print("\nDeclared but neither referenced elsewhere nor logged (probably fine -- "
              "dead/internal-only, but worth a human glance):")
        for v in unused_and_unlisted:
            print(f"  - {v}")


if __name__ == "__main__":
    main()
