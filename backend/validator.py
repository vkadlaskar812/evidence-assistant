import re
NUM = re.compile(r"(?<![A-Za-z\d\-])\d[\d,]*\.?\d*")
def nums(t): return {n.replace(",", "").rstrip(".") for n in NUM.findall(t or "")}

def validate_claim(claim, by_id, answer=None):
    """Return (status, note). Every figure in a claim must appear in a cited source
    (verified) or in the employee's own answer (self_reported); otherwise unsupported.
    A claim with no figures at all is 'unchecked', because wording is not verified."""
    cited = [by_id[i] for i in claim.get("artifact_ids", []) if i in by_id]
    if not cited:
        return "unsupported", "no valid source cited"
    claim_nums = nums(claim.get("work_done", "") + " " + claim.get("impact", ""))
    if not claim_nums:
        return "unchecked", "no figures to check; wording not verified"
    src = nums(" ".join(a["title"] + " " + a["excerpt"] for a in cited))
    missing = claim_nums - src
    if not missing:
        return "verified", ""
    if missing <= nums(answer):
        return "self_reported", "figures come from the employee's answer"
    return "unsupported", "figures not found in sources: " + ", ".join(sorted(missing))