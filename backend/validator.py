import re
NUM = re.compile(r"\d[\d,]*\.?\d*")
ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
def nums(t):
    """Figures in a text. ISO dates (2026-03-31) are split into year, month, day so that
    'March 31, 2026' and '2026-03-31' match each other."""
    t, out = t or "", set()
    for y, m, d in ISO.findall(t): out |= {y, str(int(m)), str(int(d))}
    return out | {n.replace(",", "").rstrip(".") for n in NUM.findall(ISO.sub(" ", t))}

def validate_claim(claim, by_id, answer=None):
    """Return (status, note). Every figure in a claim must appear in a cited source
    (verified) or in the employee's own answer (self_reported); otherwise unsupported."""
    cited = [by_id[i] for i in claim.get("artifact_ids", []) if i in by_id]
    if not cited:
        return "unsupported", "no valid source cited"
    src = nums(" ".join(a["title"] + " " + a["excerpt"] for a in cited))
    missing = nums(claim.get("work_done", "") + " " + claim.get("impact", "")) - src
    if not missing:
        return "verified", ""
    if missing <= nums(answer):
        return "self_reported", "figures come from the employee's answer"
    return "unsupported", "figures not found in sources: " + ", ".join(sorted(missing))