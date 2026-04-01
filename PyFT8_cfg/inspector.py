import pickle
with open("heard_by_me.pkl", "rb") as f:
    data = pickle.load(f)

import time
tnow = time.time()

HEARING_PANEL_LIFE_MINS = 20
#new_data = {}
#for b in data:
#    if b != '2m':
#        new_data[b] = data[b]
#data = new_data
for b in data:
    print(f"\nBand: {b}")
    band_rpts = data[b]
    print('\n'.join([f"{b} {band_rpts[call]}" for call in band_rpts]))
    print()
    print("Recent")
    calls_now = [call for call in band_rpts if (tnow - band_rpts[call]['t']) < 60*HEARING_PANEL_LIFE_MINS]
    for call in calls_now:
        rpt = band_rpts[call]
        ts = time.strftime("%y%m%d_%H%M%S", time.gmtime(rpt['t']))
        print(f"{b} {ts} {band_rpts[call]}")

with open("heard_by_me.pkl", "wb") as f:
    pickle.dump(data, f)
