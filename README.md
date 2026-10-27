# Pair Price

A Flask web application for tracking shoe prices, price history, and purchase
priority. Shoe data is stored in `shoe_tracker.db` beside the application.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python CensireW-project2.py
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765) in a browser. To use a
different local port, set `PAIR_PRICE_PORT` before starting the application.

The built-in Flask server is intended for local development.
