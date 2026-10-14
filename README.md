# Evidence Assistant

An employee-controlled prototype for turning work artifacts into reviewable contribution claims. Claims include links to their source artifacts, can be approved or rejected by the employee, and can be exported only after approval. The app does not make promotion decisions or calculate a promotion-readiness score.

## What it does

- Loads synthetic Jira, GitHub, and SharePoint-style artifacts from `backend/data/demo_data.json`.
- Uses Gemini to draft contribution claims when configured; otherwise, it runs a clearly labeled fallback mode that groups artifact titles by project. The fallback is not AI extraction.
- Shows each claim with its cited artifacts and a numeric-evidence check.
- Lets the employee add impact details and approve or reject claims.
- Exports approved, supported claims as CSV.
- Includes an upload API for text, DOCX, and PPTX files.

The Jira, GitHub, and SharePoint records are seeded examples, not live integrations. The current browser UI does not expose file upload controls; uploads are available through the API.

## Requirements

- Python 3.11 or newer
- A Gemini API key for live extraction, or Google Cloud Application Default Credentials and a Google Cloud project if using Vertex AI

## Run locally on Windows

Open PowerShell in the repository root, then run:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks environment activation, allow it for the current terminal only and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Start the development server with automatic reload:

```powershell
uvicorn main:app --host 127.0.0.1 --port 8080 --reload
```

Open <http://127.0.0.1:8080>. FastAPI's interactive API documentation is at <http://127.0.0.1:8080/docs>.

## Configure Gemini (optional)

Create `backend/.env` and add your key and model:

```dotenv
GEMINI_API_KEY=replace-with-your-key
GEMINI_MODEL=gemini-2.5-flash
```

The app loads this file on startup. Keep `.env` private; do not commit API keys or other credentials. Without `GEMINI_API_KEY` or `GOOGLE_CLOUD_PROJECT`, the app uses fallback mode. For Vertex AI instead of an API key, configure Application Default Credentials and set:

```dotenv
GOOGLE_CLOUD_PROJECT=your-google-cloud-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GEMINI_MODEL=gemini-2.5-flash
```

For local Vertex AI authentication, install and configure the Google Cloud CLI, then run `gcloud auth application-default login`. Google Cloud usage may require an active billing account.

## Use the app

1. Click **Build my case** to generate claims from the seeded artifacts.
2. Inspect each claim and expand **Sources** to check the cited artifacts.
3. Add an impact answer when prompted, then approve or reject each claim.
4. Click **Export approved entries** to download a CSV. Only approved claims that are not marked unsupported are included.

The validator checks whether figures in a claim appear in its cited artifacts or in the employee's answer. `verified` means the figures match cited sources; `self_reported` means a figure came from the employee's answer; `unchecked` means there are no figures to compare and the wording itself is not verified; `unsupported` means the claim lacks a valid citation or contains figures not found in the evidence or employee answer. These labels are checks, not a judgment of performance.

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/state` | Read current artifacts and claims |
| `POST` | `/api/extract` | Generate claims from the current artifacts |
| `POST` | `/api/claims/{cid}/answer` | Submit an employee answer as JSON, for example `{"text":"Reduced processing time by 20%"}` |
| `POST` | `/api/claims/{cid}/decision` | Set a decision as JSON: `{"decision":"approve"}` or `{"decision":"reject"}` |
| `POST` | `/api/upload` | Upload a file as multipart form data; optional `project` field |
| `GET` | `/api/export.csv` | Download approved, non-unsupported claims as CSV |

## State and privacy notes

- By default, artifacts and claim state live in process memory. Restarting the server resets claims, decisions, and uploads to the seeded demo data.
- Setting `USE_FIRESTORE=1` enables writes of the current case state to a Firestore document. The prototype does not restore that saved state on startup.
- Use synthetic or otherwise authorized data only. The local prototype has no sign-in or access-control layer; do not expose it publicly with confidential work artifacts.
- Imported artifact text is sent to Gemini when live extraction is enabled. Do not submit confidential data unless you have authorization and have reviewed the applicable service and organization policies.

## Run the validator checks

From the `backend` directory with the virtual environment active:

```powershell
python test_validator.py
```

## Docker / Cloud Run

The root `Dockerfile` packages the backend and serves the UI and API on the port provided by Cloud Run. From the repository root, build and run locally with Docker:

```powershell
docker build -t evidence-assistant .
docker run --rm -p 8080:8080 -e PORT=8080 evidence-assistant
```

To deploy to Cloud Run, configure an active Google Cloud billing account, enable the required APIs, and deploy the service from the repository root. Set `GEMINI_API_KEY` as a Secret Manager-backed environment variable rather than placing the key in source control or the Docker image. Cloud Run usage and Gemini requests can incur charges.

`firebase.json` contains an optional Firebase Hosting rewrite to a Cloud Run service named `case-builder` in `us-central1`; deploy a matching Cloud Run service before using that rewrite.