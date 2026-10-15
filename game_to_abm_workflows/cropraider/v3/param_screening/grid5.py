import sys, os, itertools
sys.path.insert(0, "."); os.environ["ROUND"] = "3"
import search as S
B = {'pa_soil_bonus': 0.73, 'fine': 1, 'p_defend': 0.91, 'rainFactorMin': 0.53, 'cropR': 0.48, 'needs': 1.57, 'cost_harvest': 2, 'soil_water_bias': 0.52}
sets = [(f"G{i:02d}", dict(B, cost_plant=cp, k_cap=k, herdProb=h, endowment=e))
        for i, (cp, k, h, e) in enumerate(itertools.product((4,), (4, 6), (0.05, 0.08), (10, 12)))]
start, count = int(sys.argv[2]), int(sys.argv[3])
S.run(sets[start:start + count], int(sys.argv[4]), sys.argv[1])
