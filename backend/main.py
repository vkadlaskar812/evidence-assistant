import csv, io, json, os, re
from pathlib import Path
from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from validator import validate_claim
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

BASE = Path(__file__).parent
app = FastAPI()
STATE = {"artifacts": json.loads((BASE / "data/demo_data.json").read_text()), "claims": {}, "answers": {}}

PROMPT = """You prepare an employee's annual promotion case from evidence. Return a JSON list.
Each item: project, work_done (1-2 sentences on what the employee did), impact (a measurable
result ONLY if stated in the evidence, otherwise empty string), artifact_ids (ids you used).
Never invent numbers or facts. One item per distinct contribution. Evidence:\n"""

def persist():  # single-document write, as recommended for Firestore
    if os.getenv("USE_FIRESTORE") == "1":
        from google.cloud import firestore
        firestore.Client().collection("cases").document("demo").set({"state": json.dumps(STATE)})

def gemini_claims(arts):
    from google import genai
    key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=key) if key else genai.Client(
        vertexai=True, project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"))
    r = client.models.generate_content(model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=PROMPT + json.dumps(arts), config={"response_mime_type": "application/json"})
    return json.loads(r.text)

def fallback_claims(arts):  # no-key mode so the UI can be tested; NOT the real extraction
    out = {}
    for a in arts:
        c = out.setdefault(a["project"], {"project": a["project"], "work_done": "", "impact": "", "artifact_ids": []})
        c["work_done"] += a["title"] + ". "; c["artifact_ids"].append(a["id"])
    return list(out.values())

def revalidate():
    by_id = {a["id"]: a for a in STATE["artifacts"]}
    for cid, c in STATE["claims"].items():
        c["status"], c["note"] = validate_claim(c, by_id, STATE["answers"].get(cid))
        c["question"] = "" if c["impact"] else f"What was the measurable effect of this work on {c['project']}?"

@app.get("/api/state")
def state(): return STATE

@app.post("/api/extract")
def extract():
    live = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_CLOUD_PROJECT")
    raw = gemini_claims(STATE["artifacts"]) if live else fallback_claims(STATE["artifacts"])
    STATE["claims"] = {f"C{i+1}": {**c, "id": f"C{i+1}", "decision": "pending"} for i, c in enumerate(raw)}
    STATE["answers"] = {}
    revalidate(); persist()
    return {"mode": "gemini" if live else "fallback", "claims": len(raw)}

class Answer(BaseModel): text: str
@app.post("/api/claims/{cid}/answer")
def answer(cid: str, a: Answer):
    if cid not in STATE["claims"]: raise HTTPException(404)
    STATE["answers"][cid] = a.text; STATE["claims"][cid]["impact"] = a.text
    revalidate(); persist(); return STATE["claims"][cid]

class Decision(BaseModel): decision: str
@app.post("/api/claims/{cid}/decision")
def decide(cid: str, d: Decision):
    if cid not in STATE["claims"]: raise HTTPException(404)
    STATE["claims"][cid]["decision"] = d.decision; persist(); return STATE["claims"][cid]

@app.post("/api/upload")
async def upload(file: UploadFile, project: str = Form("Uploaded")):
    data, name = await file.read(), file.filename.lower()
    if name.endswith(".docx"):
        from docx import Document
        text = "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)
    elif name.endswith(".pptx"):
        from pptx import Presentation
        text = "\n".join(s.text_frame.text for sl in Presentation(io.BytesIO(data)).slides
                         for s in sl.shapes if s.has_text_frame)
    else: text = data.decode("utf-8", "ignore")
    aid = f"UP-{len(STATE['artifacts']) + 1}"
    STATE["artifacts"].append({"id": aid, "source_type": "upload", "project": project, "date": "",
        "title": file.filename, "url": "", "excerpt": re.sub(r"\s+", " ", text)[:2000]})
    return {"id": aid}

@app.get("/api/export.csv", response_class=PlainTextResponse)
def export():
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["Project", "Work done", "Impact", "Verification", "Evidence"])
    by_id = {a["id"]: a for a in STATE["artifacts"]}
    for c in STATE["claims"].values():
        if c["decision"] == "approve" and c["status"] != "unsupported":
            w.writerow([c["project"], c["work_done"], c["impact"], c["status"],
                        "; ".join(by_id[i]["url"] or i for i in c["artifact_ids"] if i in by_id)])
    return buf.getvalue()

app.mount("/", StaticFiles(directory=BASE / "static", html=True), name="static")
