#!/usr/bin/env python3
"""
Flags imageName values that a game's CSVs (actionList.csv, stateList.csv,
turtleList.csv, scoringFunction.csv) reference but that aren't actually
defined as a shape in the shared tapSquares_template.nlogox. NetLogo does
NOT silently fall back to a default shape for an unrecognized name -- it's
a hard runtime error ("X is not a currently defined shape"), thrown the
moment update-patch-image (or similar) first tries to `set shape` to it.
This is a static, best-effort check (text search, not a real NetLogo
parser), same spirit as check_patchproperty_drift.py.

Usage:
  python3 check_shape_drift.py <path to game_to_abm_workflows/<game>/v1/game>
"""
import csv
import os
import re
import sys


def parse_shape_names(template_path):
    text = open(template_path, encoding="utf-8", errors="ignore").read()
    # top-level <shape name="..."> entries only (not the nested
    # <shape name="link direction" .../> inside a linkShape block, which
    # isn't a turtle/patch shape at all) -- cheap enough to just collect
    # every one and let false positives in an unrelated namespace be rare.
    return set(m.lower() for m in re.findall(r'<shape name="([^"]+)"', text))


def image_names_from_csv(path, column="imageName"):
    if not os.path.exists(path):
        return set()
    names = set()
    with open(path, newline="", encoding="utf-8", errors="ignore") as f:
        for row in csv.DictReader(f):
            val = (row.get(column) or "").strip()
            if val:
                names.add(val)
    return names


def check_one(label, shapes_path, game_dir):
    if not os.path.exists(shapes_path):
        print(f"[{label}] No file found at {shapes_path} -- skipped.")
        return

    defined_shapes = parse_shape_names(shapes_path)

    referenced = {}  # imageName (lowercase) -> (original casing, set of source files)
    for fname in ("actionList.csv", "stateList.csv", "turtleList.csv", "scoringFunction.csv"):
        for name in image_names_from_csv(os.path.join(game_dir, fname)):
            key = name.lower()
            referenced.setdefault(key, (name, set()))[1].add(fname)

    missing = {k: v for k, v in referenced.items() if k not in defined_shapes}

    print(f"[{label}] {len(referenced)} distinct imageName value(s) referenced; "
          f"{len(defined_shapes)} shape(s) defined in {os.path.basename(shapes_path)}.")

    if missing:
        print(f"[{label}] MISSING SHAPES -- referenced by this game but not defined here "
              "(will crash NetLogo the first time it's actually drawn):")
        for key, (original, sources) in sorted(missing.items()):
            print(f"  - \"{original}\"  (used in: {', '.join(sorted(sources))})")
    else:
        print(f"[{label}] No drift found.")
    print()


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 check_shape_drift.py <path to game_to_abm_workflows/<game>/v1/game>")
        sys.exit(1)

    game_dir = sys.argv[1]

    # TWO separate .nlogox files each carry their OWN embedded shapes
    # library -- NetLogo files are self-contained, neither one reads
    # shapes from the other at runtime, so a shape added to one does NOT
    # automatically cover the other. Confirmed the hard way: a shape fix
    # applied only to tapSquares_template.nlogox (the human-game file)
    # left tapSquares_ABM_generator.nlogox (the ABM, in the sibling abm/
    # folder) still missing the same shapes -- same crash, different file,
    # easy to miss since both files sit right next to each other and
    # "the template" and "the ABM generator" sound like they'd share one
    # shape library but don't. Check BOTH, always.
    template_path = os.path.join(game_dir, "tapSquares_template.nlogox")
    abm_path = os.path.join(os.path.dirname(game_dir), "abm", "tapSquares_ABM_generator.nlogox")

    check_one("tapSquares_template.nlogox (human game)", template_path, game_dir)
    check_one("tapSquares_ABM_generator.nlogox (ABM)", abm_path, game_dir)


if __name__ == "__main__":
    main()
