import sys; sys.path.insert(0,'../simulation')
import cropraider_surrogate as cs, time
base=dict(numRounds=3,numPhases=10,pRain=(0.1,0.1,0.3,0.7,1,1,0.7,0.3,0.1,0.1),endowment=12,pointsPerYield=3,p_defend=0.7,cost_defend=5,fine=2,
          soil_water_bias=0.5,pa_soil_bonus=0.3,herdProb=0.04,needs=1.0,max_crops=10,water_strats=True)
named={f"cur_pfine{pf}":dict(base,p_fine=pf) for pf in (0.05,0.20)}
cs.write_report('screen_current_settings_report.md','screen_current_settings_report.csv',named,reps=int(sys.argv[1]))
