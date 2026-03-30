# main.py
from fastapi import FastAPI, Request
import httpx
import os

app = FastAPI()

# Aktuelle Mac Mini URL wird hier gespeichert
current_target = {"url": ""}

@app.post("/register")
async def register(request: Request):
    body = await request.json()
    current_target["url"] = body.get("url", "")
    print(f"[REGISTER] Neue URL: {current_target['url']}")
    return {"status": "ok", "url": current_target["url"]}

@app.post("/tasse")
async def tasse(request: Request):
    if not current_target["url"]:
        return {"status": "error", "grund": "Mac Mini URL nicht registriert"}
    
    body = await request.json()
    target = f"{current_target['url']}/tasse"
    
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(target, json=body)
        return resp.json()

@app.get("/status")
async def status():
    return {"target": current_target["url"]}
