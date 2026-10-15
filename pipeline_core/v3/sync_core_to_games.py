#!/usr/bin/env python3
"""Keep every game's copy of the shared engine identical to this folder's engine files.

Run from anywhere (needs only Python 3):
  python3 pipeline_core/v3/sync_core_to_games.py --check          report drift, change nothing (exit 1 if any)
  python3 pipeline_core/v3/sync_core_to_games.py                  copy the engine files into every game's v3 folder
  python3 pipeline_core/v3/sync_core_to_games.py --games cropraider,dynamicpes
  python3 pipeline_core/v3/sync_core_to_games.py --reset-widgets  also take the core ABM's interface (default keeps each game's own)
  python3 pipeline_core/v3/sync_core_to_games.py --upgrade GAME   create GAME/v3 from its newest older version, then sync it

The three engine files are real per-game copies (not symlinks):
  1_build_a_game/tapSquares_template.nlogox           -> <game>/v3/game/
  3_autogenerate_abm/tapSquares_ABM_generator.nlogox  -> <game>/v3/abm/
  2_extract_behavior/tapSquares_decision_model.Rmd    -> <game>/v3/r_pipeline/
Edit them HERE, then sync. The ABM's <widgets> and <hubNetClient> blocks are kept from each game's copy, because the R
notebook (Step 10) writes the treatment sliders into them and a game may set its own defaults; --reset-widgets discards them.
Also reports broken symlinks inside each game folder. Game content (CSVs, game details.nls) is never touched.
"""
import argparse, os, re, shutil, sys
import xml.dom.minidom as minidom

CORE = os.path.dirname(os.path.abspath(__file__))
VER = os.path.basename(CORE)                       # "v3"
ROOT = os.path.abspath(os.path.join(CORE, "..", ".."))
GAMES = os.path.join(ROOT, "game_to_abm_workflows")
FILES = [("1_build_a_game/tapSquares_template.nlogox", "game"),
         ("3_autogenerate_abm/tapSquares_ABM_generator.nlogox", "abm"),
         ("2_extract_behavior/tapSquares_decision_model.Rmd", "r_pipeline")]
BLOCKS = [r"<widgets>.*?</widgets>", r"<hubNetClient>.*?</hubNetClient>"]


def read(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def keep_game_blocks(core_text, game_text):
    out = core_text
    for pat in BLOCKS:
        g = re.search(pat, game_text, re.S)
        if g:
            out = re.sub(pat, lambda _m, t=g.group(0): t, out, count=1, flags=re.S)
    return out


def wanted(src, dst, reset):
    text = read(src)
    if src.endswith("ABM_generator.nlogox") and os.path.exists(dst) and not reset:
        text = keep_game_blocks(text, read(dst))
    return text


def sync_game(game_dir, check, reset):
    bad = 0
    for rel, sub in FILES:
        src = os.path.join(CORE, rel); dst = os.path.join(game_dir, sub, os.path.basename(rel))
        text = wanted(src, dst, reset)
        cur = read(dst) if os.path.exists(dst) else None
        if cur == text:
            print(f"  same      {sub}/{os.path.basename(rel)}"); continue
        bad += 1
        if check:
            print(f"  DIFFERS   {sub}/{os.path.basename(rel)}" if cur is not None else f"  MISSING   {sub}/{os.path.basename(rel)}")
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "w", encoding="utf-8", newline="") as f:
                f.write(text)
            print(f"  updated   {sub}/{os.path.basename(rel)}")
        if dst.endswith(".nlogox"):
            try: minidom.parseString(text.encode("utf-8"))
            except Exception as e: print(f"  !! {sub}: not well-formed XML after sync: {e}"); bad += 1
    for sub in ("abm", "r_pipeline"):
        d = os.path.join(game_dir, sub)
        if os.path.isdir(d):
            for n in sorted(os.listdir(d)):
                p = os.path.join(d, n)
                if os.path.islink(p) and not os.path.exists(p):
                    print(f"  !! broken symlink {sub}/{n} -> {os.readlink(p)}"); bad += 1
    return bad


def newest_older(game):
    nums = []
    for n in os.listdir(game):
        m = re.fullmatch(r"v(\d+)", n)
        if m and n != VER and int(m.group(1)) < int(VER[1:]): nums.append(int(m.group(1)))
    return f"v{max(nums)}" if nums else None


def upgrade(name):
    game = os.path.join(GAMES, name)
    if not os.path.isdir(game): sys.exit(f"No such game folder: {game}")
    target = os.path.join(game, VER)
    if os.path.exists(target): sys.exit(f"{target} already exists")
    prev = newest_older(game)
    if not prev: sys.exit(f"{name} has no older version to upgrade from")
    shutil.copytree(os.path.join(game, prev), target, symlinks=True)
    old_promote = os.path.join(target, "promote_r_output.sh")
    if os.path.exists(old_promote): os.remove(old_promote)       # the notebook's Step 10 promotes its own output now
    print(f"Created {name}/{VER} from {name}/{prev}")
    return target


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true"); ap.add_argument("--reset-widgets", action="store_true")
    ap.add_argument("--games", default=""); ap.add_argument("--upgrade", default="")
    a = ap.parse_args()
    if a.upgrade:
        upgrade(a.upgrade); a.games = a.upgrade; a.reset_widgets = True
    names = [n for n in sorted(os.listdir(GAMES)) if os.path.isdir(os.path.join(GAMES, n, VER))]
    if a.games: names = [n for n in names if n in a.games.split(",")]
    total = 0
    for n in names:
        print(f"{n}/{VER}")
        total += sync_game(os.path.join(GAMES, n, VER), a.check, a.reset_widgets)
    print("\n" + ("All game copies match the core." if total == 0 else f"{total} difference(s)."))
    sys.exit(1 if (a.check and total) else 0)


if __name__ == "__main__":
    main()
