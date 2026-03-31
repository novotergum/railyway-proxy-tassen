from fastapi import FastAPI, Request
import httpx
import uuid
from datetime import datetime

app = FastAPI()

current_target = {"url": ""}
results = {}  # job_id → result
orders = {}   # job_id → order record

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
    body = await request.json()
    message = body.get("message", "").strip()
    cmd_lower = message.lower()

    # --- !tasse status ---
    if cmd_lower == "!tasse status":
        pending    = [o for o in orders.values() if o["state"] == "pending"]
        processing = [o for o in orders.values() if o["state"] == "processing"]
        done       = [o for o in orders.values() if o["state"] == "done"]
        confirmed  = [o for o in orders.values() if o["state"] == "confirmed"]
        rejected   = [o for o in orders.values() if o["state"] == "rejected"]

        def fmt(lst, show_order=False):
            if not lst:
                return ["  –"]
            lines = []
            for o in lst:
                if show_order and o.get("order_id"):
                    lines.append(f"  • {o['name']} – Order {o['order_id']} – {o['created_at']}")
                else:
                    lines.append(f"  • {o['name']} – Job {o['job_id']} – {o['created_at']}")
            return lines

        lines = [
            "📊 Tassen-Bestellungen\n",
            f"⏳ Ausstehend ({len(pending)}):",
            *fmt(pending),
            f"\n🔄 In Bearbeitung ({len(processing)}):",
            *fmt(processing),
            f"\n✅ Draft erstellt ({len(done)}):",
            *fmt(done, show_order=True),
            f"\n📦 Bestätigt ({len(confirmed)}):",
            *fmt(confirmed, show_order=True),
            f"\n❌ Abgelehnt ({len(rejected)}):",
            *fmt(rejected, show_order=True),
            f"\n🖥️ Mac Mini: {'🟢 verbunden' if current_target['url'] else '🔴 nicht registriert'}",
        ]
        return {
            "status": "ok",
            "job_id": "status",
            "status_message": "\n".join(lines)
        }

    # --- Kein Mac Mini registriert ---
    if not current_target["url"]:
        return {
            "status": "error",
            "status_message": "❌ Mac Mini nicht erreichbar. Bitte register_url.sh ausführen."
        }

    job_id = str(uuid.uuid4())[:8]
    body["job_id"] = job_id

    # Name aus Message extrahieren: !tasse VORNAME | Vorname Nachname | ...
    parts = message.split("|")
    name = "Unbekannt"
    if len(parts) >= 1:
        name_part = parts[0].replace("!tasse", "").strip()
        if name_part and name_part.upper() not in ["BESTÄTIGEN", "ABLEHNEN", "BESTELLEN", "STATUS"]:
            name = name_part

    # --- bestätigen / ablehnen → Order-State updaten ---
    if "ablehnen" in cmd_lower or "bestätigen" in cmd_lower:
        tokens = message.split()
        ref_order_id = tokens[-1] if tokens else None
        action = "rejected" if "ablehnen" in cmd_lower else "confirmed"
        for o in orders.values():
            if o.get("order_id") == ref_order_id:
                o["state"] = action
                break

    # --- Neue Bestellung tracken ---
    if len(parts) >= 4 and name != "Unbekannt":
        orders[job_id] = {
            "job_id": job_id,
            "name": name,
            "state": "processing",
            "created_at": datetime.now().strftime("%d.%m. %H:%M"),
            "order_id": None,
        }

    # --- An Mac Mini weiterleiten ---
    target = f"{current_target['url']}/tasse"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(target, json=body)
            result = resp.json()
            result["job_id"] = job_id
            return result
    except Exception as e:
        if job_id in orders:
            orders[job_id]["state"] = "error"
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
        # State und Order-ID im orders-Dict aktualisieren
        if job_id in orders:
            status_val = body.get("status", "")
            if status_val == "done":
                orders[job_id]["state"] = "done"
            elif status_val == "error":
                orders[job_id]["state"] = "error"
            # Order-ID aus status_message extrahieren
            msg = body.get("status_message", "")
            if "Order-ID:" in msg:
                try:
                    orders[job_id]["order_id"] = msg.split("Order-ID:")[1].split()[0].strip()
                except Exception:
                    pass
    return {"status": "ok"}

@app.get("/result/{job_id}")
async def get_result(job_id: str):
    return results.get(job_id, {
        "status": "pending",
        "status_message": "⏳ Noch in Bearbeitung..."
    })
