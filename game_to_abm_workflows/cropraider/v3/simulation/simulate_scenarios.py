#!/usr/bin/env python3
"""Test scenarios with KNOWN ground truth about which treatments matter.

Run:  python3 -I simulate_scenarios.py [--reps 2] [--seed N] [--out ../simulated_scenarios]

Four scenarios, same people and same treatment design, different behavior (9 players per session, the same mix of kinds every time):
  fine_only    players weigh the expected fine (p_fine x fine) when deciding whether to farm protected land;
               the cost of defending is ignored                         -> p_fine should emerge
  cost_only    players weigh the cost of defending; fines are ignored     -> defendCost should emerge, p_fine should not
  both         both responses on                                          -> both should emerge
  neither      no response to fines or cost                               -> p_fine should NOT emerge (false-positive control)
defendCost also has a purely mechanical effect everywhere (a dearer defend action uses more of the turn's effort), so
a weak defendCost signal in fine_only and neither is correct. pa_size (the amount of land protected) varies in every
scenario but changes only how much land is protected, not any player's response: it should NOT emerge.
Treatments (crossed): p_fine 0.02/0.05/0.08  x  defendCost 2/5/8  x  pa_size 8/14   (fine fixed at 2).
Game settings are parameter set A01 (see ../param_screening/README.md). Players' personal fine tolerance spans the
expected-fine range of those p_fine levels, so the assumed response shows up inside the treatment range.
Logs are written gzip-compressed (.csv.gz); the R notebook reads them directly.
"""
import argparse, csv, gzip, itertools, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import simulate_sessions as ss
import simulate_expanded as sx
import cropraider_surrogate as cs

SCENARIOS = {
    "fine_only": dict(fine_responsive=True,  cost_responsive=False),
    "cost_only": dict(fine_responsive=False, cost_responsive=True),
    "both":      dict(fine_responsive=True,  cost_responsive=True),
    "neither":   dict(fine_responsive=False, cost_responsive=False),
}
P_FINE = (0.02, 0.05, 0.08)           # the parameter-screening range (param_screening/README.md)
DEFEND_COST = (2, 5, 8)
PA_SIZE = (8, 14)                     # varied only as a null treatment; the game default is 11
FINE = 2
PA_SOIL_BONUS = 0.72
# Parameter set A01 (param_screening): applied on top of the shared simulator defaults.
A01 = dict(herdProb=0.05, needs=1.5, endowment=10, rainFactorMin=0.45, cropR=0.35, cost_plant=4, cost_harvest=2,
           soil_water_bias=0.5, p_defend=0.7, pointsPerYield=3)
PA_TOLERANCE = (0.2, 1.1)   # personal limit on expected fines over a crop cycle (p_fine x fine x 6, i.e. 0.24-0.96 here)
POPULATION = (["soil_chaser"] * 5 + ["pa_opportunist"] * 4 + ["pa_ignorer"] * 2 + ["cautious_farmer"] * 3 +
              ["near_water_defender"] * 3 + ["bulk_defender"] * 3 + ["heavy_waterer"] * 3 + ["far_from_water"] * 3 +
              ["undefended_soil"] * 3 + ["inland_minimalist"] * 2 + ["seasonal_planter"] * 2)
# Every session has the SAME mix of kinds (one person drawn from each kind's pool), so that treatment
# differences cannot arise by chance from who happened to be in the room.
CREW_KINDS = ["soil_chaser", "soil_chaser", "pa_opportunist", "pa_ignorer", "cautious_farmer",
              "near_water_defender", "bulk_defender", "heavy_waterer", "far_from_water"]
TRUTH = {  # treatment -> expected effect on what the data show. defendCost always has a MECHANICAL effect: a dearer
           # defend action eats more of a player's effort, so fewer defends fit in a turn even for players who ignore cost.
    "fine_only": dict(p_fine="strong", defendCost="weak (budget only)", pa_size="none (land supply only)"),
    "cost_only": dict(p_fine="none",   defendCost="strong",             pa_size="none (land supply only)"),
    "both":      dict(p_fine="strong", defendCost="strong",             pa_size="none (land supply only)"),
    "neither":   dict(p_fine="none",   defendCost="weak (budget only)", pa_size="none (land supply only)"),
}


def make_people(rng):
    people = []
    for i, kind in enumerate(POPULATION):
        tr = ss.draw_traits(rng)
        tr["pa_tolerance"] = rng.uniform(*PA_TOLERANCE)   # spans the expected-fine range so the p_fine response is visible
        tr.update(sx.TRAIT_OVERRIDES.get(kind, {}))
        people.append(dict(name=f"{sx.FIRST[i]}_{100 + 7 * i:03d}", archetype=kind, traits=tr))
    return people


def run_scenario(name, flags, out_root, reps, seed, props, template):
    out = os.path.join(out_root, name)
    os.makedirs(out, exist_ok=True)
    rng = random.Random(seed)
    people = make_people(random.Random(seed + 1))      # same people in every scenario
    cells = list(itertools.product(P_FINE, DEFEND_COST, PA_SIZE))
    plan = []
    for _ in range(reps):
        order = cells[:]; rng.shuffle(order)
        for c in order:
            plan.append((*c, len(CREW_KINDS)))
    manifest, arch_rows, pool_rows, seen = [], [], [], {}
    for sid, (pf, dc, pas, n_players) in enumerate(plan, start=1):
        sseed = rng.randrange(10 ** 9); srng = random.Random(sseed)
        crew, used = [], set()
        for kind in CREW_KINDS:
            pool = [q for q in people if q["archetype"] == kind and q["name"] not in used]
            pick = srng.choice(pool); used.add(pick["name"]); crew.append(pick)
        names = [c["name"] for c in crew]; arch = [c["archetype"] for c in crew]; traits = [c["traits"] for c in crew]
        P = dict(cs.DEFAULTS); P.update(ss.BASE_OVERRIDES); P.update(A01)
        P.update(numPlayers=n_players, p_fine=pf, cost_defend=dc, fine=FINE, pa_size=pas, pa_soil_bonus=PA_SOIL_BONUS,
                 pRain=ss.RAIN["base"], responsive=True, **flags)
        srow = ss.session_rows(template, sid, pf, dc, "base", n_players)
        srow.update(fine=FINE, pa_size=pas, paSoilBonus=PA_SOIL_BONUS, endowment=A01["endowment"], rainFactorMin=A01["rainFactorMin"], cropR=A01["cropR"])
        fname = f"{name[:2]}{sid:03d}_pf{pf:.2f}_dc{dc}_pa{pas}_n{n_players}.csv.gz"
        lines, summ, totals, fines = ss.simulate_session(P, arch, traits, sseed, srow, props, names=names)
        with gzip.open(os.path.join(out, fname), "wt") as f:
            f.write("\n".join(lines) + "\n")
        manifest.append(dict(session_file=fname, sessionID=sid, p_fine=pf, defendCost=dc, pa_size=pas, fine=FINE,
                             numPlayers=n_players, share_plant_in_pa=round(summ["share_plant_in_pa"], 3),
                             n_defend=summ["n_defend"], mean_total_score=round(summ["mean_total_score"], 1)))
        pool_rows.append(srow)
        for p in range(n_players):
            arch_rows.append(dict(session_file=fname, player=p + 1, person_id=names[p], archetype=arch[p]))
            seen.setdefault(names[p], arch[p])
    def dump(path, rows):
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    dump(os.path.join(out, "MANIFEST.csv"), manifest)
    dump(os.path.join(out, "player_archetypes.csv"), arch_rows)
    dump(os.path.join(out, "sessionList_pool.csv"), pool_rows)
    dump(os.path.join(out, "ground_truth_persons.csv"), [dict(person_id=p, archetype=t) for p, t in sorted(seen.items())])
    dump(os.path.join(out, "ground_truth_treatments.csv"),
         [dict(treatment=t, true_effect=v, scenario=name) for t, v in TRUTH[name].items()])
    print(f"{name}: {len(plan)} sessions, {len(seen)} people", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3, help="sessions per treatment cell (18 cells)")
    ap.add_argument("--seed", type=int, default=20261201)
    ap.add_argument("--out", default=os.path.join(ss.V2, "simulated_scenarios"))
    ap.add_argument("--only", default="", help="comma-separated scenario names")
    a = ap.parse_args()
    props = ss.read_patch_properties()
    template = list(csv.DictReader(open(os.path.join(ss.GAME, "sessionList.csv"), newline="")))[0]
    for name, flags in SCENARIOS.items():
        if a.only and name not in a.only.split(","):
            continue
        run_scenario(name, flags, a.out, a.reps, a.seed, props, template)


if __name__ == "__main__":
    main()
