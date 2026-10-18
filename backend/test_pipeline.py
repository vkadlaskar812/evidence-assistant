import json, pipeline
arts = [{"id": f"A{i}", "project": "P1" if i < 3 else "P2", "owner": "Priya", "title": "t", "excerpt": "e"} for i in range(6)]
calls = []
def ok(prompt):
    calls.append(prompt)
    if prompt.startswith("You are a fact-checker"):
        items = json.loads(prompt.split("Items:\n")[1]); return [{"id": i["id"], "supported": True, "issue": ""} for i in items]
    return [{"work_done": "did x", "impact": "", "artifact_ids": ["A0"]}]
claims, failed = pipeline.extract_claims(arts, ok, sleep=lambda s: None)
assert len(claims) == 2 and failed == [] and len(calls) == 2
many = [{"id": f"C{i}", "work_done": "w", "impact": "", "artifact_ids": ["A0"]} for i in range(13)]
calls.clear(); v, f = pipeline.check_wording(many, {a["id"]: a for a in arts}, ok, sleep=lambda s: None)
assert len(calls) == 2 and len(v) == 13 and f == 0, (len(calls), len(v), f)
slept, n = [], {"k": 0}
def limited(prompt):
    n["k"] += 1
    if n["k"] == 1: raise RuntimeError("429 RESOURCE_EXHAUSTED Please retry in 36.7s.")
    return [{"ok": 1}]
assert pipeline.ask_retry("p", limited, sleep=slept.append) == [{"ok": 1}] and 38 < slept[0] < 39
def dead(prompt): raise RuntimeError("boom")
claims, failed = pipeline.extract_claims(arts, dead, sleep=lambda s: None)
assert claims == [] and sorted(failed) == ["P1", "P2"]
print("pipeline tests passed")