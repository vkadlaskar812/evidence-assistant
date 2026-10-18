import json, os, re, time
from concurrent.futures import ThreadPoolExecutor

EMP = os.getenv("EMPLOYEE", "Priya")
PROMPT = f"""You prepare the annual promotion case for an employee named {EMP}. Return a JSON list.
Each item: project, work_done (1-2 sentences on what {EMP} personally did), impact (the OUTCOME of the work,
only if a source states it, otherwise an empty string; never restate the activity), artifact_ids (ids you used).
Rules:
- Never invent numbers or facts.
- Every source has an owner field. Credit {EMP} only for sources whose owner is {EMP}. Work owned by anyone else,
  or by "Team", is not hers: skip it, or describe it as a team result beginning "Team result:".
- Team-level or epic-level figures are not her own impact: leave impact empty or begin it with "Team result:".
- Skip open or unfinished items and trivial changes such as typos.
- Counts such as attendees, tests, pages or tickets describe the activity; they are not impact. Leave impact empty
  unless a source states a result (time saved, usage, quality, revenue).
- Combine only closely related records (a ticket with its pull request and design note) into one item per
  deliverable. Never bundle unrelated work into one item. Aim for 3 to 6 items for the evidence below.
Evidence:
"""
CHECK = """You are a fact-checker. You receive a JSON list of items, each with an id, a claim and sources. Using ONLY an
item's sources (title and excerpt both count as source text), decide whether its claim adds anything the sources do not
support. Flag only substantive additions: new facts or numbers, causal links ("by doing X", "which caused"), ownership
("authored", "led", "delivered") that does not match the source's owner field, and team or epic results credited to one
person. Do NOT flag paraphrase or details that appear in a title. Return a JSON list with one object per item:
{"id": the item id, "supported": true or false, "issue": "one short sentence, empty if supported"}.
Items:
"""

def _ask(prompt):
    from google import genai
    key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=key) if key else genai.Client(
        vertexai=True, project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"))
    r = client.models.generate_content(model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), contents=prompt,
        config={"response_mime_type": "application/json", "temperature": 0})
    return json.loads(r.text)

def ask_retry(prompt, ask=None, tries=3, sleep=time.sleep):
    """Retry on failure; for rate limits wait as long as the API asks (it names a delay)."""
    ask = ask or _ask
    for n in range(tries):
        try: return ask(prompt)
        except Exception as e:
            if n == tries - 1: raise
            m = re.search(r"retry in ([\d.]+)s", str(e)) or re.search(r"retryDelay\W+(\d+)s", str(e))
            sleep(min(float(m.group(1)) + 2, 60) if m else 3 * (n + 1))

def extract_claims(arts, ask=None, sleep=time.sleep):
    groups = {}
    for a in arts: groups.setdefault(a["project"], []).append(a)
    failed = []
    def one(item):
        proj, items = item
        try:
            out = ask_retry(PROMPT + json.dumps(items), ask, sleep=sleep)
            good = [c for c in out if isinstance(c, dict) and isinstance(c.get("artifact_ids"), list)] if isinstance(out, list) else []
            for c in good:
                c.setdefault("project", proj); c["work_done"] = c.get("work_done") or ""; c["impact"] = c.get("impact") or ""
            return good
        except Exception as e:
            print(f"extraction failed for {proj}: {e}"); failed.append(proj); return []
    with ThreadPoolExecutor(max_workers=2) as ex:
        claims = [c for r in ex.map(one, groups.items()) for c in r]
    return claims, failed

def check_wording(claims, by_id, ask=None, sleep=time.sleep, batch=12):
    """One request per 12 entries (not one per entry), to stay inside per-minute quotas."""
    items = [{"id": c["id"], "claim": (c["work_done"] + " " + c["impact"]).strip(),
              "sources": [{k: by_id[i].get(k, "") for k in ("id", "owner", "title", "excerpt")}
                          for i in c["artifact_ids"] if i in by_id]} for c in claims]
    verdicts, failed = {}, 0
    for s in range(0, len(items), batch):
        try:
            for v in ask_retry(CHECK + json.dumps(items[s:s + batch]), ask, sleep=sleep):
                if isinstance(v, dict) and "id" in v: verdicts[v["id"]] = v
        except Exception as e:
            print("fact-check failed:", e); failed += 1
    return verdicts, failed