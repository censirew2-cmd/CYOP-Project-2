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

Enter a shoe name and product link, then select **Pull price from link** to fill
in the current price. If the price field is left empty, Pair Price will try to
find the price when you add the shoe. Use **Refresh price** on a saved pair to
pull a later price and record it in the history; manual entry is still available.
Price extraction uses product metadata and Schema.org JSON-LD. Some stores block
automated requests or render prices only with JavaScript, so those prices may
need to be entered manually. Only public website addresses are fetched.

The built-in Flask server is intended for local development.
