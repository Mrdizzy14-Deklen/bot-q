# Bot-Q

Queue system for combat robot competitions. Coordinators add fights to a shared queue; a display shows which bots need to be on deck.

## Setup

```bash
pip install -r requirements.txt
```

## Run

Start the server (on the coordinator computer or any machine on the LAN):

```bash
./start.sh
```

Or manually:

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

- **Coordinator UI**: http://localhost:8000/coordinator  
  Add fights, remove, edit, reorder, and set which fight is currently happening.
- **Display UI**: http://localhost:8000/display  
  Read-only list of fights. The current fight is highlighted in red. Put in fullscreen on the display screen.

On the display computer, use `http://<server-ip>:8000/display` (replace `<server-ip>` with the coordinator machine's IP).

## Data

The queue and current fight are stored in `queue.json` in the project directory. Data persists across server restarts.
