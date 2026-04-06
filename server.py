"""
Bot-Q: Combat robot queue system - FastAPI backend
Run with: ./start.sh or uvicorn server:app --host 0.0.0.0 --port 8000
"""

import json
import uuid
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Bot-Q")

BASE = Path(__file__).parent
DATA_FILE = BASE / "queue.json"

# In-memory state
fights: list[dict] = []
current_fight_id: str | None = None
connected_clients: list[WebSocket] = []


def _load():
    """Load queue and current fight from file."""
    global fights, current_fight_id
    if not DATA_FILE.exists():
        fights = []
        current_fight_id = None
        return
    try:
        data = json.loads(DATA_FILE.read_text())
        fights = data.get("fights", [])
        current_fight_id = data.get("current_fight_id")
    except (json.JSONDecodeError, OSError):
        fights = []
        current_fight_id = None


def _save():
    """Save queue and current fight to file."""
    DATA_FILE.write_text(
        json.dumps({"fights": fights, "current_fight_id": current_fight_id}, indent=2)
    )


_load()


class AddFightRequest(BaseModel):
    bot1: str
    bot2: str


class EditFightRequest(BaseModel):
    bot1: str | None = None
    bot2: str | None = None


class MoveFightRequest(BaseModel):
    direction: str


class SetCurrentRequest(BaseModel):
    fight_id: str | None = None


def _state():
    return {"queue": fights, "current_fight_id": current_fight_id}


async def _broadcast():
    """Notify all connected WebSocket clients of state change."""
    dead = []
    state = _state()
    for client in connected_clients:
        try:
            await client.send_json(state)
        except Exception:
            dead.append(client)
    for c in dead:
        if c in connected_clients:
            connected_clients.remove(c)


# --- API ---

@app.get("/api/queue")
def get_queue():
    """Get current queue and current fight."""
    return _state()


def _persist():
    """Save to file after in-memory state is updated. Call after broadcast."""
    _save()


@app.post("/api/queue")
async def add_fight(req: AddFightRequest):
    """Add a fight (2 bots) to end of queue."""
    fight = {"id": str(uuid.uuid4()), "bot1": req.bot1.strip(), "bot2": req.bot2.strip()}
    fights.append(fight)
    await _broadcast()
    _persist()
    return {"ok": True, "fight": fight}


@app.delete("/api/queue/{fight_id}")
async def remove_fight(fight_id: str):
    """Remove a fight from queue."""
    global current_fight_id
    idx = next((i for i, f in enumerate(fights) if f["id"] == fight_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Fight not found")
    fights.pop(idx)
    if current_fight_id == fight_id:
        current_fight_id = None
    await _broadcast()
    _persist()
    return {"ok": True}


@app.patch("/api/queue/{fight_id}")
async def edit_fight(fight_id: str, req: EditFightRequest):
    """Edit bots in a fight."""
    fight = next((f for f in fights if f["id"] == fight_id), None)
    if fight is None:
        raise HTTPException(status_code=404, detail="Fight not found")
    if req.bot1 is not None:
        fight["bot1"] = req.bot1.strip()
    if req.bot2 is not None:
        fight["bot2"] = req.bot2.strip()
    await _broadcast()
    _persist()
    return {"ok": True, "fight": fight}


@app.patch("/api/queue/{fight_id}/move")
async def move_fight(fight_id: str, req: MoveFightRequest):
    """Move fight up or down in queue."""
    idx = next((i for i, f in enumerate(fights) if f["id"] == fight_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Fight not found")
    direction = req.direction.lower()
    if direction == "up" and idx > 0:
        fights[idx], fights[idx - 1] = fights[idx - 1], fights[idx]
    elif direction == "down" and idx < len(fights) - 1:
        fights[idx], fights[idx + 1] = fights[idx + 1], fights[idx]
    else:
        return {"ok": True, **_state()}
    await _broadcast()
    _persist()
    return {"ok": True, **_state()}


@app.patch("/api/current")
async def set_current(req: SetCurrentRequest):
    """Set which fight is currently happening. Only one at a time."""
    global current_fight_id
    if req.fight_id is None:
        current_fight_id = None
    else:
        exists = any(f["id"] == req.fight_id for f in fights)
        if not exists:
            raise HTTPException(status_code=404, detail="Fight not found")
        current_fight_id = req.fight_id
    await _broadcast()
    _persist()
    return {"ok": True, "current_fight_id": current_fight_id}


# --- WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        await websocket.send_json(_state())
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        connected_clients.remove(websocket)


# --- Serve UIs ---

@app.get("/")
def index():
    return FileResponse(BASE / "static" / "display.html")


@app.get("/display")
def display():
    return FileResponse(BASE / "static" / "display.html")


@app.get("/coordinator")
def coordinator():
    return FileResponse(BASE / "static" / "coordinator.html")
