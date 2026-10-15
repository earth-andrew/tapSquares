"""Random search for parameter sets with no dominated decisions. Run: python3 -I search.py N_SETS REPS OUT.jsonl"""
import sys, json, random, time
sys.path.insert(0, ".")
import dilemma_screen as d
from multiprocessing import Pool

CORNERS = [dict(p_fine=0.04, cost_defend=2), dict(p_fine=0.04, cost_defend=8), dict(p_fine=0.20, cost_defend=2), dict(p_fine=0.20, cost_defend=8)]
RANGES = dict(pa_soil_bonus=(0.2, 0.9), fine=(1, 4), p_defend=(0.5, 0.95), rainFactorMin=(0.25, 0.6), cropR=(0.25, 0.6),
              herdProb=(0.02, 0.10), needs=(0.5, 2.0), endowment=(8, 16), soil_water_bias=(0.2, 0.8))
INTS = {"fine", "endowment", "k_cap"}
import os
if os.environ.get("ROUND") == "3":   # round 3: protected-area share at the shipped 2 x 10; K must tend (see dilemma_screen)
    RANGES = dict(pa_soil_bonus=(0.5, 0.9), fine=(1, 3), p_defend=(0.6, 0.95), rainFactorMin=(0.3, 0.55), cropR=(0.35, 0.5),
                  herdProb=(0.04, 0.12), needs=(1.0, 2.5), endowment=(9, 13), soil_water_bias=(0.2, 0.6), k_cap=(3, 6))
if os.environ.get("ROUND") == "2":   # round 2: more elephant pressure, so tending a few squares can pay
    RANGES = dict(pa_soil_bonus=(0.3, 0.8), fine=(1, 3), p_defend=(0.7, 0.99), rainFactorMin=(0.3, 0.5), cropR=(0.3, 0.5),
                  herdProb=(0.05, 0.20), needs=(1.0, 3.0), endowment=(8, 13), soil_water_bias=(0.3, 0.7), k_cap=(3, 5))

def score(rows):
    D = 0; flags = []; bests = set()
    for ci, (c, a) in enumerate(rows):
        f = []
        for dim, lv in (("breadth", "r"), ("defend", "0"), ("water", "0")):
            w = a[f"{dim}_win_{lv}"]
            if not 0.2 <= w <= 0.8: f.append(f"{dim}:{'first' if w > .8 else 'second'}")
        for L in d.PREF:
            if a[f"where={L}_best"] < 0.85 * a["best_val"]:
                # protected land may be poor at high fines (that is the treatment working); flag it only if poor at BOTH fine levels
                if L == "PA" and not (rows[(ci + 2) % 4][1]["where=PA_best"] < 0.85 * rows[(ci + 2) % 4][1]["best_val"]): continue
                f.append(f"where={L}")
        D += len(f); flags.append(f); bests.add(a["best"])
    return D - 0.5 * (len(bests) - 1), flags, len(bests)

def run(sets, reps, out):
    with Pool(4) as pool, open(out, "a") as fh:
        for name, over in sets:
            P = dict(d.REAL); P.update(over)
            t = time.time(); rows = d.show(P, reps, CORNERS, pool)
            s, flags, nb = score(rows)
            fh.write(json.dumps(dict(name=name, over=over, score=s, flags=flags, n_best=nb,
                                     best=[list(a["best"]) for _, a in rows], secs=round(time.time() - t))) + "\n"); fh.flush()

if __name__ == "__main__":
    n, reps, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    start, count = int(sys.argv[4]), int(sys.argv[5])
    rng = random.Random(int(os.environ.get("ROUND", "1")) * 11)
    sets = [("current", dict(pa_soil_bonus=0.3))]
    for i in range(n):
        o = {}
        for k, (lo, hi) in RANGES.items():
            v = rng.uniform(lo, hi); o[k] = int(round(v)) if k in INTS else round(v, 2)
        sets.append((f"rand{i:03d}", o))
    run(sets[start:start + count], reps, out)
