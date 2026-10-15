#!/usr/bin/env python3
"""
Simulate a pool of cropRaider v2 session logs, in the format tapSquares itself writes, with scripted
players of several kinds, varying number of players, and varying treatments:

    p_fine      probability a farmed protected-area square is fined each phase
    defendCost  effort cost of defending a farm square (a fence subsidy lowers it)
    rain        rainfall regime (per-phase rain probabilities, see RAIN below)

The game itself is replaced by a simplified stand-in (cropraider_surrogate.py -- see its docstring for the
simplifications), so these are *simulated* logs: useful for testing the R pipeline and the ABM hand-off, and
for seeing what a model fitted to strategic play looks like.  They are not human data, and the scripted
players are not the ABM.  Ground truth (who played what) is in player_archetypes.csv; the R model never sees it.

Usage:
    python3 simulate_sessions.py            # writes ../simulated_sessions/
    python3 simulate_sessions.py --reps 2   # 2 sessions per treatment cell instead of the default pool
"""
import argparse, csv, itertools, math, os, random, re, sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cropraider_surrogate as cs

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.dirname(HERE)
GAME = os.path.join(V2, "game")

# ----------------------------------------------------------------------------- design
P_FINE = (0.05, 0.12, 0.20)
DEFEND_COST = (2, 5, 8)           # 2 = subsidised fence, 5 = v2 default, 8 = unsubsidised
RAIN = {                          # per-phase rain probability, 10 phases (cyclic across rounds)
    "dry":  (0.05, 0.05, 0.1, 0.4, 0.7, 0.7, 0.4, 0.1, 0.05, 0.05),
    "base": (0.1, 0.1, 0.3, 0.7, 1.0, 1.0, 0.7, 0.3, 0.1, 0.1),
    "wet":  (0.2, 0.3, 0.6, 0.9, 1.0, 1.0, 0.9, 0.6, 0.3, 0.2),
}
PLAYER_COUNTS = (4, 6, 8)

# scripted player kinds: (planting preference, defend policy, water policy); '@S' = plants only before the rains
ARCHETYPES = {
    "cautious_farmer":     ("SOIL", "A", "W"),
    "undefended_soil":     ("SOIL", "0", "0"),
    "near_water_defender": ("NW", "A", "W"),
    "inland_minimalist":   ("IN", "0", "W"),
    "pa_opportunist":      ("PA", "T", "W"),
    "soil_chaser":         ("SOILANY", "A", "W"),   # farms the best soil anywhere, protected areas included
    "seasonal_planter":    ("SOIL@S", "A", "W"),
}

BASE_OVERRIDES = dict(herdProb=0.04, needs=1.0, pointsPerYield=3, endowment=12, soil_water_bias=0.5,
                      pa_soil_bonus=0.3, fine=2, p_defend=0.7, numRounds=3, numPhases=10)


# ----------------------------------------------------------------------------- formatting
def num(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return str(int(v)) if v == int(v) and abs(v) < 1e15 else repr(v)
    return str(v)


class Clock:
    def __init__(self, rng, start):
        self.rng, self.t = rng, start

    def tick(self, lo=0.4, hi=2.5):
        self.t += timedelta(seconds=self.rng.uniform(lo, hi))
        t = self.t
        return t.strftime("%I:%M:%S.") + f"{t.microsecond // 1000:03d}" + t.strftime(" %p %d-%b-%Y")


def read_patch_properties():
    text = open(os.path.join(GAME, "game details.nls"), encoding="utf-8").read()
    m = re.search(r"set patchPropertyList \(list(.*?)\)\s*\n", text, re.S)
    return re.findall(r'"([^"]+)"', m.group(1))


# ----------------------------------------------------------------------------- the simulated world
class SimWorld(cs.World):
    """Surrogate world plus the bookkeeping needed to write STATE lines."""

    def __init__(self, P, rng):
        super().__init__(P, rng)
        n = self.n
        self.trees = [0 if self.water[i] or rng.random() >= 0.3 else rng.randint(1, 2) for i in range(n)]
        self.veg_log = [0.0 if self.water[i] else self.soil[i] * P["fullVeg"] for i in range(n)]
        self.last_yield = [0] * n
        self.fined = [False] * n
        self.fine_amt = [0] * n
        self.phr = [[0] * P["numPlayers"] for _ in range(n)]   # playerHarvestRound, per patch

    def reset_round_harvest(self):
        self.phr = [[0] * self.P["numPlayers"] for _ in range(self.n)]

    def elephant_counts(self):
        cnt = [0] * self.n
        for e in self.eles:
            x, y = int(math.floor(e[0] + 0.5)), int(math.floor(e[1] + 0.5))
            cnt[x * self.N + y] += 1
        return cnt

    def sim_spatial(self, plants, harvests, defends, watered, scores, fines_paid):
        """The game's spatial functions 0..6, in order, with logging bookkeeping."""
        P, rng = self.P, self.rng
        s0 = (P["sizeInitMin"] + P["sizeInitMax"]) / 2
        n = self.n
        self.last_yield = [0] * n                          # fn0
        self.fined = [False] * n
        self.fine_amt = [0] * n
        for i, p in plants:                                 # fn1
            self.cropped[i], self.owner[i], self.n_g[i] = True, p, 0
            self.n_c[i] = round(self.soil[i] * P["fullCrop"])
            self.s_c[i] = s0
            self.trees[i] = 0
            self.veg_log[i] = 0.0
        for i in range(n):                                  # fn2, fn3
            if self.cropped[i] and self.n_c[i] > 0:
                rf = 1.0 if (P["water_effect"] and i in watered) else self.rf
                self.s_c[i] += P["cropR"] * self.s_c[i] * (1 - self.s_c[i] / P["cropMax"]) * rf
            elif not self.cropped[i] and not self.water[i] and self.n_g[i] > 0:
                self.s_g[i] += P["vegR"] * self.s_g[i] * (1 - self.s_g[i] / P["vegMax"]) * self.rf
        for i, p in harvests:                               # fn4
            y = round(self.n_c[i] * (self.s_c[i] - P["cropMin"])) if self.n_c[i] > 0 else 0
            scores[p] += y * P["pointsPerYield"]
            self.last_yield[i] = y
            self.phr[i][p] += y
            self.cropped[i], self.owner[i], self.defended[i] = False, -1, False
            self.n_c[i], self.s_c[i] = 0, 0.0
            self.n_g[i], self.s_g[i] = round(self.soil[i] * P["fullVeg"]), s0
            self.veg_log[i] = float(self.n_g[i])
        for i in range(n):                                  # fn5
            if self.prot[i] and self.cropped[i] and rng.random() < P["p_fine"]:
                self.fined[i], self.fine_amt[i] = True, P["fine"]
                scores[self.owner[i]] -= P["fine"]
                fines_paid[self.owner[i]] += P["fine"]
        for i in defends:                                   # fn6
            self.defended[i] = True


# ----------------------------------------------------------------------------- scripted players
def valid_actions(w, i):
    """Actions whose flags hold for patch i at the start of the phase (actionList.csv flags)."""
    v = []
    if not w.water[i] and not w.cropped[i]:
        v.append(1)
    if w.cropped[i] and not w.raining:
        v.append(2)
    if w.cropped[i]:
        v.append(3)
    if w.cropped[i] and not w.defended[i]:
        v.append(4)
    return v


def action_cost(w, i, a):
    P = w.P
    return {1: P["cost_plant"], 2: round(P["cost_water_per_dist"] * w.wdist[i]),
            3: P["cost_harvest"], 4: P["cost_defend"]}[a]


def plant_candidates(w, pref, taken, allow_pa):
    if pref == "PA":
        return cs.plant_candidates(w, "PA" if allow_pa else "SOIL", taken)
    if pref == "SOILANY":
        free = [i for i in range(w.n) if not w.water[i] and not w.cropped[i] and i not in taken
                and (allow_pa or not w.prot[i])]
        return sorted(free, key=lambda i: -w.soil[i])
    return cs.plant_candidates(w, pref, taken)


def decide(w, p, strat, tr, taken, final):
    """Which (patch, action) pairs player p takes this phase -- same rules as the screening script, plus
    (when P['responsive']) two treatment responses: a player enters the protected area only if the expected
    fines over a typical crop cycle (p_fine x fine x 6 phases) are within their personal tolerance, and only
    defends if the defend cost is within their personal limit.  These responses are ASSUMED, not estimated."""
    P = w.P
    responsive = P.get("responsive", True)
    fine_resp = P.get("fine_responsive", responsive)     # do players weigh the expected fine?
    cost_resp = P.get("cost_responsive", responsive)     # do players weigh the cost of defending?
    allow_pa = (not fine_resp) or (P["p_fine"] * P["fine"] * 6 <= tr["pa_tolerance"])
    will_defend = (not cost_resp) or (P["cost_defend"] <= tr["defend_max_cost"])
    pref, dpol, wpol = strat
    seasonal = pref.endswith("@S")
    pref = pref.split("@")[0]
    budget = P["endowment"]
    acts = []
    own = [i for i in range(w.n) if w.cropped[i] and w.owner[i] == p and i not in taken]
    for i in sorted(own, key=lambda i: -w.s_c[i]):                       # harvest what is ripe
        if (w.s_c[i] >= tr["ripe_size"] or final) and budget >= P["cost_harvest"]:
            acts.append((i, 3)); taken.add(i); budget -= P["cost_harvest"]
    own = [i for i in own if i not in taken]
    if wpol == "W" and not w.raining:                                     # water
        for i in own:
            c = round(P["cost_water_per_dist"] * w.wdist[i])
            if c <= tr["water_max_cost"] and budget >= c:
                acts.append((i, 2)); taken.add(i); budget -= c
        own = [i for i in own if i not in taken]
    if dpol != "0" and will_defend:                                       # defend
        for i in own:
            if w.defended[i] or budget < P["cost_defend"]:
                continue
            if dpol == "A" or (dpol == "T" and w.herd_near(i)):
                acts.append((i, 4)); taken.add(i); budget -= P["cost_defend"]
    plant_ok = True
    if seasonal:
        k = P["numPhases"]
        upcoming = [P["pRain"][(w.phase_idx + j) % k] for j in range(3)]
        plant_ok = sum(upcoming) / 3 >= 0.5
    if not final and plant_ok:                                            # plant
        held = sum(1 for i in range(w.n) if w.cropped[i] and w.owner[i] == p)
        for i in plant_candidates(w, pref, taken, allow_pa):
            if budget < P["cost_plant"] or held >= tr["max_crops"]:
                break
            acts.append((i, 1)); taken.add(i); budget -= P["cost_plant"]; held += 1
    return acts


def taps_for(w, i, target, budget):
    """The CHOICE values logged while a player taps patch i until `target` shows.  Mirrors
    update-current-choice: the cycle is [-99] + affordable valid actions, starting after -99."""
    cycle = [-99] + [a for a in sorted(valid_actions(w, i)) if action_cost(w, i, a) <= budget]
    if target == -99:                       # cycle all the way round, back to 'do nothing'
        return cycle[1:] + [-99] if len(cycle) > 1 else [-99]
    return cycle[1: cycle.index(target) + 1]


# ----------------------------------------------------------------------------- one session
def prop_value(w, name, i, elephants):
    N = w.N
    table = {
        "ownedBy": lambda: -99, "village": lambda: 0, "shared?": lambda: 0,
        "protected?": lambda: w.prot[i], "water?": lambda: w.water[i], "cropped?": lambda: w.cropped[i],
        "driedUp?": lambda: w.dried[i], "soilQuality": lambda: w.soil[i], "treeCount": lambda: w.trees[i],
        "currentBiomass": lambda: 0, "waterLevel": lambda: w.wlevel[i] if w.water[i] else -99,
        "elephantCount": lambda: elephants[i], "myWaterDistance": lambda: min(w.wdist[i], 10000),
        "harvestYield": lambda: w.last_yield[i],
        "playerHarvestRound": lambda: "[" + " ".join(str(v) for v in w.phr[i]) + "]",
        "fined?": lambda: w.fined[i], "fineAmount": lambda: w.fine_amt[i],
        "cropOwner": lambda: (w.owner[i] + 1) if w.cropped[i] else -99,
        "defended?": lambda: w.defended[i], "cropCount": lambda: w.n_c[i] if w.cropped[i] else 0,
        "vegCount": lambda: w.veg_log[i],
        # v3: the actions allowed on this patch this phase (flags only, before effort), as tapSquares logs landChoices
        "landChoices": lambda: "[" + " ".join(str(v) for v in [-99] + sorted(valid_actions(w, i))) + "]",
    }
    if name not in table:
        raise SystemExit(f"simulate_sessions.py doesn't know how to simulate patch property '{name}'. "
                         f"Add it to prop_value().")
    return table[name]()


def simulate_session(P, archetype_names, traits, seed, header_params, props, names=None):
    rng = random.Random(seed)
    w = SimWorld(P, rng)
    num_players = P["numPlayers"]
    clock = Clock(rng, datetime(2026, 10, 12, 9, 0, 0))
    lines = [f"{k}: {v}" for k, v in header_params.items()]
    lines.append("simulated: TRUE  (cropRaider surrogate -- see simulation/cropraider_surrogate.py)")
    for k, nm in enumerate(names or []):    # v2: PLAYER|number|enteredName|timestamp
        lines.append(f"PLAYER|{k + 1}|{nm}|{clock.tick(1, 2)}")
    lines.append(f"PHASE|beginning-land-use|{clock.tick(1, 5)}")

    all_props = list(dict.fromkeys(["ownedBy", "village", "shared?", "landChoices"] + props))

    def state(rnd, ph):
        el = w.elephant_counts()
        for name in all_props:
            for x in range(w.N):
                for y in range(w.N):
                    i = x * w.N + y
                    lines.append(f"STATE|{rnd}|{ph}|{x}|{y}|{name}|{num(prop_value(w, name, i, el))}")

    strategies = [ARCHETYPES[a] for a in archetype_names]
    scores_total = [0] * num_players
    fines_total = [0] * num_players
    n_noaction = 0
    n_choice = 0
    n_plant = n_plant_pa = n_defend = 0
    state(1, 1)   # NOTE: the real engine logs no STATE for round 1 / phase 1; included here so phase-1 decisions have features
    for rnd in range(1, P["numRounds"] + 1):
        for ph in range(1, P["numPhases"] + 1):
            final = rnd == P["numRounds"] and ph == P["numPhases"]
            w.phase_idx = ph - 1
            if ph == 1:
                w.reset_round_harvest()
            taken, plants, harvests, defends, watered = set(), [], [], [], set()
            order = list(range(num_players)); rng.shuffle(order)
            resources_left = {}
            for p in order:
                tr = traits[p]
                acts = decide(w, p, strategies[p], tr, taken, final)
                budget = P["endowment"]
                events = [("act", i, a) for i, a in acts]
                if rng.random() < tr["browse_prob"]:      # taps a patch, cycles it round to 'do nothing'
                    cand = [i for i in range(w.n) if not w.water[i] and i not in taken and valid_actions(w, i)]
                    if cand:
                        events.append(("cancel", rng.choice(cand), -99))
                if rng.random() < tr["water_tap_prob"]:   # taps a water square
                    wat = [i for i in range(w.n) if w.water[i]]
                    if wat:
                        events.append(("cancel", rng.choice(wat), -99))
                rng.shuffle(events)
                for kind, i, a in events:
                    for v in taps_for(w, i, a, budget):
                        lines.append(f"CHOICE|{rnd}|{ph}|{p + 1}|{i // w.N}|{i % w.N}|{v}|{clock.tick()}")
                        n_choice += 1
                        n_noaction += (v == -99)
                    if kind == "act":
                        budget -= action_cost(w, i, a)
                        if a == 1:
                            plants.append((i, p)); n_plant += 1; n_plant_pa += bool(w.prot[i])
                        elif a == 2: watered.add(i)
                        elif a == 3: harvests.append((i, p))
                        elif a == 4:
                            defends.append(i); n_defend += 1
                resources_left[p] = budget
                lines.append(f"CONFIRM|{rnd}|{ph}|{p + 1}|{clock.tick()}")
            # engine order: non-spatial (elephants move, feed, rain) then spatial functions, then scoring
            w.move_elephants(); w.feed_elephants(); w.make_rain(P["pRain"][ph - 1])
            before = list(scores_total)
            phase_scores = [0] * num_players
            w.sim_spatial(plants, harvests, defends, watered, phase_scores, fines_total)
            for p in range(num_players):
                scores_total[p] += phase_scores[p]
            for p in range(num_players):
                lines.append(f"SCORE|{rnd}|{ph}|{p + 1}|{phase_scores[p]}|{scores_total[p]}|{resources_left[p]}")
            for p in order:
                lines.append(f"CONFIRM|{rnd}|{ph}|{p + 1}|{clock.tick()}")
            if not final:
                nr, nph = (rnd, ph + 1) if ph < P["numPhases"] else (rnd + 1, 1)
                state(nr, nph)
    summary = dict(mean_total_score=sum(scores_total) / num_players, total_fines=sum(fines_total),
                   n_choice_lines=n_choice, share_no_action=(n_noaction / n_choice if n_choice else 0),
                   n_plant=n_plant, share_plant_in_pa=(n_plant_pa / n_plant if n_plant else 0), n_defend=n_defend)
    return lines, summary, scores_total, fines_total


# ----------------------------------------------------------------------------- pool design
POOL_SIZE = 24   # distinct people; each keeps one archetype and one set of traits across every session


def make_people(rng):
    """A fixed population. Entered IDs look like what a field team would type: Name_HHID."""
    first = ["Ana", "Bo", "Chen", "Dara", "Eli", "Fatu", "Gita", "Hugo", "Ines", "Jomo", "Kofi", "Lena",
             "Musa", "Nia", "Omar", "Pia", "Quin", "Rosa", "Sef", "Tavi", "Uma", "Vik", "Wen", "Zane"]
    names = [f"{first[i]}_{100 + 7 * i:03d}" for i in range(POOL_SIZE)]
    kinds = list(ARCHETYPES)
    return [dict(name=names[i], archetype=kinds[i % len(kinds)], traits=draw_traits(rng)) for i in range(POOL_SIZE)]


def draw_composition(rng, n):
    names = list(ARCHETYPES)
    for _ in range(50):
        w = [rng.gammavariate(1.0, 1.0) for _ in names]
        picks = rng.choices(names, weights=w, k=n)
        if n < 4 or len(set(picks)) >= 2:
            return picks
    return picks


def draw_traits(rng):
    return dict(ripe_size=rng.uniform(0.25, 0.30), max_crops=rng.randint(4, 10), water_max_cost=rng.randint(4, 8),
                browse_prob=rng.uniform(0.02, 0.12), water_tap_prob=rng.uniform(0.0, 0.08),
                pa_tolerance=rng.uniform(0.3, 3.0), defend_max_cost=rng.uniform(2.0, 9.0))


def session_rows(game_row_template, sid, p_fine, defend_cost, rain, n_players):
    r = dict(game_row_template)
    r.update(sessionID=sid, p_fine=p_fine, defendCost=defend_cost, pRain=" ".join(str(x) for x in RAIN[rain]),
             villageMembership=" ".join(str((k % 2) + 1) for k in range(n_players)))
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=1, help="sessions per treatment cell (27 cells)")
    ap.add_argument("--base-rain-extra", type=int, default=1, help="extra sessions per base-rain cell (9 cells)")
    ap.add_argument("--out", default=os.path.join(V2, "simulated_sessions"))
    ap.add_argument("--seed", type=int, default=20261012)
    ap.add_argument("--fixed-strategies", action="store_true",
                    help="players ignore the treatments (no fine/cost responses); default is responsive")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    props = read_patch_properties()
    game_rows = list(csv.DictReader(open(os.path.join(GAME, "sessionList.csv"), newline="")))
    template = game_rows[0]
    rng = random.Random(a.seed)
    people = make_people(random.Random(a.seed + 1))

    cells = list(itertools.product(P_FINE, DEFEND_COST, RAIN))
    plan = []   # (p_fine, defend_cost, rain, n_players)
    k = 0
    for r in range(a.reps):
        for (pf, dc, rain) in cells:
            plan.append((pf, dc, rain, PLAYER_COUNTS[k % len(PLAYER_COUNTS)])); k += 1
    for r in range(a.base_rain_extra):
        for (pf, dc, rain) in cells:
            if rain == "base":
                plan.append((pf, dc, rain, PLAYER_COUNTS[(k + 1) % len(PLAYER_COUNTS)])); k += 1

    manifest, pool_rows, arch_rows = [], [], []
    for sid, (pf, dc, rain, n_players) in enumerate(plan, start=1):
        seed = rng.randrange(10 ** 9)
        srng = random.Random(seed)
        crew = srng.sample(people, n_players)          # who turned up for this session
        names = [c["name"] for c in crew]
        arch = [c["archetype"] for c in crew]
        traits = [c["traits"] for c in crew]
        P = dict(cs.DEFAULTS); P.update(BASE_OVERRIDES)
        P.update(numPlayers=n_players, p_fine=pf, cost_defend=dc, pRain=RAIN[rain],
                 responsive=not a.fixed_strategies)
        srow = session_rows(template, sid, pf, dc, rain, n_players)
        fname = f"sim{sid:03d}_pf{pf:.2f}_dc{dc}_{rain}_n{n_players}.csv"
        lines, summ, totals, fines = simulate_session(P, arch, traits, seed, srow, props, names=names)
        with open(os.path.join(a.out, fname), "w") as f:
            f.write("\n".join(lines) + "\n")
        comp = ";".join(f"{k}:{arch.count(k)}" for k in ARCHETYPES if arch.count(k))
        manifest.append(dict(session_file=fname, sessionID=sid, p_fine=pf, defendCost=dc, rain=rain,
                             numPlayers=n_players, numRounds=P["numRounds"], numPhases=P["numPhases"],
                             composition=comp, seed=seed, mean_total_score=round(summ["mean_total_score"], 1),
                             total_fines=summ["total_fines"], share_no_action=round(summ["share_no_action"], 3),
                             n_plant=summ["n_plant"], share_plant_in_pa=round(summ["share_plant_in_pa"], 3),
                             n_defend=summ["n_defend"],
                             n_lines=len(lines)))
        pool_rows.append(srow)
        for p in range(n_players):
            arch_rows.append(dict(session_file=fname, player=p + 1, person_id=names[p], archetype=arch[p],
                                  plant_pref=ARCHETYPES[arch[p]][0], defend_policy=ARCHETYPES[arch[p]][1],
                                  water_policy=ARCHETYPES[arch[p]][2], total_score=totals[p], fines_paid=fines[p],
                                  **{f"trait_{k}": round(v, 3) if isinstance(v, float) else v for k, v in traits[p].items()}))
        print(f"{fname}: {len(lines)} lines, mean score {summ['mean_total_score']:.1f}, {comp}", file=sys.stderr)

    def dump(path, rows):
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    dump(os.path.join(a.out, "MANIFEST.csv"), manifest)
    dump(os.path.join(a.out, "player_archetypes.csv"), arch_rows)
    dump(os.path.join(a.out, "sessionList_pool.csv"), pool_rows)
    print(f"\nWrote {len(plan)} sessions to {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
