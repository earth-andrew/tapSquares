#!/usr/bin/env python3
"""Expanded simulated pool: more contrasting player types, three numeric treatments, known ground truth.

Run:  python3 -I simulate_expanded.py [--reps 3] [--out ../simulated_sessions_expanded] [--seed N]

Built on simulate_sessions.py (same surrogate game, same log format).  Differences:
  * 11 scripted player kinds, including the contrasts a field team would expect:
      heavy_waterer      near-water planter, waters every crop (high water-cost limit), never defends   (risk avoided by watering)
      far_from_water     plants as far from water as possible, never waters or defends                  (gambles on rain)
      bulk_defender      near-water planter, defends every crop whatever the cost, never waters         (risk avoided by fencing)
      pa_ignorer         plants only inside protected areas, whatever the fine
      cautious_farmer, undefended_soil, near_water_defender, inland_minimalist, pa_opportunist,
      soil_chaser, seasonal_planter   (as in the first pool)
  * A fixed population of 33 people (3 per kind, IDs like Ana_100).  Each person keeps one kind and one set of
    traits in every session they attend; sessions draw 4, 6 or 8 of them.
  * Treatments (crossed): p_fine 0.05/0.12/0.20  x  defendCost 2/5/8  x  fine 2/4.  Rain profile is fixed (base).
  * Treatment responses are ASSUMED (see simulate_sessions.decide): entering protected land depends on
    p_fine x fine x 6 vs. the person's tolerance (pa_ignorer never responds); defending depends on defendCost vs.
    the person's limit (bulk_defender never responds).
  * player_archetypes.csv is the ground truth the R notebook never sees.
"""
import argparse, csv, itertools, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import simulate_sessions as ss
import cropraider_surrogate as cs

ss.ARCHETYPES.update({
    "heavy_waterer":  ("NW", "0", "W"),
    "far_from_water": ("IN", "0", "0"),
    "bulk_defender":  ("NW", "A", "0"),
    "pa_ignorer":     ("PA", "0", "W"),
})
KINDS = ["cautious_farmer", "undefended_soil", "near_water_defender", "inland_minimalist", "pa_opportunist",
         "soil_chaser", "seasonal_planter", "heavy_waterer", "far_from_water", "bulk_defender", "pa_ignorer"]
TRAIT_OVERRIDES = {
    "heavy_waterer": dict(water_max_cost=14),
    "bulk_defender": dict(defend_max_cost=99.0),
    "pa_ignorer":    dict(pa_tolerance=99.0),
}
P_FINE = (0.05, 0.12, 0.20)
DEFEND_COST = (2, 5, 8)
FINE = (2, 4)
PLAYER_COUNTS = (4, 6, 8)
PER_KIND = 3

FIRST = ["Ana", "Bo", "Chen", "Dara", "Eli", "Fatu", "Gita", "Hugo", "Ines", "Jomo", "Kofi", "Lena", "Musa", "Nia",
         "Omar", "Pia", "Quin", "Rosa", "Sef", "Tavi", "Uma", "Vik", "Wen", "Zane", "Abel", "Bima", "Cato", "Dina",
         "Ewa", "Faris", "Gus", "Hana", "Ivo"]


def make_people(rng):
    people = []
    for k, kind in enumerate(KINDS * PER_KIND):
        i = len(people)
        tr = ss.draw_traits(rng)
        tr.update(TRAIT_OVERRIDES.get(kind, {}))
        people.append(dict(name=f"{FIRST[i]}_{100 + 7 * i:03d}", archetype=kind, traits=tr))
    return people


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3, help="sessions per treatment cell (18 cells)")
    ap.add_argument("--out", default=os.path.join(ss.V2, "simulated_sessions_expanded"))
    ap.add_argument("--seed", type=int, default=20261101)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    props = ss.read_patch_properties()
    template = list(csv.DictReader(open(os.path.join(ss.GAME, "sessionList.csv"), newline="")))[0]
    rng = random.Random(a.seed)
    people = make_people(random.Random(a.seed + 1))

    cells = list(itertools.product(P_FINE, DEFEND_COST, FINE))
    plan, k = [], 0
    for _ in range(a.reps):
        order = cells[:]
        rng.shuffle(order)
        for c in order:
            plan.append((*c, PLAYER_COUNTS[k % len(PLAYER_COUNTS)])); k += 1

    manifest, pool_rows, arch_rows = [], [], []
    for sid, (pf, dc, fine, n_players) in enumerate(plan, start=1):
        seed = rng.randrange(10 ** 9)
        srng = random.Random(seed)
        crew = srng.sample(people, n_players)
        names = [c["name"] for c in crew]
        arch = [c["archetype"] for c in crew]
        traits = [c["traits"] for c in crew]
        P = dict(cs.DEFAULTS); P.update(ss.BASE_OVERRIDES)
        P.update(numPlayers=n_players, p_fine=pf, cost_defend=dc, fine=fine, pRain=ss.RAIN["base"], responsive=True)
        srow = ss.session_rows(template, sid, pf, dc, "base", n_players)
        srow["fine"] = fine
        fname = f"x{sid:03d}_pf{pf:.2f}_dc{dc}_f{fine}_n{n_players}.csv"
        lines, summ, totals, fines = ss.simulate_session(P, arch, traits, seed, srow, props, names=names)
        with open(os.path.join(a.out, fname), "w") as f:
            f.write("\n".join(lines) + "\n")
        manifest.append(dict(session_file=fname, sessionID=sid, p_fine=pf, defendCost=dc, fine=fine,
                             numPlayers=n_players, composition=";".join(f"{x}:{arch.count(x)}" for x in KINDS if arch.count(x)),
                             mean_total_score=round(summ["mean_total_score"], 1), total_fines=summ["total_fines"],
                             share_plant_in_pa=round(summ["share_plant_in_pa"], 3), n_defend=summ["n_defend"], n_lines=len(lines)))
        pool_rows.append(srow)
        for p in range(n_players):
            arch_rows.append(dict(session_file=fname, player=p + 1, person_id=names[p], archetype=arch[p],
                                  total_score=totals[p], fines_paid=fines[p]))
        print(f"{fname}: {len(lines)} lines", file=sys.stderr)

    def dump(path, rows):
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    dump(os.path.join(a.out, "MANIFEST.csv"), manifest)
    dump(os.path.join(a.out, "player_archetypes.csv"), arch_rows)
    dump(os.path.join(a.out, "sessionList_pool.csv"), pool_rows)
    # ground truth by person (one row per person who attended)
    seen = {}
    for r in arch_rows:
        seen.setdefault(r["person_id"], r["archetype"])
    dump(os.path.join(a.out, "ground_truth_persons.csv"), [dict(person_id=p, archetype=t) for p, t in sorted(seen.items())])
    print(f"\nWrote {len(plan)} sessions, {len(seen)} people to {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
