from fastapi import FastAPI, Request
import httpx
import os
import uuid
app = FastAPI()
current_target = {"url": ""}
results = {}  # job_id → result
# -----------------------------------------------------------------------------
# Register
# -----------------------------------------------------------------------------
@app.post("/register")
async def register(request: Request):
    body = await request.json()
    current_target["url"] = body.get("url", "")
    return {"status": "ok", "url": current_target["url"]}
@app.get("/status")
async def status():
    return {"target": current_target["url"]}
# -----------------------------------------------------------------------------
# Tasse
# -----------------------------------------------------------------------------
@app.post("/tasse")
async def tasse(request: Request):
    if not current_target["url"]:
        return {
            "status": "error",
            "status_message": "❌ Mac Mini nicht erreichbar. Bitte register_url.sh ausführen."
        }
    body = await request.json()
    job_id = str(uuid.uuid4())[:8]
    body["job_id"] = job_id
    target = f"{current_target['url']}/tasse"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(target, json=body)
            result = resp.json()
            result["job_id"] = job_id
            return result
    except Exception as e:
        return {
            "status": "error",
            "job_id": job_id,
            "status_message": f"❌ Verbindungsfehler zum Mac Mini: {str(e)}"
        }
# -----------------------------------------------------------------------------
# Result Store
# -----------------------------------------------------------------------------
@app.post("/result")
async def store_result(request: Request):
    body = await request.json()
    job_id = body.get("job_id")
    if job_id:
        results[job_id] = body
    return {"status": "ok"}
@app.get("/result/{job_id}")
async def get_result(job_id: str):
    return results.get(job_id, {
        "status": "pending",
        "status_message": "⏳ Noch in Bearbeitung..."
    })
