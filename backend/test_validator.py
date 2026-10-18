import json
from validator import validate_claim
arts = {a["id"]: a for a in json.load(open("data/demo_data.json"))}
ok = {"work_done": "Added 62 contract tests.", "impact": "", "artifact_ids": ["PR-412"]}
bad = {"work_done": "Added 62 contract tests.", "impact": "Cut defects by 40%", "artifact_ids": ["PR-412"]}
nosrc = {"work_done": "Did things", "impact": "", "artifact_ids": ["NOPE"]}
assert validate_claim(ok, arts)[0] == "verified"
assert validate_claim(bad, arts)[0] == "unsupported"
assert validate_claim(bad, arts, "defects fell 40%")[0] == "self_reported"
assert validate_claim(nosrc, arts)[0] == "unsupported"
dated = {"TRN-2": {"id": "TRN-2", "title": "Course", "excerpt": "Completed on 2026-03-18, before the 2026-03-31 deadline."}}
assert validate_claim({"work_done": "Finished before the March 31, 2026 deadline.", "impact": "", "artifact_ids": ["TRN-2"]}, dated)[0] == "verified"
assert validate_claim({"work_done": "Finished before the April 30, 2026 deadline.", "impact": "", "artifact_ids": ["TRN-2"]}, dated)[0] == "unsupported"
print("validator tests passed")