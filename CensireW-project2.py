"""A small, dependency-free web app for tracking shoe prices."""

from __future__ import annotations

import json
import math
import os
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


HOST = "127.0.0.1"
PORT = int(os.environ.get("PAIR_PRICE_PORT", "8765"))
DATABASE = Path(__file__).with_name("shoe_tracker.db")
MAX_REQUEST_SIZE = 16_384

PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f6f5f2">
  <title>Pair Price — Shoe price tracker</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #20231f;
      --muted: #73766f;
      --paper: #f6f5f2;
      --card: #fff;
      --line: #e7e5df;
      --green: #2f6848;
      --green-dark: #214e36;
      --lime: #d7ed9b;
      --red: #b94a3b;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--paper); color: var(--ink); }
    button, input { font: inherit; }
    button { cursor: pointer; }
    .shell { max-width: 1160px; margin: auto; padding: 28px 30px 60px; }
    header { display: flex; align-items: center; justify-content: space-between; gap: 20px; }
    .brand { display: flex; align-items: center; gap: 11px; font-size: 19px; font-weight: 800; letter-spacing: -.7px; }
    .brand-mark { display: grid; place-items: center; width: 35px; height: 35px; border-radius: 12px; color: white; background: var(--green); font-size: 18px; }
    .local-note { color: var(--muted); font-size: 12px; }
    .hero { display: flex; align-items: end; justify-content: space-between; gap: 24px; padding: 67px 0 35px; }
    .eyebrow { margin: 0 0 12px; color: var(--green); font-size: 11px; font-weight: 800; letter-spacing: 1.8px; text-transform: uppercase; }
    h1 { margin: 0; font-size: clamp(36px, 5vw, 58px); line-height: 1.02; letter-spacing: -3.2px; }
    .hero-copy { max-width: 440px; margin: 15px 0 0; color: var(--muted); font-size: 15px; line-height: 1.6; }
    .summary { min-width: 180px; padding: 18px 22px; border: 1px solid var(--line); border-radius: 16px; background: var(--card); }
    .summary strong { display: block; font-size: 28px; letter-spacing: -1px; }
    .summary span { color: var(--muted); font-size: 12px; }
    .add-panel { display: grid; grid-template-columns: 1.15fr 1.5fr .8fr .8fr .85fr auto; gap: 12px; align-items: end; padding: 20px; border-radius: 19px; background: #e9eee7; }
    .field label { display: block; margin: 0 0 7px; color: #51564f; font-size: 11px; font-weight: 750; }
    .field input, .field select, .search { width: 100%; height: 44px; padding: 0 12px; border: 1px solid #d6dbd3; border-radius: 10px; outline: none; background: white; color: var(--ink); }
    .field input:focus, .field select:focus, .search:focus { border-color: var(--green); box-shadow: 0 0 0 3px #2f68481a; }
    .primary { height: 44px; padding: 0 18px; border: 0; border-radius: 10px; background: var(--green); color: white; font-weight: 750; white-space: nowrap; }
    .primary:hover { background: var(--green-dark); }
    .toolbar { display: flex; align-items: center; justify-content: space-between; gap: 18px; margin: 35px 0 17px; }
    h2 { margin: 0; font-size: 20px; letter-spacing: -.6px; }
    .search { max-width: 270px; height: 40px; background: transparent; }
    .grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 17px; }
    .shoe-card { min-width: 0; overflow: hidden; border: 1px solid var(--line); border-radius: 17px; background: var(--card); }
    .shoe-top { min-height: 140px; padding: 19px; background: #e6e9e1; display: flex; flex-direction: column; justify-content: space-between; }
    .shoe-symbol { align-self: flex-end; color: #82927d; font-size: 45px; line-height: 1; }
    .badge { display: inline-flex; align-self: flex-start; align-items: center; gap: 6px; padding: 6px 9px; border-radius: 999px; background: white; color: var(--green); font-size: 10px; font-weight: 800; }
    .badge.target { background: var(--lime); color: #38531e; }
    .shoe-badges { display: flex; flex-wrap: wrap; gap: 7px; }
    .badge.priority { background: #fff; color: #555; text-transform: capitalize; }
    .badge.priority.high { background: #f9ded8; color: #9c3d2e; }
    .badge.priority.medium { background: #f7ebca; color: #765914; }
    .badge.priority.low { background: #dcece0; color: #376046; }
    .shoe-body { padding: 17px 18px 15px; }
    .shoe-name { overflow: hidden; margin: 0; font-size: 17px; font-weight: 780; letter-spacing: -.45px; text-overflow: ellipsis; white-space: nowrap; }
    .store-link { display: inline-block; max-width: 100%; overflow: hidden; margin-top: 5px; color: var(--muted); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
    .price-row { display: flex; align-items: end; justify-content: space-between; gap: 8px; margin: 18px 0 14px; }
    .price { font-size: 28px; font-weight: 800; letter-spacing: -1px; }
    .price-caption { display: block; margin-bottom: 4px; color: var(--muted); font-size: 10px; }
    .target-price { color: var(--muted); font-size: 12px; text-align: right; }
    .target-price strong { display: block; margin-top: 4px; color: var(--ink); font-size: 14px; }
    .history { padding: 11px 0; border-top: 1px solid var(--line); color: var(--muted); font-size: 11px; line-height: 1.65; }
    .history strong { color: var(--ink); font-weight: 650; }
    .card-actions { display: flex; gap: 8px; }
    .small-btn { flex: 1; height: 36px; border: 1px solid var(--line); border-radius: 9px; background: white; color: var(--ink); font-size: 12px; font-weight: 700; }
    .small-btn:hover { border-color: #b5c3b4; background: #f7f9f5; }
    .small-btn.delete { flex: 0 0 38px; color: var(--red); }
    .empty { grid-column: 1 / -1; padding: 55px 20px; border: 1px dashed #c9ccc4; border-radius: 17px; color: var(--muted); text-align: center; }
    .empty strong { display: block; margin-bottom: 7px; color: var(--ink); font-size: 17px; }
    .notice { position: fixed; right: 24px; bottom: 24px; z-index: 3; max-width: min(390px, calc(100vw - 48px)); padding: 13px 17px; border-radius: 11px; background: #242a24; color: white; box-shadow: 0 8px 26px #0002; font-size: 13px; }
    .notice[hidden] { display: none; }
    @media (max-width: 900px) { .add-panel { grid-template-columns: repeat(2, minmax(0, 1fr)); } .add-panel .primary { grid-column: 1 / -1; } .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    @media (max-width: 600px) {
      .shell { padding: 20px 16px 42px; }
      .local-note { display: none; }
      .hero { align-items: start; flex-direction: column; padding: 49px 0 26px; }
      h1 { letter-spacing: -2px; }
      .summary { min-width: 0; width: 100%; }
      .summary strong { display: inline; margin-right: 7px; }
      .add-panel { grid-template-columns: 1fr 1fr; padding: 15px; }
      .field.name, .field.url, .add-panel .primary { grid-column: 1 / -1; }
      .toolbar { align-items: start; flex-direction: column; margin-top: 29px; }
      .search { max-width: none; }
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header>
      <div class="brand"><span class="brand-mark">↗</span> pair price</div>
      <div class="local-note">Your list is saved locally</div>
    </header>
    <section class="hero">
      <div>
        <p class="eyebrow">Good shoes. Better prices.</p>
        <h1>Keep an eye on<br>your next pair.</h1>
        <p class="hero-copy">Save the shoes you love and update their prices as they change. Set a target price and know when your recorded price reaches it.</p>
      </div>
      <div class="summary"><strong id="shoe-count">0</strong><span>pairs on your list</span></div>
    </section>
    <form class="add-panel" id="add-form">
      <div class="field name"><label for="name">SHOE NAME</label><input id="name" name="name" placeholder="e.g. Air Max 90" maxlength="100" required></div>
      <div class="field url"><label for="url">PRODUCT LINK</label><input id="url" name="url" type="url" placeholder="https://store.com/product" maxlength="2000" required></div>
      <div class="field"><label for="price">CURRENT PRICE ($)</label><input id="price" name="price" type="number" min="0.01" max="1000000" step="0.01" placeholder="120.00" required></div>
      <div class="field"><label for="target">TARGET ($) · OPTIONAL</label><input id="target" name="target" type="number" min="0.01" max="1000000" step="0.01" placeholder="90.00"></div>
      <div class="field"><label for="priority">PRIORITY</label><select id="priority" name="priority"><option value="Low">Low</option><option value="Medium" selected>Medium</option><option value="High">High</option></select></div>
      <button class="primary" type="submit">＋ Add pair</button>
    </form>
    <section>
      <div class="toolbar"><h2>Your interest list</h2><input class="search" id="search" type="search" placeholder="Search your list..." aria-label="Search your list"></div>
      <div class="grid" id="shoe-list"></div>
    </section>
  </main>
  <div class="notice" id="notice" role="status" hidden></div>
  <script>
    const list = document.querySelector("#shoe-list");
    const count = document.querySelector("#shoe-count");
    const form = document.querySelector("#add-form");
    const search = document.querySelector("#search");
    const notice = document.querySelector("#notice");
    let shoes = [];
    let noticeTimer;

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, char => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      })[char]);
    }
    function money(value) {
      return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);
    }
    function showNotice(message) {
      notice.textContent = message;
      notice.hidden = false;
      clearTimeout(noticeTimer);
      noticeTimer = setTimeout(() => { notice.hidden = true; }, 3200);
    }
    async function request(url, options = {}) {
      const response = await fetch(url, {
        ...options,
        headers: { "Content-Type": "application/json", ...options.headers }
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Something went wrong.");
      return data;
    }
    function render() {
      count.textContent = shoes.length;
      const query = search.value.trim().toLowerCase();
      const visible = shoes.filter(shoe => shoe.name.toLowerCase().includes(query));
      if (!visible.length) {
        list.innerHTML = `<div class="empty"><strong>${shoes.length ? "No pairs match that search." : "Your list is ready for its first pair."}</strong>${shoes.length ? "Try another search." : "Add a shoe above to start tracking its price."}</div>`;
        return;
      }
      list.innerHTML = visible.map(shoe => {
        const history = shoe.history.slice(0, 3).map(item =>
          `<div><strong>${money(item.price)}</strong> · ${escapeHtml(item.recorded_at)}</div>`
        ).join("");
        const hitTarget = shoe.target_price !== null && shoe.price <= shoe.target_price;
        const badge = hitTarget
          ? `<span class="badge target">✓ Target reached</span>`
          : `<span class="badge">● Tracking</span>`;
        return `<article class="shoe-card">
          <div class="shoe-top"><div class="shoe-badges">${badge}<span class="badge priority ${escapeHtml(shoe.priority.toLowerCase())}">${escapeHtml(shoe.priority)} priority</span></div><span class="shoe-symbol" aria-hidden="true">⌁</span></div>
          <div class="shoe-body">
            <h3 class="shoe-name" title="${escapeHtml(shoe.name)}">${escapeHtml(shoe.name)}</h3>
            <a class="store-link" href="${escapeHtml(shoe.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(new URL(shoe.url).hostname)}</a>
            <div class="price-row"><div><span class="price-caption">CURRENT PRICE</span><strong class="price">${money(shoe.price)}</strong></div>
              <div class="target-price">${shoe.target_price === null ? "No target set" : "TARGET"}${shoe.target_price === null ? "" : `<strong>${money(shoe.target_price)}</strong>`}</div></div>
            <div class="history">${history || "No price history yet."}</div>
            <div class="card-actions">
              <button class="small-btn" data-action="update" data-id="${shoe.id}">Update price</button>
              <button class="small-btn delete" data-action="delete" data-id="${shoe.id}" aria-label="Remove ${escapeHtml(shoe.name)}" title="Remove pair">×</button>
            </div>
          </div>
        </article>`;
      }).join("");
    }
    async function loadShoes() {
      try {
        shoes = await request("/api/shoes");
        render();
      } catch (error) {
        showNotice(error.message);
      }
    }
    form.addEventListener("submit", async event => {
      event.preventDefault();
      const values = new FormData(form);
      const target = values.get("target");
      try {
        await request("/api/shoes", {
          method: "POST",
          body: JSON.stringify({
            name: values.get("name"),
            url: values.get("url"),
            price: Number(values.get("price")),
            target_price: target ? Number(target) : null,
            priority: values.get("priority")
          })
        });
        form.reset();
        await loadShoes();
        showNotice("Pair added to your list.");
      } catch (error) {
        showNotice(error.message);
      }
    });
    search.addEventListener("input", render);
    list.addEventListener("click", async event => {
      const button = event.target.closest("button[data-action]");
      if (!button) return;
      const shoe = shoes.find(item => item.id === Number(button.dataset.id));
      if (!shoe) return;
      if (button.dataset.action === "update") {
        const value = prompt(`Enter the current price for ${shoe.name}:`, shoe.price.toFixed(2));
        if (value === null) return;
        const price = Number(value);
        if (!Number.isFinite(price) || price <= 0) {
          showNotice("Enter a price greater than $0.");
          return;
        }
        try {
          await request(`/api/shoes/${shoe.id}`, { method: "PATCH", body: JSON.stringify({ price }) });
          await loadShoes();
          showNotice("Price updated and saved to history.");
        } catch (error) {
          showNotice(error.message);
        }
      } else if (button.dataset.action === "delete" && confirm(`Remove ${shoe.name} from your list?`)) {
        try {
          await request(`/api/shoes/${shoe.id}`, { method: "DELETE" });
          await loadShoes();
          showNotice("Pair removed.");
        } catch (error) {
          showNotice(error.message);
        }
      }
    });
    loadShoes();
  </script>
</body>
</html>
"""


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS shoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                price REAL NOT NULL,
                target_price REAL,
                priority TEXT NOT NULL DEFAULT 'Medium' CHECK(priority IN ('Low', 'Medium', 'High')),
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shoe_id INTEGER NOT NULL REFERENCES shoes(id) ON DELETE CASCADE,
                price REAL NOT NULL,
                recorded_at TEXT NOT NULL
            );
            """
        )
        shoe_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(shoes)").fetchall()
        }
        if "priority" not in shoe_columns:
            connection.execute(
                "ALTER TABLE shoes ADD COLUMN priority TEXT NOT NULL DEFAULT 'Medium'"
            )


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%b %d, %Y")


def serialize_shoe(connection: sqlite3.Connection, row: sqlite3.Row) -> dict:
    history = connection.execute(
        "SELECT price, recorded_at FROM price_history WHERE shoe_id = ? ORDER BY id DESC LIMIT 10",
        (row["id"],),
    ).fetchall()
    return {
        "id": row["id"],
        "name": row["name"],
        "url": row["url"],
        "price": row["price"],
        "target_price": row["target_price"],
        "priority": row["priority"],
        "history": [dict(item) for item in history],
    }


class ShoeTrackerHandler(BaseHTTPRequestHandler):
    server_version = "PairPrice/1.0"

    def send_json(self, status: int, payload: object) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length_text = self.headers.get("Content-Length", "")
        try:
            length = int(length_text)
        except ValueError as exc:
            raise ValueError("A valid JSON request body is required.") from exc
        if length < 1 or length > MAX_REQUEST_SIZE:
            raise ValueError("The request body is empty or too large.")
        try:
            data = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("The request body must be valid JSON.") from exc
        if not isinstance(data, dict):
            raise ValueError("The request body must be a JSON object.")
        return data

    @staticmethod
    def validate_price(value: object, label: str = "Price") -> float:
        if isinstance(value, bool):
            raise ValueError(f"{label} must be a number greater than $0.")
        try:
            price = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} must be a number greater than $0.") from exc
        if not math.isfinite(price) or price <= 0 or price > 1_000_000:
            raise ValueError(f"{label} must be between $0.01 and $1,000,000.")
        return round(price, 2)

    @staticmethod
    def validate_url(value: object) -> str:
        if not isinstance(value, str) or len(value) > 2000:
            raise ValueError("Enter a valid product link.")
        parsed = urlparse(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Product link must start with http:// or https://.")
        return value.strip()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
            return
        if path != "/api/shoes":
            self.send_json(404, {"error": "Not found."})
            return
        with connect() as connection:
            rows = connection.execute("SELECT * FROM shoes ORDER BY id DESC").fetchall()
            self.send_json(200, [serialize_shoe(connection, row) for row in rows])

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/shoes":
            self.send_json(404, {"error": "Not found."})
            return
        try:
            data = self.read_json()
            name = data.get("name")
            if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
                raise ValueError("Shoe name must be between 1 and 100 characters.")
            url = self.validate_url(data.get("url"))
            price = self.validate_price(data.get("price"))
            target_value = data.get("target_price")
            target_price = None if target_value is None else self.validate_price(target_value, "Target price")
            priority = data.get("priority", "Medium")
            if not isinstance(priority, str) or priority not in {"Low", "Medium", "High"}:
                raise ValueError("Priority must be Low, Medium, or High.")
            with connect() as connection:
                cursor = connection.execute(
                    "INSERT INTO shoes (name, url, price, target_price, priority, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (name.strip(), url, price, target_price, priority, now_utc()),
                )
                shoe_id = cursor.lastrowid
                connection.execute(
                    "INSERT INTO price_history (shoe_id, price, recorded_at) VALUES (?, ?, ?)",
                    (shoe_id, price, now_utc()),
                )
                row = connection.execute("SELECT * FROM shoes WHERE id = ?", (shoe_id,)).fetchone()
                self.send_json(201, serialize_shoe(connection, row))
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
        except sqlite3.Error:
            self.send_json(500, {"error": "The shoe could not be saved. Please try again."})

    def do_PATCH(self) -> None:
        parts = urlparse(self.path).path.strip("/").split("/")
        if len(parts) != 3 or parts[:2] != ["api", "shoes"]:
            self.send_json(404, {"error": "Not found."})
            return
        try:
            shoe_id = int(parts[2])
            if shoe_id < 1:
                raise ValueError
            data = self.read_json()
            price = self.validate_price(data.get("price"))
            with connect() as connection:
                existing = connection.execute("SELECT id FROM shoes WHERE id = ?", (shoe_id,)).fetchone()
                if existing is None:
                    self.send_json(404, {"error": "That pair is no longer on your list."})
                    return
                connection.execute("UPDATE shoes SET price = ? WHERE id = ?", (price, shoe_id))
                connection.execute(
                    "INSERT INTO price_history (shoe_id, price, recorded_at) VALUES (?, ?, ?)",
                    (shoe_id, price, now_utc()),
                )
                row = connection.execute("SELECT * FROM shoes WHERE id = ?", (shoe_id,)).fetchone()
                self.send_json(200, serialize_shoe(connection, row))
        except ValueError:
            self.send_json(400, {"error": "Enter a valid pair ID and price."})
        except sqlite3.Error:
            self.send_json(500, {"error": "The price could not be updated. Please try again."})

    def do_DELETE(self) -> None:
        parts = urlparse(self.path).path.strip("/").split("/")
        if len(parts) != 3 or parts[:2] != ["api", "shoes"]:
            self.send_json(404, {"error": "Not found."})
            return
        try:
            shoe_id = int(parts[2])
            if shoe_id < 1:
                raise ValueError
        except ValueError:
            self.send_json(400, {"error": "Enter a valid pair ID."})
            return
        with connect() as connection:
            cursor = connection.execute("DELETE FROM shoes WHERE id = ?", (shoe_id,))
            if cursor.rowcount == 0:
                self.send_json(404, {"error": "That pair is no longer on your list."})
                return
        self.send_json(200, {"ok": True})

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    initialize_database()
    server = ThreadingHTTPServer((HOST, PORT), ShoeTrackerHandler)
    print(f"Pair Price is running at http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Pair Price.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()