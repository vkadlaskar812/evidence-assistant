import json, sys, urllib.request
src = sys.argv[1] if len(sys.argv) > 1 else "last_state.json"
S = json.load(open(src, encoding="utf-8")) if src.endswith(".json") else json.load(urllib.request.urlopen(src + "/api/state"))
cl = list(S["claims"].values())
if not cl:
    sys.exit("No entries in this file: it was saved before or without a build. Build first, then save.")
arts = {a["id"]: a for a in S["artifacts"]}
large = "PAY-J1" in arts
truth = json.load(open("data/large_truth.json" if large else "data/small_truth.json"))
cited = {i for c in cl for i in c["artifact_ids"]}
print("dataset:", "large" if large else "small", "| sources", len(arts), "| entries", len(cl),
      "| held back", sum(c["status"] == "unsupported" for c in cl))
for kind in sorted(set(truth.values())):
    ids = [i for i, k in truth.items() if k == kind and i in arts]
    print(f"traps {kind}: {sum(i in cited for i in ids)} of {len(ids)} cited (lower is better)")
leak = sum(1 for c in cl if c["status"] != "unsupported" and any(arts.get(i, {}).get("owner") != "Priya" for i in c["artifact_ids"]))
print("non-held-back entries citing a non-Priya source:", leak)
good = [a for a in arts if a not in truth and arts[a].get("owner") == "Priya"]
print("legitimate Priya sources unused (misses):", sum(a not in cited for a in good), "of", len(good))