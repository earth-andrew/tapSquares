import sys, os, json
sys.path.insert(0, "."); os.environ["ROUND"] = "3"
import dilemma_screen as d, search as S
from multiprocessing import Pool
CAND = {
 "A01": {'pa_soil_bonus': 0.72, 'fine': 2, 'p_defend': 0.71, 'rainFactorMin': 0.46, 'cropR': 0.35, 'herdProb': 0.05, 'needs': 1.57, 'endowment': 10, 'soil_water_bias': 0.49, 'k_cap': 4, 'pa_size': 11, 'cost_plant': 4, 'cost_harvest': 2},
 "B04": {'pa_soil_bonus': 0.73, 'fine': 1, 'p_defend': 0.91, 'rainFactorMin': 0.53, 'cropR': 0.48, 'herdProb': 0.08, 'needs': 1.57, 'endowment': 11, 'soil_water_bias': 0.52, 'k_cap': 6, 'cost_plant': 3, 'cost_harvest': 2},
 "G06": {'pa_soil_bonus': 0.73, 'fine': 1, 'p_defend': 0.91, 'rainFactorMin': 0.53, 'cropR': 0.48, 'needs': 1.57, 'cost_harvest': 2, 'soil_water_bias': 0.52, 'cost_plant': 4, 'k_cap': 6, 'herdProb': 0.08, 'endowment': 10}}
name = sys.argv[1]; reps = int(sys.argv[2])
corn = [dict(p_fine=pf, cost_defend=5) for pf in (0.02, 0.05, 0.08, 0.10)] if len(sys.argv) > 3 else [dict(p_fine=pf, cost_defend=c) for pf in (0.04, 0.12, 0.20) for c in (2, 8)]
with Pool(4) as pool:
    for c in corn:
        P = dict(d.REAL, **CAND[name], **c); a = d.analyse(d.payoffs(P, reps, pool, seed0=9100))
        print(name, c, "best", a["best"], "| where/best", " ".join(f"{L}:{a[f'where={L}_best']/a['best_val']:.2f}" for L in d.PREF),
              "| r>K %.2f  0>A def %.2f  0>W %.2f" % (a["breadth_win_r"], a["defend_win_0"], a["water_win_0"]), flush=True)
