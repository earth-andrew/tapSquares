"""Round 4: also vary the effort price of planting/harvesting (actionList.csv). python3 -I refine2.py OUT START COUNT"""
import sys, random, os
sys.path.insert(0, "."); os.environ["ROUND"] = "3"
import search as S
BASES = {
 "A": {'pa_soil_bonus': 0.72, 'fine': 2, 'p_defend': 0.71, 'rainFactorMin': 0.46, 'cropR': 0.35, 'herdProb': 0.08, 'needs': 1.57, 'endowment': 10, 'soil_water_bias': 0.49, 'k_cap': 4, 'pa_size': 11},
 "B": {'pa_soil_bonus': 0.73, 'fine': 1, 'p_defend': 0.91, 'rainFactorMin': 0.53, 'cropR': 0.48, 'herdProb': 0.08, 'needs': 1.57, 'endowment': 11, 'soil_water_bias': 0.52, 'k_cap': 6}}
R2 = dict(cost_plant=(2, 5), cost_harvest=(1, 3), pa_soil_bonus=(0.5, 1.0), herdProb=(0.04, 0.16), needs=(1.0, 2.5), endowment=(9, 14), k_cap=(3, 6), fine=(1, 3))
INTS = {"cost_plant", "cost_harvest", "endowment", "k_cap", "fine"}
if __name__ == "__main__":
    out, start, count = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    rng = random.Random(9); sets = []
    for tag, base in BASES.items():
        for i in range(14):
            o = dict(base)
            for k in ["cost_plant"] + rng.sample([k for k in R2 if k != "cost_plant"], 2):
                lo, hi = R2[k]; v = rng.uniform(lo, hi) if k == "cost_plant" else min(hi, max(lo, o.get(k, (lo + hi) / 2) + rng.uniform(-.3, .3) * (hi - lo)))
                o[k] = int(round(v)) if k in INTS else round(v, 2)
            sets.append((f"{tag}{i:02d}", o))
    S.run(sets[start:start + count], 8, out)
