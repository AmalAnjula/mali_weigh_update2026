# Oil Level Monitoring System v2

## Quick Start

Open **two terminals**:

**Terminal 1 — data updater (1 Hz):**
```bash
pip install flask
python simulator.py
```

**Terminal 2 — web server:**
```bash
python app.py
```

Then open: **http://localhost:5000**

---

## How it works

```
simulator.py  ──writes──►  data.json  ◄──reads──  app.py  ──serves──►  browser
    (1 Hz)                                           Flask              (polls 1 Hz)
```

- `simulator.py` updates `data.json` every 1 second (replace with real PLC/Modbus read)
- `app.py` serves `data.json` via `/api/data` and handles button commands via `/api/control`
- The browser polls `/api/data` every 1 second and re-renders the UI

## Files

```
ols2/
├── app.py           Flask server
├── simulator.py     1 Hz data updater (replace with real PLC)
├── data.json        Shared state file
├── requirements.txt
└── templates/
    └── index.html   HMI frontend
```

## Admin password
Default: `1234`  
Change in `templates/index.html`: `const PASS = "1234";`

## Replace simulator with real hardware
Edit `simulate_step()` in `simulator.py` — replace the flow logic with actual sensor reads:
```python
def simulate_step(d):
    # Read from Modbus / serial / OPC-UA here
    d["tank"]["weight_kg"] = read_weight_from_plc()
    ...
```
