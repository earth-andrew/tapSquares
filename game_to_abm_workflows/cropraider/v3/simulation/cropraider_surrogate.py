#!/usr/bin/env python3
"""
cropRaider parameter SCREENING surrogate.

*** This is NOT the game. ***  It is a simplified re-implementation of cropRaider's
rules (game/spatialFunctionList.csv, game/nonSpatialFunctionList.csv,
game/game details.nls, game/actionList.csv, game/scoringFunction.csv) used to
shortlist parameter sets cheaply.  Anything it recommends must be confirmed in
the real NetLogo model (see ../param_sweep_kit/ for that).

Main simplifications (all deliberate, all listed so you can judge them):
  * Plants/grass are tracked per patch as (count, mean size), not as individual turtles.
    Elephant bites reduce the patch mean; they don't concentrate on particular plants.
  * An elephant eats the largest-size class within eatRadius, using the true fraction of a
    patch's area inside the radius (turtles are scattered uniformly in a patch).
  * Phase order follows the engine (run-non-spatial-functions, then run-spatial-functions):
    player actions -> elephants move -> elephants feed -> make-rain(pRain[phase]) -> spatial
    functions 0..6 (plant, growth using the NEW rainFactor, harvest, fine, defend).
    Consequence: the `raining?` flag that gates watering at choice time describes the PREVIOUS
    phase's rain draw, while growth uses the CURRENT phase's draw.
  * Scripted players stand in for humans: each plays one fixed (planting preference,
    defend policy, water policy) combination.  They are crude on purpose; the point is
    to see whether DIFFERENT simple strategies pay differently, not to predict people.
  * Players can only harvest/defend their own crops; patches are shared (no ownership),
    and a patch can be acted on by one player per phase.
  * Watering: spatial function 2 now uses (ifelse-value (currentChoice = 2) [1] [rainFactor])
    for crop growth, so a watered crop grows at full (rain) rate that phase.  `water_effect`
    (default True) models that; False reproduces the earlier version where watering did nothing.
"""
import argparse, csv, itertools, math, random, statistics, sys, time

DEFAULTS = dict(
    N=8, numPlayers=4, numRounds=4, numPhases=4, endowment=20,
    fractionWater=0.3, probWaterConnected=0.5, fullVeg=20, fullCrop=20,
    cropR=0.4, vegR=0.4, pRain=(0, 1, 1, 0), rainFactorMin=0.25, pointsPerYield=1,
    pa_count=2, pa_size=10, p_fine=0.1, fine=2, p_defend=0.7,
    herdProb=0.1, herdMin=3, herdMax=9,
    cost_plant=2, cost_harvest=2, cost_defend=5, cost_water_per_dist=2,
    cropMin=0.05, cropMax=0.35, vegMin=0.05, vegMax=0.35,
    sizeInitMin=0.1, sizeInitMax=0.25,
    lookRadius=3, firstCut=3, moveNoise=1.0, eatRadius=1.0, needs=2.0,
    water_effect=True, max_crops=6, ripe_size=0.275, water_max_cost=6,
    # DESIGN LEVERS THAT ARE NOT IN THE SHIPPED GAME (0 = shipped behaviour):
    soil_water_bias=0.0,   # 0-1: blend soil quality toward 'closeness to water' (needs a small setup-soil change)
    pa_soil_bonus=0.0,     # 0-1: add this to soil quality inside protected areas (needs a small change)
)

# ---------------------------------------------------------------- geometry helpers
_frac_cache = {}


def frac_in_radius(dx, dy, r, k=8):
    """Fraction of a unit square (centred at offset (dx,dy) from the elephant) within r."""
    key = (round(dx * 10), round(dy * 10), r)
    v = _frac_cache.get(key)
    if v is None:
        cnt = 0
        for a in range(k):
            for b in range(k):
                px = dx - 0.5 + (a + 0.5) / k
                py = dy - 0.5 + (b + 0.5) / k
                if px * px + py * py <= r * r:
                    cnt += 1
        v = cnt / (k * k)
        _frac_cache[key] = v
    return v


class World:
    def __init__(self, P, rng):
        self.P, self.rng = P, rng
        N = self.N = P["N"]
        self.n = N * N
        self.xy = [(i // N, i % N) for i in range(self.n)]
        self.nb4 = [[j for j in range(self.n) if abs(self.xy[i][0] - self.xy[j][0]) + abs(self.xy[i][1] - self.xy[j][1]) == 1] for i in range(self.n)]
        self.nb8 = [[j for j in range(self.n) if j != i and abs(self.xy[i][0] - self.xy[j][0]) <= 1 and abs(self.xy[i][1] - self.xy[j][1]) <= 1] for i in range(self.n)]
        self.water = [False] * self.n
        self.wlevel = [-99] * self.n
        self.dried = [False] * self.n
        self.prot = [False] * self.n
        self.soil = [0.0] * self.n
        self.cropped = [False] * self.n
        self.owner = [-1] * self.n
        self.defended = [False] * self.n
        self.n_c = [0] * self.n
        self.s_c = [0.0] * self.n
        self.n_g = [0] * self.n
        self.s_g = [0.0] * self.n
        self.mass_eaten_crop = 0.0
        self.mass_grown_crop = 0.0
        self._init_water()
        self._init_soil()
        self._init_pa()
        self._apply_soil_levers()
        self._init_veg_and_elephants()
        self.raining = False
        self.rf = P["rainFactorMin"]
        self.planted_at, self.records, self.abs_phase, self.phase_idx = {}, [], 0, 0
        self.dry_crashes = 0  # times a dry draw found NO live water (the game's `max` of an empty set would error)
        self.make_rain(P["pRain"][-1])  # game: ask one-of turtles [make-rain (last pRain)]

    # --- initialisation, mirroring game details.nls ---
    def _init_water(self):
        P, rng = self.P, self.rng
        target = round(P["fractionWater"] * self.n)
        for _ in range(target):
            found = False
            wat = [i for i in range(self.n) if self.water[i]]
            if rng.random() < P["probWaterConnected"] and wat:
                edges = sorted({j for i in wat for j in self.nb4[i] if not self.water[j]})
                if edges:
                    j = rng.choice(edges)
                    wn = [k for k in self.nb4[j] if self.water[k]]
                    self.wlevel[j] = self.wlevel[rng.choice(wn)] + 1 if wn else 0
                    self.water[j] = True
                    found = True
            if not found:
                land = [i for i in range(self.n) if not self.water[i]]
                if land:
                    j = rng.choice(land)
                    self.water[j] = True
                    self.wlevel[j] = 0

    def _init_soil(self):
        rng = self.rng
        self.soil = [rng.random() for _ in range(self.n)]
        for _ in range(10):
            order = list(range(self.n))
            rng.shuffle(order)
            for i in order:
                m = sum(self.soil[j] for j in self.nb8[i]) / len(self.nb8[i])
                self.soil[i] = m * 0.9 + rng.random() * 0.1 * 0.1
        lo, hi = min(self.soil), max(self.soil)
        self.soil = [(s - lo) / (hi - lo) if hi > lo else 0.5 for s in self.soil]

    def _apply_soil_levers(self):
        P = self.P
        b, pb = P["soil_water_bias"], P["pa_soil_bonus"]
        if b <= 0 and pb <= 0:
            return
        allw = [i for i in range(self.n) if self.water[i]]
        for i in range(self.n):
            d = min(math.dist(self.xy[i], self.xy[j]) for j in allw) if allw else 9
            close = max(0.0, 1 - d / 4.0)
            self.soil[i] = (1 - b) * self.soil[i] + b * close + (pb if self.prot[i] else 0.0)
        lo, hi = min(self.soil), max(self.soil)
        self.soil = [(s - lo) / (hi - lo) if hi > lo else 0.5 for s in self.soil]

    def _init_pa(self):
        P, rng = self.P, self.rng
        for _ in range(P["pa_count"]):
            free = [i for i in range(self.n) if not self.prot[i]]
            if not free:
                break
            start = rng.choice(free)
            self.prot[start] = True
            left = P["pa_size"] - 1
            cand = [j for j in self.nb4[start] if not self.prot[j]]
            while left > 0 and cand:  # NetLogo quirk: neighbors4 is re-evaluated from the newly claimed patch
                j = rng.choice(cand)
                self.prot[j] = True
                left -= 1
                cand = [k for k in self.nb4[j] if not self.prot[k]]

    def _init_veg_and_elephants(self):
        P, rng = self.P, self.rng
        s0 = (P["sizeInitMin"] + P["sizeInitMax"]) / 2
        self.eles = []  # [x, y, matriarch_flag, herd_id]
        herd_id = 0
        for i in range(self.n):
            if self.water[i]:
                continue
            self.n_g[i] = round(self.soil[i] * P["fullVeg"])
            self.s_g[i] = s0
            if rng.random() < P["herdProb"]:
                k = rng.randint(P["herdMin"], P["herdMax"])
                cx, cy = self.xy[i]
                herd = [[cx + rng.uniform(-.5, .5), cy + rng.uniform(-.5, .5), False, herd_id] for _ in range(k)]
                herd[0][2] = True
                herd[0][0], herd[0][1] = cx, cy
                self.eles.extend(herd)
                herd_id += 1

    # --- rain / water ---
    def make_rain(self, p):
        P = self.P
        if self.rng.random() < p:
            self.rf, self.raining = 1.0, True
            self.dried = [False] * self.n
        else:
            self.rf, self.raining = P["rainFactorMin"], False
            live = [i for i in range(self.n) if self.water[i] and not self.dried[i]]
            if not live:
                self.dry_crashes += 1
            if live:
                top = max(self.wlevel[i] for i in live)
                for i in live:
                    if self.wlevel[i] == top:
                        self.dried[i] = True
        live = [i for i in range(self.n) if self.water[i] and not self.dried[i]]
        self.wdist = [(min(math.dist(self.xy[i], self.xy[j]) for j in live) if live else 1e4) for i in range(self.n)]
        allw = [i for i in range(self.n) if self.water[i]]
        self.wdist_any = [(min(math.dist(self.xy[i], self.xy[j]) for j in allw) if allw else 1e4) for i in range(self.n)]

    # --- elephants ---
    def move_elephants(self):
        P, rng = self.P, self.rng
        xy = self.xy
        mats = [e for e in self.eles if e[2]]
        for m in mats:
            near = [i for i in range(self.n) if math.dist(xy[i], (m[0], m[1])) <= P["lookRadius"]]
            food = {i: self.n_c[i] * self.s_c[i] + self.n_g[i] * self.s_g[i] for i in near}
            top = sorted(near, key=lambda i: (-food[i], rng.random()))[:P["firstCut"]]
            keep = list(top)
            for i in top:
                if self.defended[i] and rng.random() < P["p_defend"] and i in keep:
                    keep.remove(i)
            if keep:
                dest = min(keep, key=lambda i: (self.wdist_any[i], rng.random()))
                m[0], m[1] = xy[dest]
        N = self.N
        for e in self.eles:
            if e[2]:
                continue
            m = next(x for x in mats if x[3] == e[3])
            e[0] = min(N - 1, max(0, m[0] + rng.random() * 2 * P["moveNoise"] - 1))
            e[1] = min(N - 1, max(0, m[1] + rng.random() * 2 * P["moveNoise"] - 1))

    def feed_elephants(self):
        P, rng = self.P, self.rng
        R = P["eatRadius"]
        order = list(self.eles)
        rng.shuffle(order)
        for e in order:
            need = P["needs"]
            classes = []
            ci, cj = round(e[0]), round(e[1])
            for i in range(self.n):
                x, y = self.xy[i]
                if abs(x - ci) > 2 or abs(y - cj) > 2:
                    continue
                f = frac_in_radius(x - e[0], y - e[1], R)
                if f <= 0:
                    continue
                if self.n_c[i] > 0 and self.s_c[i] > P["cropMin"]:
                    classes.append([self.s_c[i], i, "c", f * self.n_c[i] * (self.s_c[i] - P["cropMin"])])
                if self.n_g[i] > 0 and self.s_g[i] > P["vegMin"]:
                    classes.append([self.s_g[i], i, "g", f * self.n_g[i] * (self.s_g[i] - P["vegMin"])])
            classes.sort(key=lambda c: -c[0])
            for s, i, kind, avail in classes:
                if need <= 0:
                    break
                bite = min(need, avail)
                if bite <= 0:
                    continue
                need -= bite
                if kind == "c":
                    self.s_c[i] -= bite / self.n_c[i]
                    self.mass_eaten_crop += bite
                else:
                    self.s_g[i] -= bite / self.n_g[i]

    # --- spatial functions (the game's spatialFunctionList.csv, in functionID order) ---
    def spatial(self, plants, harvests, defends, watered, scores, fines_paid, yields):
        P, rng = self.P, self.rng
        s0 = (P["sizeInitMin"] + P["sizeInitMax"]) / 2
        for i, p in plants:  # fn1
            self.planted_at[i] = (self.abs_phase, self.phase_idx)
            self.cropped[i], self.owner[i], self.n_g[i] = True, p, 0
            self.n_c[i] = round(self.soil[i] * P["fullCrop"])
            self.s_c[i] = s0
            self.mass_grown_crop += self.n_c[i] * (s0 - P["cropMin"])  # planted biomass counts as 'available to lose'
        for i in range(self.n):  # fn2, fn3
            if self.cropped[i] and self.n_c[i] > 0:
                rf = 1.0 if (P["water_effect"] and i in watered) else self.rf
                before = self.n_c[i] * (self.s_c[i] - P["cropMin"])
                self.s_c[i] += P["cropR"] * self.s_c[i] * (1 - self.s_c[i] / P["cropMax"]) * rf
                self.mass_grown_crop += self.n_c[i] * (self.s_c[i] - P["cropMin"]) - before
            elif not self.cropped[i] and not self.water[i] and self.n_g[i] > 0:
                self.s_g[i] += P["vegR"] * self.s_g[i] * (1 - self.s_g[i] / P["vegMax"]) * self.rf
        for i, p in harvests:  # fn4
            y = round(self.n_c[i] * (self.s_c[i] - P["cropMin"])) if self.n_c[i] > 0 else 0
            scores[p] += y * P["pointsPerYield"]
            yields[p] += y
            if i in self.planted_at:
                a0, k0 = self.planted_at.pop(i)
                self.records.append((k0, self.abs_phase - a0 + 1, y))
            self.cropped[i], self.owner[i], self.defended[i] = False, -1, False
            self.n_c[i], self.s_c[i] = 0, 0.0
            self.n_g[i], self.s_g[i] = round(self.soil[i] * P["fullVeg"]), s0
        for i in range(self.n):  # fn5
            if self.prot[i] and self.cropped[i] and rng.random() < P["p_fine"]:
                o = self.owner[i]
                scores[o] -= P["fine"]
                fines_paid[o] += P["fine"]
        for i in defends:  # fn6
            self.defended[i] = True

    def herd_near(self, i, r=4):
        return any(e[2] and math.dist(self.xy[i], (e[0], e[1])) <= r for e in self.eles)


# ---------------------------------------------------------------- scripted players
PREFS = ("NW", "IN", "PA", "SOIL")
DEFENDS = ("0", "A", "T")
WATERS = ("0", "W")


def plant_candidates(w, pref, taken):
    free = [i for i in range(w.n) if not w.water[i] and not w.cropped[i] and i not in taken]
    if pref == "NW":
        free = [i for i in free if not w.prot[i]]
        free.sort(key=lambda i: (w.wdist[i], -w.soil[i]))
    elif pref == "IN":
        free = [i for i in free if not w.prot[i]]
        free.sort(key=lambda i: (-w.wdist[i], -w.soil[i]))
    elif pref == "PA":
        free = [i for i in free if w.prot[i]]
        free.sort(key=lambda i: (w.wdist[i], -w.soil[i]))
    elif pref == "SOIL":
        free = [i for i in free if not w.prot[i]]
        free.sort(key=lambda i: -w.soil[i])
    return free


def player_turn(w, p, strat, taken, final_phase, plants, harvests, defends, watered):
    P = w.P
    pref, dpol, wpol = strat
    seasonal = pref.endswith("@S")
    pref = pref.split("@")[0]
    # "~K": a 'K-strategist' who works only k_cap squares and tends them; plain = 'r-strategist' (up to max_crops)
    crop_cap = P.get("k_cap", 3) if pref.endswith("~K") else P["max_crops"]
    pref = pref.split("~")[0]
    budget = P["endowment"]
    own = [i for i in range(w.n) if w.cropped[i] and w.owner[i] == p and i not in taken]
    # 1. harvest what's ripe (everything on the very last phase)
    for i in sorted(own, key=lambda i: -w.s_c[i]):
        if (w.s_c[i] >= P["ripe_size"] or final_phase) and budget >= P["cost_harvest"]:
            harvests.append((i, p)); taken.add(i); budget -= P["cost_harvest"]
    own = [i for i in own if i not in taken]
    # 2. water thirsty crops
    if wpol == "W" and not w.raining:
        for i in own:
            c = round(P["cost_water_per_dist"] * w.wdist[i])
            if c <= P["water_max_cost"] and budget >= c:
                watered.add(i); taken.add(i); budget -= c
        own = [i for i in own if i not in taken]
    # 3. defend
    if dpol != "0":
        for i in own:
            if w.defended[i] or budget < P["cost_defend"]:
                continue
            if dpol == "A" or (dpol == "T" and w.herd_near(i)):
                defends.append(i); taken.add(i); budget -= P["cost_defend"]
    # 4. plant with what's left ('@S' players only plant when the next 3 phases are on average wet enough)
    plant_ok = True
    if seasonal:
        k = P["numPhases"]
        upcoming = [P["pRain"][(w.phase_idx + j) % k] for j in range(3)]
        plant_ok = sum(upcoming) / 3 >= 0.5
    if not final_phase and plant_ok:
        held = sum(1 for i in range(w.n) if w.cropped[i] and w.owner[i] == p)
        for i in plant_candidates(w, pref, taken):
            if budget < P["cost_plant"] or held >= crop_cap:
                break
            plants.append((i, p)); taken.add(i); budget -= P["cost_plant"]; held += 1


LAST_WORLD = None


def play(P, strategies, seed):
    rng = random.Random(seed)
    w = World(P, rng)
    num = P["numPlayers"]
    scores, fines_paid, yields = [0] * num, [0] * num, [0] * num
    for rnd in range(P["numRounds"]):
        for ph in range(1, P["numPhases"] + 1):
            final = rnd == P["numRounds"] - 1 and ph == P["numPhases"]
            w.phase_idx = ph - 1
            w.abs_phase = rnd * P["numPhases"] + ph
            taken, plants, harvests, defends, watered = set(), [], [], [], set()
            order = list(range(num)); rng.shuffle(order)
            for p in order:
                player_turn(w, p, strategies[p], taken, final, plants, harvests, defends, watered)
            # engine order (tapSquares_template: run-non-spatial-functions THEN run-spatial-functions):
            # non-spatial = move-elephants, feed-elephants, make-rain; then spatial functions 0..6.
            w.move_elephants()
            w.feed_elephants()
            w.make_rain(P["pRain"][ph - 1])
            w.spatial(plants, harvests, defends, watered, scores, fines_paid, yields)
    raid = w.mass_eaten_crop / w.mass_grown_crop if w.mass_grown_crop > 0 else 0.0
    global LAST_WORLD
    LAST_WORLD = w
    return scores, fines_paid, yields, raid


# ---------------------------------------------------------------- experiments
def strategies_all(with_water=False):
    return [(a, b, c) for a in PREFS for b in DEFENDS for c in (WATERS if with_water else ("0",))]


def label(s):
    return f"{s[0]}-{s[1]}" + ("" if s[2] == "0" else "-W")


def mean_se(xs):
    m = statistics.fmean(xs)
    se = statistics.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else 0.0
    return m, se


def evaluate(P, reps, seed0, baselines, with_water=False):
    strats = strategies_all(with_water)
    out = {"sym": {}, "vs": {}, "diag": {}}
    sd = seed0
    for s in strats:  # everyone plays s
        vals, fines, raids = [], [], []
        for r in range(reps):
            sc, fp, yl, raid = play(P, [s] * P["numPlayers"], sd + r)
            vals.append(statistics.fmean(sc)); fines.append(statistics.fmean(fp)); raids.append(raid)
        out["sym"][s] = (*mean_se(vals), statistics.fmean(fines), statistics.fmean(raids))
    for b in baselines:  # focal plays s, others play baseline b
        for s in strats:
            vals = []
            for r in range(reps):
                sc, _, _, _ = play(P, [s] + [b] * (P["numPlayers"] - 1), sd + r)
                vals.append(sc[0])
            out["vs"][(s, b)] = mean_se(vals)
    return out


def summarize(P, res, baselines):
    strats = sorted({k[0] for k in res["vs"]}, key=lambda s: (PREFS.index(s[0]), DEFENDS.index(s[1]), s[2]))
    sym = {s: res["sym"][s][0] for s in strats}
    best_resp = {}
    for b in baselines:
        best_resp[b] = max(strats, key=lambda s: res["vs"][(s, b)][0])
    vals0 = [res["vs"][(s, baselines[0])][0] for s in strats]
    mean0 = statistics.fmean(vals0)
    spread = (max(vals0) - min(vals0)) / abs(mean0) if mean0 else float("nan")
    top = sorted(vals0, reverse=True)
    top_gap = (top[0] - top[1]) / abs(mean0) if mean0 else float("nan")
    distinct_br = len({best_resp[b] for b in baselines})
    # externality: focal's payoff when others defend vs not, same focal strategy
    ext = None
    if len(baselines) >= 2:
        f = ("NW", "0", "0")
        if (f, baselines[0]) in res["vs"] and (f, baselines[1]) in res["vs"]:
            ext = res["vs"][(f, baselines[1])][0] - res["vs"][(f, baselines[0])][0]
    return dict(strats=strats, sym=sym, best_resp=best_resp, mean=mean0, spread=spread,
                top_gap=top_gap, distinct_br=distinct_br, ext=ext,
                best_sym=max(strats, key=lambda s: sym[s]), worst_sym=min(strats, key=lambda s: sym[s]))


def write_report(path_md, path_csv, named, reps):
    baselines = [("NW", "0", "0"), ("NW", "A", "0"), ("PA", "0", "0")]
    rows, md = [], []
    md.append("# cropRaider parameter screening (surrogate model -- NOT the real game)\n")
    md.append(f"Replicates per cell: {reps}.  Payoffs are mean total points over the game "
              f"({'; '.join(f'{k}' for k in ['4 players'])}). Baselines for 'vs' tables: "
              + ", ".join(label(b) for b in baselines) + ".\n")
    for name, over in named.items():
        P = dict(DEFAULTS); P.update(over)
        t0 = time.time()
        res = evaluate(P, reps, 1000, baselines, with_water=P.get("water_strats", False))
        S = summarize(P, res, baselines)
        md.append(f"\n## {name}\n")
        md.append("Overrides vs shipped defaults: " + (", ".join(f"{k}={v}" for k, v in over.items()) or "(none)") + "\n")
        md.append("| strategy | all-play-it payoff | fines paid | crop mass lost to elephants | " +
                  " | ".join(f"vs {label(b)} others" for b in baselines) + " |")
        md.append("|---|---|---|---|" + "---|" * len(baselines))
        for s in S["strats"]:
            m, se, fines, raid = res["sym"][s]
            cells = [f"{res['vs'][(s, b)][0]:.1f}" + ("*" if S['best_resp'][b] == s else "") for b in baselines]
            md.append(f"| {label(s)} | {m:.1f} ± {se:.1f} | {fines:.1f} | {raid:.0%} | " + " | ".join(cells) + " |")
            rows.append(dict(set=name, strategy=label(s), sym_payoff=m, sym_se=se, fines=fines, raid_share=raid,
                             **{f"vs_{label(b)}": res["vs"][(s, b)][0] for b in baselines}))
        md.append("\n(* = best response to that opponent baseline)\n")
        md.append(f"- spread of payoffs across strategies (vs {label(baselines[0])}): {S['spread']:.2f} of the mean payoff ({S['mean']:.1f})")
        md.append(f"- gap between best and second-best strategy: {S['top_gap']:.2f} of the mean")
        md.append(f"- distinct best responses across the {len(baselines)} opponent baselines: {S['distinct_br']}")
        if S["ext"] is not None:
            md.append(f"- externality: NW-0 focal payoff changes by {S['ext']:+.1f} when opponents switch from NW-0 to NW-A")
        md.append(f"- best / worst all-play-it strategy: {label(S['best_sym'])} / {label(S['worst_sym'])}")
        md.append(f"- ({time.time()-t0:.0f}s)\n")
        print(f"done: {name}", file=sys.stderr)
    with open(path_md, "w") as f:
        f.write("\n".join(md))
    keys = sorted({k for r in rows for k in r})
    with open(path_csv, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=keys); wr.writeheader(); wr.writerows(rows)


NAMED = {
    "A_shipped_defaults": {},
    "B_param_changes_only": dict(herdProb=0.04, needs=1.0, pointsPerYield=3, p_defend=0.9, cost_defend=3),
    "C_B_plus_design_levers": dict(herdProb=0.04, needs=1.0, pointsPerYield=3, p_defend=0.9, cost_defend=3,
                                   soil_water_bias=0.5, pa_soil_bonus=0.3),
    "D_C_light_monitoring": dict(herdProb=0.04, needs=1.0, pointsPerYield=3, p_defend=0.9, cost_defend=3,
                                 soil_water_bias=0.5, pa_soil_bonus=0.3, fine=1, p_fine=0.05),
    "E_C_heavy_monitoring": dict(herdProb=0.04, needs=1.0, pointsPerYield=3, p_defend=0.9, cost_defend=3,
                                 soil_water_bias=0.5, pa_soil_bonus=0.3, fine=3, p_fine=0.2),
    "G1_recommended_low_monitoring": dict(herdProb=0.04, needs=1.0, pointsPerYield=3, endowment=12, max_crops=10,
                                          soil_water_bias=0.5, pa_soil_bonus=0.3, fine=2, p_fine=0.05),
    "G2_recommended_medium_monitoring": dict(herdProb=0.04, needs=1.0, pointsPerYield=3, endowment=12, max_crops=10,
                                             soil_water_bias=0.5, pa_soil_bonus=0.3, fine=2, p_fine=0.10),
    "G3_recommended_high_monitoring": dict(herdProb=0.04, needs=1.0, pointsPerYield=3, endowment=12, max_crops=10,
                                           soil_water_bias=0.5, pa_soil_bonus=0.3, fine=2, p_fine=0.15),
    "H1_G2_with_watering_pRain_0110": dict(herdProb=0.04, needs=1.0, pointsPerYield=3, endowment=12, max_crops=10,
                                           soil_water_bias=0.5, pa_soil_bonus=0.3, fine=2, p_fine=0.10, water_strats=True),
    "H2_G2_with_watering_pRain_even_0.3": dict(herdProb=0.04, needs=1.0, pointsPerYield=3, endowment=12, max_crops=10,
                                               soil_water_bias=0.5, pa_soil_bonus=0.3, fine=2, p_fine=0.10,
                                               pRain=(0.3, 0.3, 0.3, 0.3), water_strats=True),
    "F_C_with_water_strategies": dict(herdProb=0.04, needs=1.0, pointsPerYield=3, p_defend=0.9, cost_defend=3,
                                      soil_water_bias=0.5, pa_soil_bonus=0.3, water_strats=True),
}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=40)
    ap.add_argument("--out", default="screening_report")
    ap.add_argument("--time-one", action="store_true")
    ap.add_argument("--sets", default="", help="comma-separated names from NAMED (default: all)")
    a = ap.parse_args()
    if a.time_one:
        t = time.time(); r = play(dict(DEFAULTS), [("NW", "0", "0")] * 4, 1); print(r, f"{time.time()-t:.2f}s")
    else:
        chosen = {k: v for k, v in NAMED.items() if not a.sets or k in a.sets.split(",")}
        write_report(a.out + ".md", a.out + ".csv", chosen, a.reps)
