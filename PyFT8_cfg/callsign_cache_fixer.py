import pickle
with open("callsign_cache.pkl", "rb") as f:
    data = pickle.load(f)

new_data = {}
for d in data:
    if not d.startswith('<'):
        rec = data[d]
        new_data[d] = rec
    else:
        print(d)

with open("callsign_cache.pkl", "wb") as f:
    pickle.dump(new_data, f)
