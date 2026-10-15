"""Screen parameter sets for DOMINATED decisions (stand-in model, not the game).
Strategy = where (NW near water / IN far from water / SOIL best soil / PA protected area)
         x breadth (r: up to max_crops squares, K: k_cap squares, tended)
         x defend (0 / A always) x water (0 / W when affordable).
Payoff of each strategy is measured against two opponent populations, at each treatment corner.
"""
import sys, os, itertools, math, random, statistics, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "simulation"))
import cropraider_surrogate as cs
from multiprocessing import Pool

PREF = ("NW", "IN", "SOIL", "PA"); BREADTH = ("r", "K"); DEF = ("0", "A"); WAT = ("0", "W")
STRATS = [(p, b, d, w) for p in PREF for b in BREADTH for d in DEF for w in WAT]
BASES = [("NW", "r", "0", "0"), ("SOIL", "K", "A", "W")]
REAL = dict(cs.DEFAULTS, numRounds=3, numPhases=10, pRain=(0.1, 0.1, 0.3, 0.7, 1, 1, 0.7, 0.3, 0.1, 0.1), numPlayers=4,
            endowment=12, pointsPerYield=3, p_defend=0.7, cost_defend=5, fine=2, p_fine=0.1, rainFactorMin=0.25,
            soil_water_bias=0.5, pa_soil_bonus=0.3, herdProb=0.04, needs=1.0, max_crops=10, k_cap=3, water_max_cost=8)

def tup(s): return (s[0] + ("~K" if s[1] == "K" else ""), s[2], s[3])

def _task(a):
    P, s, b, reps, seed0 = a
    out = []
    for r in range(reps):
        sc, fp, _, _ = cs.play(P, [tup(s)] + [tup(b)] * (P["numPlayers"] - 1), seed0 + r)
        out.append(sc[0])
    return (s, b), statistics.fmean(out)

def payoffs(P, reps, pool, seed0=7000):
    jobs = [(P, s, b, reps, seed0) for s in STRATS for b in BASES]
    return dict(pool.map(_task, jobs, chunksize=4))

def analyse(U):
    """U[(s,b)] -> dict of diagnostics for one treatment point."""
    best = max(U.values())
    mean_u = {s: statistics.fmean(U[(s, b)] for b in BASES) for s in STRATS}
    out = {"best": max(mean_u, key=mean_u.get), "best_val": max(mean_u.values())}
    dims = {"where": (0, PREF), "breadth": (1, BREADTH), "defend": (2, DEF), "water": (3, WAT)}
    for name, (k, levels) in dims.items():
        for L in levels:
            vals = [U[(s, b)] for s in STRATS for b in BASES if s[k] == L]
            out[f"{name}={L}_best"] = max(vals)
        if len(levels) == 2:
            a, b2 = levels; wins = n = 0
            for s in STRATS:
                if s[k] != a: continue
                if name == "breadth" and s[2] == "0" and s[3] == "0": continue   # K with nothing to tend leaves effort idle: dominated by construction
                s2 = s[:k] + (b2,) + s[k + 1:]
                for bs in BASES:
                    d = U[(s, bs)] - U[(s2, bs)]; n += 1; wins += d > 0
            out[f"{name}_win_{a}"] = wins / n
    return out

def show(P, reps=12, corners=None, pool=None):
    corners = corners or [dict(p_fine=0.05), dict(p_fine=0.2)]
    rows = []
    for c in corners:
        Q = dict(P); Q.update(c)
        rows.append((c, analyse(payoffs(Q, reps, pool))))
    return rows
