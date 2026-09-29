#!/usr/bin/env python3
"""
Generates synthetic tapSquares session logs for testing Steps 2 (R script)
and 3 (ABM generator) of the pipeline, without needing real playtest data.

Reads each game's own actionList.csv, game details.nls (for
patchPropertyList), and sessionList.csv (for defaults) so nothing about
the game itself is hardcoded here -- only the *scenarios* (which
parameters to vary) are game-agnostic choices made below.

Usage:
  python3 generate_synthetic_sessions.py <path to game_to_abm_workflows/<game>/v1>

Writes files into <path>/synthetic_sessions/ and appends rows to
<path>/synthetic_sessions/MANIFEST.csv describing what each file varies.
"""
import csv
import os
import random
import re
import sys
from datetime import datetime, timedelta

CORE_OWNERSHIP = ["ownedBy", "village", "shared?"]  # logged unconditionally by the core template


def parse_action_ids(path):
    ids = []
    if not os.path.exists(path):
        return [1]
    with open(path, newline="", encoding="utf-8", errors="ignore") as f:
        for row in csv.DictReader(f):
            try:
                ids.append(int(row["actionID"]))
            except (KeyError, ValueError):
                pass
    return sorted(set(ids)) or [1]


def parse_patch_property_list(path):
    if not os.path.exists(path):
        return []
    text = open(path, encoding="utf-8", errors="ignore").read()
    m = re.search(r"patchPropertyList", text)
    if not m:
        return []
    window = text[m.end(): m.end() + 1200]
    # stop at the first line that doesn't look like part of the list literal
    close = re.search(r"\)\s*\n|\]\s*\n", window)
    if close:
        window = window[: close.end()]
    return re.findall(r'"([^"]+)"', window)


def parse_list_valued_props(path):
    # A patches-own variable assigned via "n-values numPlayers [...]" is a
    # real NetLogo list, one entry per player -- not a scalar. The real
    # game logs these as bracketed text (e.g. "[0 4 2]"), which the Rmd's
    # smart_coerce step already knows to detect and exclude from
    # modeling. Synthesizing a plain number for one of these instead
    # (the bug this function exists to avoid) slips a bogus numeric
    # predictor into the fit that crashes the ABM at runtime, since the
    # real patch variable it resolves to is a list, not a number.
    if not os.path.exists(path):
        return set()
    text = open(path, encoding="utf-8", errors="ignore").read()
    return set(re.findall(r"set\s+([A-Za-z_][A-Za-z0-9_\?]*)\s+n-values\s+numPlayers", text))


def parse_boolean_props(game_dir, candidate_props):
    # Naming convention ("?" suffix) is not reliable across games -- e.g.
    # Crouching Tiger's "arable" is a genuine NetLogo boolean (`set arable
    # true` in game details.nls) with no "?". Guessing wrong here means
    # synthesizing a number where the real game has a boolean, which
    # fits a numeric predictor in R that then crashes at ABM runtime
    # multiplying a weight by a live TRUE/FALSE value. Ground truth
    # instead: scan game details.nls and the CSVs' expression columns for
    # a literal "set <prop> true" or "set <prop> false" assignment. Not
    # exhaustive (a boolean only ever set via a computed expression,
    # never a literal, would be missed), but catches real cases like
    # this one that the naming heuristic can't.
    texts = []
    for fname in ("game details.nls", "spatialFunctionList.csv", "nonSpatialFunctionList.csv", "scoringFunction.csv"):
        p = os.path.join(game_dir, fname)
        if os.path.exists(p):
            texts.append(open(p, encoding="utf-8", errors="ignore").read())
    haystack = "\n".join(texts)

    found = set()
    for prop in candidate_props:
        pattern = r"set\s+" + re.escape(prop) + r"\s+(true|false)\b"
        if re.search(pattern, haystack, re.IGNORECASE):
            found.add(prop)
    return found


def parse_session_defaults(path):
    if not os.path.exists(path):
        return 4, 1, 3
    with open(path, newline="", encoding="utf-8", errors="ignore") as f:
        row = next(csv.DictReader(f))
    num_rounds = int(float(row.get("numRounds", 4) or 4))
    num_phases = int(float(row.get("numPhases", 1) or 1))
    village = (row.get("villageMembership") or "1 1 1").split()
    return num_rounds, num_phases, max(1, len(village))


def gen_value(prop, rng, list_valued_props=frozenset(), num_players=1, boolean_props=frozenset()):
    if prop in list_valued_props:
        # Real NetLogo list literal text, one entry per player -- matches
        # the "[0 4 2]" format the real game logs and smart_coerce already
        # knows to leave as text (list-shaped, not a predictor).
        return "[" + " ".join(str(rng.randint(0, 10)) for _ in range(num_players)) + "]"
    if prop.endswith("?") or prop in boolean_props:
        # "?" suffix is tapSquares' naming convention for booleans, but not
        # every game follows it (e.g. Crouching Tiger's "arable" is a real
        # boolean with no "?") -- boolean_props catches those via a literal
        # "set <prop> true/false" scan of the game's own code (see
        # parse_boolean_props). Without this, a boolean gets synthesized as
        # a number, R fits it as a numeric predictor, and the ABM crashes
        # multiplying a weight by a live TRUE/FALSE value at runtime.
        return "true" if rng.random() < 0.5 else "false"
    if prop in ("ownedBy", "village"):
        # 0 = unassigned. Weighted so "unassigned" shows up but isn't dominant.
        return str(rng.choice([0, 0, 1, 2, 3, 3]))
    return str(round(rng.uniform(0, 10), 2))


def fmt_ts(t):
    return t.strftime("%I:%M:%S.") + f"{t.microsecond // 1000:03d}" + t.strftime(" %p %d-%b-%Y")


def generate(game_dir, out_path, num_rounds, num_phases, num_players, nx, ny, seed,
             no_action_rate=0.1, retap_rate=0.3):
    rng = random.Random(seed)
    action_ids = parse_action_ids(os.path.join(game_dir, "actionList.csv"))
    props = parse_patch_property_list(os.path.join(game_dir, "game details.nls"))
    all_props = list(dict.fromkeys(props + CORE_OWNERSHIP))
    list_valued_props = parse_list_valued_props(os.path.join(game_dir, "game details.nls")) & set(all_props)
    boolean_props = parse_boolean_props(game_dir, all_props)
    players = list(range(1, num_players + 1))

    lines = []
    t = datetime(2026, 9, 28, 12, 0, 0)

    def tick(seconds_range=(1, 15)):
        nonlocal t
        t = t + timedelta(seconds=rng.randint(*seconds_range))
        return fmt_ts(t)

    for rnd in range(1, num_rounds + 1):
        for ph in range(1, num_phases + 1):
            lines.append(f"PHASE|phase-{rnd}-{ph}|{tick()}")
            for x in range(nx):
                for y in range(ny):
                    for prop in all_props:
                        val = gen_value(prop, rng, list_valued_props=list_valued_props, num_players=num_players, boolean_props=boolean_props)
                        lines.append(f"STATE|{rnd}|{ph}|{x}|{y}|{prop}|{val}")
            for p in players:
                n_taps = rng.randint(1, 3)
                used_patch = None
                for _ in range(n_taps):
                    if used_patch is not None and rng.random() < retap_rate:
                        x, y = used_patch
                    else:
                        x, y = rng.randrange(nx), rng.randrange(ny)
                        used_patch = (x, y)
                    aid = -99 if rng.random() < no_action_rate else rng.choice(action_ids)
                    lines.append(f"CHOICE|{rnd}|{ph}|{p}|{x}|{y}|{aid}|{tick()}")
                lines.append(f"CONFIRM|{rnd}|{ph}|{p}|{tick()}")
            for p in players:
                cur = rng.randint(0, 20)
                tot = cur + rng.randint(0, 50)
                res = rng.randint(0, 20)
                lines.append(f"SCORE|{rnd}|{ph}|{p}|{cur}|{tot}|{res}")

    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return len(lines)


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 generate_synthetic_sessions.py <path to game_to_abm_workflows/<game>/v1>")
        sys.exit(1)

    game_version_dir = sys.argv[1].rstrip("/")
    game_dir = os.path.join(game_version_dir, "game")
    out_dir = os.path.join(game_version_dir, "synthetic_sessions")
    os.makedirs(out_dir, exist_ok=True)

    base_rounds, base_phases, base_players = parse_session_defaults(os.path.join(game_dir, "sessionList.csv"))

    lv = parse_list_valued_props(os.path.join(game_dir, "game details.nls"))
    if lv:
        print(f"List-valued (per-player) properties detected, synthesized as bracketed lists, not scalars: {sorted(lv)}")

    props_for_bool_scan = parse_patch_property_list(os.path.join(game_dir, "game details.nls"))
    bp = parse_boolean_props(game_dir, list(dict.fromkeys(props_for_bool_scan + CORE_OWNERSHIP)))
    if bp:
        print(f"Boolean properties detected via 'set <prop> true/false' (no '?' naming required), synthesized as true/false: {sorted(bp)}")

    scenarios = [
        dict(name="baseline",        rounds=base_rounds,     players=base_players,          nx=4, ny=4, seed=1, no_action_rate=0.1, retap_rate=0.3),
        dict(name="fewer_players",   rounds=base_rounds,     players=max(2, base_players//2), nx=4, ny=4, seed=2, no_action_rate=0.1, retap_rate=0.3),
        dict(name="more_players",    rounds=base_rounds,     players=base_players + 4,      nx=4, ny=4, seed=3, no_action_rate=0.1, retap_rate=0.3),
        dict(name="more_rounds",     rounds=base_rounds * 3, players=base_players,          nx=4, ny=4, seed=4, no_action_rate=0.1, retap_rate=0.3),
        dict(name="larger_world",    rounds=base_rounds,     players=base_players,          nx=8, ny=8, seed=5, no_action_rate=0.1, retap_rate=0.3),
        dict(name="high_no_action",  rounds=base_rounds,     players=base_players,          nx=4, ny=4, seed=6, no_action_rate=0.4, retap_rate=0.3),
        dict(name="heavy_retapping", rounds=base_rounds,     players=base_players,          nx=4, ny=4, seed=7, no_action_rate=0.1, retap_rate=0.7),
    ]

    manifest_path = os.path.join(out_dir, "MANIFEST.csv")
    with open(manifest_path, "w", newline="") as mf:
        w = csv.writer(mf)
        w.writerow(["session_file", "numRounds", "numPlayers", "grid", "varied_params", "notes"])
        for sc in scenarios:
            fname = f"{sc['name']}.csv"
            out_path = os.path.join(out_dir, fname)
            n_lines = generate(game_dir, out_path, sc["rounds"], base_phases, sc["players"],
                                sc["nx"], sc["ny"], sc["seed"],
                                no_action_rate=sc["no_action_rate"], retap_rate=sc["retap_rate"])
            varied = sc["name"].replace("_", " ")
            w.writerow([fname, sc["rounds"], sc["players"], f"{sc['nx']}x{sc['ny']}", varied,
                        f"{n_lines} log lines, seed={sc['seed']}"])
            print(f"{fname}: {n_lines} lines (rounds={sc['rounds']}, players={sc['players']}, grid={sc['nx']}x{sc['ny']})")

    print(f"\nWrote {len(scenarios)} synthetic session files + MANIFEST.csv to {out_dir}")


if __name__ == "__main__":
    main()
