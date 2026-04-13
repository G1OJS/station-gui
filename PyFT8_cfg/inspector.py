import json
import numpy as np
import time

#file = "backup/hearing_me1.json"
#file = "hearing_me.json"
file = "heard_by_me.json"
#file = "heard_by_me_260412_1302.json"

with open(file, "r") as f:
    data = json.load(f)

print(len(data['10m']))

data2 = {}
i = 1
for b in data:
    for c in data[b]:
        if b == "2m":
            info = data[b][c]
            t = time.strftime("%y%m%d %H%M",time.gmtime(info['t']))
            print(i, b, c, t)
            i+=1
        
        #if int(info['t']) > 0:
        #    data2.setdefault(b, {})
        #    data2[b].setdefault(c, {})
        #    data2[b][c] = info

#with open(file, "wb") as f:
#    pickle.dump(data2, f)
