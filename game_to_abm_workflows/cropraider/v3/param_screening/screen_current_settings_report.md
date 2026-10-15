# cropRaider parameter screening (surrogate model -- NOT the real game)

Replicates per cell: 8.  Payoffs are mean total points over the game (4 players). Baselines for 'vs' tables: NW-0, NW-A, PA-0.


## cur_pfine0.05

Overrides vs shipped defaults: numRounds=3, numPhases=10, pRain=(0.1, 0.1, 0.3, 0.7, 1, 1, 0.7, 0.3, 0.1, 0.1), endowment=12, pointsPerYield=3, p_defend=0.7, cost_defend=5, fine=2, soil_water_bias=0.5, pa_soil_bonus=0.3, herdProb=0.04, needs=1.0, max_crops=10, water_strats=True, p_fine=0.05

| strategy | all-play-it payoff | fines paid | crop mass lost to elephants | vs NW-0 others | vs NW-A others | vs PA-0 others |
|---|---|---|---|---|---|---|
| NW-0 | 66.8 ± 15.7 | 0.0 | 45% | 60.8 | 78.8 | 104.2 |
| NW-0-W | 71.9 ± 19.1 | 0.0 | 49% | 60.4 | 63.8 | 112.1 |
| NW-A | 75.8 ± 15.9 | 0.0 | 41% | 60.4 | 71.6 | 127.9 |
| NW-A-W | 78.0 ± 18.5 | 0.0 | 45% | 61.9 | 72.0 | 117.4 |
| NW-T | 80.0 ± 17.8 | 0.0 | 40% | 65.2 | 75.8 | 117.0 |
| NW-T-W | 82.4 ± 18.7 | 0.0 | 44% | 62.6 | 74.2 | 136.9 |
| IN-0 | 70.9 ± 16.3 | 0.0 | 45% | 56.2 | 63.0 | 70.1 |
| IN-0-W | 77.0 ± 19.1 | 0.0 | 45% | 51.0 | 61.1 | 77.2 |
| IN-A | 67.9 ± 17.1 | 0.0 | 47% | 49.5 | 57.8 | 79.5 |
| IN-A-W | 84.5 ± 16.7 | 0.0 | 41% | 51.4 | 52.5 | 82.1 |
| IN-T | 67.6 ± 15.3 | 0.0 | 45% | 51.4 | 60.8 | 84.4 |
| IN-T-W | 77.2 ± 13.5 | 0.0 | 41% | 49.5 | 61.9 | 90.8 |
| PA-0 | 16.2 ± 11.2 | 10.2 | 74% | 40.1 | 30.5 | 5.1 |
| PA-0-W | 26.6 ± 14.5 | 9.8 | 72% | 64.1 | 50.0 | 8.5 |
| PA-A | 21.0 ± 13.6 | 11.4 | 69% | 60.5 | 52.9 | 11.9 |
| PA-A-W | 32.8 ± 14.4 | 9.5 | 67% | 76.5 | 67.9 | 17.5 |
| PA-T | 20.6 ± 12.9 | 11.4 | 71% | 74.6 | 47.8 | 10.1 |
| PA-T-W | 32.4 ± 14.0 | 10.2 | 68% | 70.1 | 72.6 | 20.8 |
| SOIL-0 | 69.3 ± 14.6 | 0.0 | 43% | 65.6 | 83.2 | 80.2 |
| SOIL-0-W | 76.7 ± 18.0 | 0.0 | 45% | 80.2 | 70.9 | 107.6 |
| SOIL-A | 67.2 ± 12.9 | 0.0 | 46% | 74.2 | 85.1* | 107.2 |
| SOIL-A-W | 79.2 ± 16.9 | 0.0 | 44% | 82.9 | 84.4 | 122.6 |
| SOIL-T | 72.6 ± 12.1 | 0.0 | 41% | 75.8 | 77.2 | 106.1 |
| SOIL-T-W | 81.7 ± 17.4 | 0.0 | 44% | 83.2* | 79.9 | 137.2* |

(* = best response to that opponent baseline)

- spread of payoffs across strategies (vs NW-0): 0.68 of the mean payoff (63.7)
- gap between best and second-best strategy: 0.01 of the mean
- distinct best responses across the 3 opponent baselines: 2
- externality: NW-0 focal payoff changes by +18.0 when opponents switch from NW-0 to NW-A
- best / worst all-play-it strategy: IN-A-W / PA-0
- (15s)


## cur_pfine0.2

Overrides vs shipped defaults: numRounds=3, numPhases=10, pRain=(0.1, 0.1, 0.3, 0.7, 1, 1, 0.7, 0.3, 0.1, 0.1), endowment=12, pointsPerYield=3, p_defend=0.7, cost_defend=5, fine=2, soil_water_bias=0.5, pa_soil_bonus=0.3, herdProb=0.04, needs=1.0, max_crops=10, water_strats=True, p_fine=0.2

| strategy | all-play-it payoff | fines paid | crop mass lost to elephants | vs NW-0 others | vs NW-A others | vs PA-0 others |
|---|---|---|---|---|---|---|
| NW-0 | 66.8 ± 15.7 | 0.0 | 45% | 60.8 | 78.8 | 104.2 |
| NW-0-W | 71.9 ± 19.1 | 0.0 | 49% | 60.4 | 63.8 | 112.1 |
| NW-A | 75.8 ± 15.9 | 0.0 | 41% | 60.4 | 71.6 | 127.9 |
| NW-A-W | 78.0 ± 18.5 | 0.0 | 45% | 61.9 | 72.0 | 117.4 |
| NW-T | 80.0 ± 17.8 | 0.0 | 40% | 65.2 | 75.8 | 117.0 |
| NW-T-W | 82.4 ± 18.7 | 0.0 | 44% | 62.6 | 74.2 | 136.9 |
| IN-0 | 70.9 ± 16.3 | 0.0 | 45% | 56.2 | 63.0 | 70.1 |
| IN-0-W | 77.0 ± 19.1 | 0.0 | 45% | 51.0 | 61.1 | 77.2 |
| IN-A | 67.9 ± 17.1 | 0.0 | 47% | 49.5 | 57.8 | 79.5 |
| IN-A-W | 84.5 ± 16.7 | 0.0 | 41% | 51.4 | 52.5 | 82.1 |
| IN-T | 67.6 ± 15.3 | 0.0 | 45% | 51.4 | 60.8 | 84.4 |
| IN-T-W | 77.2 ± 13.5 | 0.0 | 41% | 49.5 | 61.9 | 90.8 |
| PA-0 | -12.7 ± 12.6 | 39.1 | 74% | -40.4 | -59.0 | -23.4 |
| PA-0-W | -4.0 ± 16.9 | 40.4 | 72% | -16.1 | -31.8 | -15.5 |
| PA-A | -9.4 ± 15.7 | 41.8 | 69% | -24.5 | -30.6 | -14.6 |
| PA-A-W | 2.3 ± 15.7 | 39.9 | 67% | -8.0 | -13.9 | -6.8 |
| PA-T | -10.8 ± 14.6 | 42.8 | 71% | -12.9 | -39.0 | -15.6 |
| PA-T-W | 2.8 ± 14.8 | 39.8 | 68% | -14.1 | -10.6 | -4.8 |
| SOIL-0 | 69.3 ± 14.6 | 0.0 | 43% | 65.6 | 83.2 | 80.2 |
| SOIL-0-W | 76.7 ± 18.0 | 0.0 | 45% | 80.2 | 70.9 | 107.6 |
| SOIL-A | 67.2 ± 12.9 | 0.0 | 46% | 74.2 | 85.1* | 107.2 |
| SOIL-A-W | 79.2 ± 16.9 | 0.0 | 44% | 82.9 | 84.4 | 122.6 |
| SOIL-T | 72.6 ± 12.1 | 0.0 | 41% | 75.8 | 77.2 | 106.1 |
| SOIL-T-W | 81.7 ± 17.4 | 0.0 | 44% | 83.2* | 79.9 | 137.2* |

(* = best response to that opponent baseline)

- spread of payoffs across strategies (vs NW-0): 2.89 of the mean payoff (42.8)
- gap between best and second-best strategy: 0.01 of the mean
- distinct best responses across the 3 opponent baselines: 2
- externality: NW-0 focal payoff changes by +18.0 when opponents switch from NW-0 to NW-A
- best / worst all-play-it strategy: IN-A-W / PA-0
- (16s)
