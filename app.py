"""
Jumia Price Benchmark Tool - Backend Flask
Usage: python app.py  →  http://localhost:5000
"""

from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import os
import io
import secrets
from functools import wraps

app = Flask(__name__, static_folder=".")
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
CORS(app, supports_credentials=True)

# Mot de passe — à définir dans les variables d'env Render : APP_PASSWORD
APP_PASSWORD = os.environ.get("APP_PASSWORD", "jumia2024")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# ─────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            return jsonify({"error": "Non authentifié", "code": "UNAUTHORIZED"}), 401
        return f(*args, **kwargs)
    return decorated


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    password = data.get("password", "")
    if password == APP_PASSWORD:
        session["authenticated"] = True
        session.permanent = True
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Mot de passe incorrect"}), 401


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/api/auth-check", methods=["GET"])
def auth_check():
    return jsonify({"authenticated": bool(session.get("authenticated"))})


# ─────────────────────────────────────────
# SCRAPER JUMIA
# ─────────────────────────────────────────

def scrape_jumia(sku: str) -> dict:
    url = f"https://www.jumia.com.ng/catalog/?q={sku}"
    try:
        resp = SESSION.get(url, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        article = soup.select_one("article.prd")
        if not article:
            return {"sku": sku, "found": False, "source": "jumia"}
        name_el = article.select_one(".name")
        price_el = article.select_one(".prc")
        img_el = article.select_one("img.img")
        link_el = article.select_one("a.core")
        name = name_el.get_text(strip=True) if name_el else ""
        price_raw = price_el.get_text(strip=True) if price_el else ""
        price_num = parse_price(price_raw)
        img = img_el.get("data-src") or img_el.get("src", "") if img_el else ""
        link = "https://www.jumia.com.ng" + link_el.get("href", "") if link_el else url
        return {"sku": sku, "found": bool(name), "source": "jumia",
                "name": name, "price_raw": price_raw, "price": price_num,
                "image": img, "url": link}
    except Exception as e:
        return {"sku": sku, "found": False, "source": "jumia", "error": str(e)}


# ─────────────────────────────────────────
# SCRAPERS CONCURRENTS
# ─────────────────────────────────────────

def scrape_konga(product_name: str) -> dict:
    query = clean_query(product_name)
    url = f"https://www.konga.com/search?search={query}"
    try:
        resp = SESSION.get(url, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        item = soup.select_one("[class*='product-item'], [class*='ProductItem'], ._1v8X2")
        if not item:
            return {"source": "konga", "found": False}
        name_el = item.select_one("[class*='name'], [class*='title'], h3, h4")
        price_el = item.select_one("[class*='price'], [data-price]")
        link_el = item.select_one("a[href]")
        name = name_el.get_text(strip=True) if name_el else ""
        price_raw = price_el.get_text(strip=True) if price_el else ""
        price_num = parse_price(price_raw)
        link = link_el.get("href", "") if link_el else ""
        if link and not link.startswith("http"):
            link = "https://www.konga.com" + link
        return {"source": "konga", "found": bool(price_num),
                "name": name, "price_raw": price_raw, "price": price_num, "url": link}
    except Exception as e:
        return {"source": "konga", "found": False, "error": str(e)}


def scrape_slot(product_name: str) -> dict:
    query = clean_query(product_name)
    url = f"https://slot.ng/?s={query}"
    try:
        resp = SESSION.get(url, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        item = soup.select_one(".product, .type-product, li.product")
        if not item:
            return {"source": "slot", "found": False}
        name_el = item.select_one(".woocommerce-loop-product__title, h2, h3")
        price_el = item.select_one(".price .woocommerce-Price-amount, .price")
        link_el = item.select_one("a[href]")
        name = name_el.get_text(strip=True) if name_el else ""
        price_raw = price_el.get_text(strip=True) if price_el else ""
        price_num = parse_price(price_raw)
        link = link_el.get("href", "") if link_el else ""
        return {"source": "slot", "found": bool(price_num),
                "name": name, "price_raw": price_raw, "price": price_num, "url": link}
    except Exception as e:
        return {"source": "slot", "found": False, "error": str(e)}


def scrape_payporte(product_name: str) -> dict:
    query = clean_query(product_name)
    url = f"https://www.payporte.com/search?q={query}"
    try:
        resp = SESSION.get(url, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        item = soup.select_one(".product-item, .product-card, [class*='product']")
        if not item:
            return {"source": "payporte", "found": False}
        name_el = item.select_one("[class*='name'], [class*='title'], h3, h4")
        price_el = item.select_one("[class*='price']")
        link_el = item.select_one("a[href]")
        name = name_el.get_text(strip=True) if name_el else ""
        price_raw = price_el.get_text(strip=True) if price_el else ""
        price_num = parse_price(price_raw)
        link = link_el.get("href", "") if link_el else ""
        if link and not link.startswith("http"):
            link = "https://www.payporte.com" + link
        return {"source": "payporte", "found": bool(price_num),
                "name": name, "price_raw": price_raw, "price": price_num, "url": link}
    except Exception as e:
        return {"source": "payporte", "found": False, "error": str(e)}


def scrape_fouani(product_name: str) -> dict:
    query = clean_query(product_name)
    url = f"https://fouanistore.com/?s={query}"
    try:
        resp = SESSION.get(url, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        item = soup.select_one(".product, li.product, .type-product")
        if not item:
            return {"source": "fouani", "found": False}
        name_el = item.select_one("h2, h3, .woocommerce-loop-product__title")
        price_el = item.select_one(".price .amount, .price")
        link_el = item.select_one("a[href]")
        name = name_el.get_text(strip=True) if name_el else ""
        price_raw = price_el.get_text(strip=True) if price_el else ""
        price_num = parse_price(price_raw)
        link = link_el.get("href", "") if link_el else ""
        return {"source": "fouani", "found": bool(price_num),
                "name": name, "price_raw": price_raw, "price": price_num, "url": link}
    except Exception as e:
        return {"source": "fouani", "found": False, "error": str(e)}


# ─────────────────────────────────────────
# UTILITAIRES
# ─────────────────────────────────────────

def parse_price(text: str) -> float:
    if not text:
        return 0.0
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def clean_query(name: str) -> str:
    return requests.utils.quote(name[:80])


def determine_status(jumia_price: float, competitors: list) -> str:
    comp_prices = [c["price"] for c in competitors if c.get("found") and c.get("price", 0) > 0]
    if not comp_prices:
        return "no_data"
    min_comp = min(comp_prices)
    if jumia_price <= min_comp:
        return "win"
    elif jumia_price <= min_comp * 1.02:
        return "tie"
    else:
        return "lose"


def run_benchmark_for_skus(skus):
    results = []
    for sku in skus[:50]:
        sku = str(sku).strip()
        if not sku:
            continue
        jumia = scrape_jumia(sku)
        time.sleep(0.5)
        if not jumia.get("found"):
            results.append({"sku": sku, "jumia": jumia, "competitors": [], "status": "not_found"})
            continue
        product_name = jumia.get("name", "")
        competitors = []
        for fn in [scrape_konga, scrape_slot, scrape_payporte, scrape_fouani]:
            competitors.append(fn(product_name))
            time.sleep(0.4)
        status = determine_status(jumia.get("price", 0), competitors)
        results.append({"sku": sku, "jumia": jumia, "competitors": competitors, "status": status})
    return results


# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/benchmark", methods=["POST"])
@require_auth
def benchmark():
    data = request.get_json()
    skus = data.get("skus", [])
    if not skus:
        return jsonify({"error": "Aucun SKU fourni"}), 400
    return jsonify({"results": run_benchmark_for_skus(skus)})


@app.route("/api/benchmark/upload", methods=["POST"])
@require_auth
def benchmark_upload():
    if "file" not in request.files:
        return jsonify({"error": "Aucun fichier envoyé"}), 400
    file = request.files["file"]
    filename = file.filename.lower()
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(file)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file)
        else:
            return jsonify({"error": "Format non supporté. Utilise .csv ou .xlsx"}), 400
        col = next((c for c in df.columns if "sku" in c.lower()), df.columns[0])
        skus = df[col].dropna().astype(str).tolist()
        return jsonify({"results": run_benchmark_for_skus(skus)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/export", methods=["POST"])
@require_auth
def export_excel():
    data = request.get_json()
    results = data.get("results", [])
    rows = []
    for r in results:
        jumia = r.get("jumia", {})
        comp_map = {c["source"]: c for c in r.get("competitors", [])}
        rows.append({
            "SKU": r.get("sku", ""),
            "Nom produit": jumia.get("name", ""),
            "Prix Jumia (₦)": jumia.get("price", ""),
            "Konga (₦)": comp_map.get("konga", {}).get("price", ""),
            "Slot.ng (₦)": comp_map.get("slot", {}).get("price", ""),
            "PayPorte (₦)": comp_map.get("payporte", {}).get("price", ""),
            "Fouani (₦)": comp_map.get("fouani", {}).get("price", ""),
            "Statut": r.get("status", ""),
            "Lien Jumia": jumia.get("url", ""),
        })
    df = pd.DataFrame(rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Benchmark")
    output.seek(0)
    from flask import send_file
    return send_file(output, download_name="benchmark_jumia.xlsx", as_attachment=True,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("RENDER") is None
    print("=" * 50)
    print(f"  Jumia Benchmark Tool — http://localhost:{port}")
    print(f"  Mot de passe par défaut : {APP_PASSWORD}")
    print("=" * 50)
    app.run(debug=debug, host="0.0.0.0", port=port)
