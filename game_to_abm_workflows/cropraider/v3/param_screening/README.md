# Parameter screening for credible dilemmas (cropRaider v3)

Stand-in model, not the game (`../simulation/cropraider_surrogate.py`, now with a r/K "breadth" option). Confirm in NetLogo before trusting.

## What is screened
Scripted players choose **where** (near water / far from water / best soil / protected land) x **breadth** (r: many squares, K: few tended squares) x **defend** (never / always) x **water** (never / when affordable): 32 strategies, each played against two opponent groups, at six treatment corners (`p_fine` 0.04-0.20 x `defendCost` 2/8). A level is flagged *dominated* if one option beats the other in over 80% of matched comparisons (breadth, defend, water), or if a "where" option's best case is under 85% of the overall best. Protected land is only flagged when it is poor at both fine levels, since being poor at high fines is the treatment working.

`dilemma_screen.py` (strategies, payoffs, flags), `search.py` / `refine.py` / `refine2.py` / `grid5.py` (searches over about 190 parameter sets, results in `results/`), `validate.py` (final check, 16 replicates). Run from this folder with `python3 -I`; each call needs under about 170 s here.

## Recommended set: A01 (`candidate_sessionList_A01.csv`, 9 sessions)

| parameter | now | A01 | where it lives |
|---|---|---|---|
| `p_fine` (treatment) | 0.05 / 0.12 / 0.20 | **0.02 / 0.05 / 0.08** | sessionList |
| `defendCost` (treatment) | 5 | **2 / 5 / 8** | sessionList |
| `paSoilBonus` | 0.3 | **0.72** | sessionList |
| `pa_size` | 10 | **11** | sessionList |
| `endowment` | 12 | **10** | sessionList |
| `rainFactorMin` | 0.25 | **0.45** | sessionList |
| `cropR` | 0.4 | **0.35** | sessionList |
| `growCrop` effort | 2 | **4** | `actionList.csv` (effort column) |
| `elephantNeedsTurn` | 1 | **1.5** | `game details.nls` |
| elephant herd probability | 0.04 | **0.05** | `initialConditionList.csv` row 3 |
| `fine`, `pointsPerYield`, `p_defend`, `soilWaterBias`, `harvestCrop` effort | 2, 3, 0.7, 0.5, 2 | unchanged | |

Not applied to the game files; edit them yourself or ask me to.

## What the screen shows for A01 (16 replicates)
- **Protected land is graded by `p_fine`.** Its best case relative to the best strategy: 0.97 at 0.02, 0.67 at 0.05, 0.39 at 0.08, 0.24 at 0.10, and under 0.2 at 0.12 and above. Live at low fines, a poor bet at high ones. Keep `p_fine` at or below about 0.08.
- **Defending flips with `defendCost`.** Always-defend beats never-defend at cost 2 (wins 59-72% of matched comparisons) and mostly loses at cost 8 (wins 34-44%).
- **Near water, far from water and best soil are all within about 15% of each other** (best soil leads); watering wins about half the comparisons.
- **Still dominated:** r beats K (75-100% of matched comparisons, falling as `p_fine` rises). A K player tending 4 squares does not match an r player on 10 in this stand-in. No lever I tried closed the gap without making protected land dominant.
- Raising the plant effort from 2 to 4 helped: sets with the cheap plant cost were dominated by r at every corner. This is from the search, not a controlled test.

## Caveats
8x8 map and 4 players in the stand-in; the real map and group size may differ. Scripted players are crude. `needs` and `herdProb` map to the game by my reading of the code, so check the mapping. The search objective is noisy (8 replicates); only A01 was re-checked at 16.
