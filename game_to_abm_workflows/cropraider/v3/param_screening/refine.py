"""Local refinement: perturb a promising set. Run: python3 -I refine.py OUT.jsonl START COUNT"""
import sys, json, random, os
sys.path.insert(0, ".")
os.environ["ROUND"] = "3"
import search as S
BASES = {
 "A": {'pa_soil_bonus': 0.64, 'fine': 2, 'p_defend': 0.71, 'rainFactorMin': 0.51, 'cropR': 0.35, 'herdProb': 0.08, 'needs': 1.57, 'endowment': 10, 'soil_water_bias': 0.49, 'k_cap': 4},
 "B": {'pa_soil_bonus': 0.73, 'fine': 1, 'p_defend': 0.91, 'rainFactorMin': 0.55, 'cropR': 0.48, 'herdProb': 0.08, 'needs': 1.57, 'endowment': 11, 'soil_water_bias': 0.52, 'k_cap': 6}}
R2 = dict(S.RANGES, pa_count=(2, 3), pa_size=(8, 12)); R2["pa_soil_bonus"] = (0.5, 1.0); R2["herdProb"] = (0.04, 0.16)
INTS = S.INTS | {"pa_count", "pa_size"}
if __name__ == "__main__":
    out, start, count = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    rng = random.Random(5); sets = []
    for tag, base in BASES.items():
        for i in range(14):
            o = dict(base)
            for k in rng.sample(list(R2), 3):
                lo, hi = R2[k]; cur = o.get(k, (lo + hi) / 2)
                v = min(hi, max(lo, cur + rng.uniform(-0.3, 0.3) * (hi - lo)))
                o[k] = int(round(v)) if k in INTS else round(v, 2)
            sets.append((f"{tag}{i:02d}", o))
    S.run(sets[start:start + count], 8, out)
