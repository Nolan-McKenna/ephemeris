# Ephemeris — Conjunction Risk Demo

A minimal Flask-based demo for your VC presentation showing satellite collision risk assessment.

## Setup

### 1. Install dependencies
```bash
pip install flask requests
```
*(numpy is optional but helps — only stdlib + flask + requests required)*

### 2. Get Space-Track credentials
Register at [space-track.org](https://www.space-track.org/auth/createAccount) (free).

### 3. Run
```bash
cd ephemeris_demo
python app.py
```
Then open **http://localhost:5050**

---

## How to use the demo

1. **Connect** — Enter your Space-Track email + password and click Connect
2. **Search objects** — Type a satellite name (e.g. "ISS", "STARLINK", "COSMOS 1408") or a NORAD ID
3. **Select** two objects from the search results
4. **Analyze** — Click "Analyze Conjunction"
5. See the **risk assessment**, **miss distance**, and **3D globe visualization** with both orbit tracks and the closest approach point

---

## Good demo scenarios

| Scenario | Object 1 | Object 2 |
|---|---|---|
| Classic conjunction | ISS (25544) | Any nearby debris |
| Debris concern | COSMOS 1408 DEB | STARLINK-xxxx |
| Two LEO sats | STARLINK-1007 | ONEWEB-0001 |

---

## Files

- `app.py` — Flask server + API routes
- `sgp4_lite.py` — Pure Python SGP4 orbit propagator (no external deps)

## Architecture

```
Browser (CesiumJS globe)
    ↕ REST API
Flask Server (app.py)
    ↕ HTTPS
Space-Track.org (TLE data)
```

## Notes

- The SGP4 propagator is a simplified implementation suitable for LEO visualization. For production, use the full `sgp4` Python package.
- Conjunction analysis runs over 90-minute window with 0.5-minute resolution.
- No data is stored — purely in-memory for demo purposes.
