# CaseLedger

Turns the scattered evidence behind a promotion case (tickets, pull requests, documents, emails, training records) into short, cited entries for the yearly form. Built for the Google Cloud AI Builder Cup, theme: Future of Work and Enterprise Productivity.

**Live app:** https://case-builder-904477666788.us-central1.run.app/| **Video:** 

> Demo data and mocked connectors. All 28 records (and a 150-record scale set) are synthetic. The live page opens with a saved build; pressing Build calls Gemini live and is subject to API limits.

## The problem
Every year, employees rebuild their promotion case from memory across Jira, GitHub, SharePoint and slides. In the author's case this took 4 to 5 hours (one person's estimate), and the coach presenting it cannot easily verify it.

## How it works
1. **Collect:** records from each source are normalised into one format (id, source, owner, project, date, title, excerpt). Word and PowerPoint files can be uploaded.
2. **Draft:** Gemini drafts form entries one project at a time. It is told to credit only the owner's work and never to invent numbers.
3. **Verify:** a rule check confirms every figure in an entry appears in a cited source (dates are matched too). A second Gemini pass checks wording, causal claims, ownership and scope. Entries that fail are held back.
4. **Review and export:** missing results are asked for and marked self-reported. A person approves or rejects each entry, and approved entries export to Excel with evidence links.

## Architecture
FastAPI service on **Cloud Run** (`backend/main.py`, `pipeline.py`, `validator.py`, `export_xlsx.py`) -> **Gemini** (drafting and fact-check, with retry and rate-limit backoff) -> **Firestore** (one document, `cases/demo`, holds the case so it survives restarts). Static interface in `backend/static`, served by Cloud Run [and Firebase Hosting, if deployed].

## Run locally
```
cd backend
python -m venv ../.venv && ../.venv/Scripts/activate   # Windows
pip install -r requirements.txt
# create backend/.env with: GEMINI_API_KEY=...  GEMINI_MODEL=...   (never commit it)
python test_validator.py && python test_pipeline.py
uvicorn main:app --port 8080
```
Optional variables: `DATA_FILE=data/demo_data_large.json` (150-record set), `USE_FIRESTORE=1`, `EMPLOYEE=Priya`.

## Deploy
```
gcloud run deploy case-builder --source . --region us-central1 --allow-unauthenticated \
  --min-instances 1 --max-instances 1 --timeout 300
gcloud run services update case-builder --region us-central1 \
  --update-env-vars "GEMINI_API_KEY=...,GEMINI_MODEL=...,USE_FIRESTORE=1"
```

## Evaluation
`python score.py <state file>` counts planted traps (other people's work, open tickets, typo fixes, team notes, conflicting figures) that appear in entries.

| Run | Sources | Entries | Held back | Trap sources cited | Legitimate sources missed |
|---|---|---|---|---|---|
| Small set, local run 2 | 28 | 13 | 2 | 0 of 7 | 3 of 21 |
| Small set, local run 3 | 31 | 16 | 0 | 0 of 7 | 1 of 24 |
| Small set, before deploy | 28 | 16 | 2 | 0 of 7 | 0 of 21 |
| 150 records, per-project extraction | 151 | 61 | 3 | 0 of 36 | 0 of 115 |

## Limits
- Connectors are mocked and the data is synthetic.
- The AI fact-check varies between runs and produced false positives (for example, an entry flagged although its source title supported it).
- Entry counts vary run to run (36 and 61 on the same 150 records), and most entries at that scale are one line each.
- Documents written by the employee are weaker evidence than system records.
- A single shared Firestore document is used; there is no sign-in.

## Next
Rubric mapping (the same evidence mapped to any firm's criteria), real connectors with employee consent, retrieval for large histories, and an edit button.