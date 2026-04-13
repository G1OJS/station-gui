import json, pickle
import numpy as np
import time

file = "hearing_me"
#file = "heard_by_me"

data2 = {}

with open(file + '.json', "r") as f:
    data = json.load(f)

i = 1
for b in data:
    for c in data[b]:
        data2.setdefault(b,{})
        data2[b][c] = data[b][c] 
        if b == "20m":
            info = data[b][c]
            print(i, b, c, info)
            i+=1

with open(file + '.pkl', "rb") as f:
    data = pickle.load(f)

for b in data:
    for c in data[b]:
        data2.setdefault(b,{})
        data2[b][c] = data[b][c] 
        if b == "20m":
            info = data[b][c]
            print(i, b, c, info)
            i+=1

        
        #if int(info['t']) > 0:
        #    data2.setdefault(b, {})
        #    data2[b].setdefault(c, {})
        #    data2[b][c] = info

with open(file+'2.json', "w") as f:
    json.dump(data2, f)
