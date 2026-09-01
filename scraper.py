"""
Scrapes current Vadodara property-for-sale listings from Square Yards
(server-rendered search-result pages) and writes them to a CSV in the same
schema as the app's dataset:

    sr no,city,zip code,No Bathroom,No bedroom,price  per squrefoot,area_name

price per squrefoot is computed from the listing's total price and built-up
area. Zip codes are mapped per locality from the existing dataset (most
common zip per area) so the model's categorical features stay in the same
space; localities not in the old dataset fall back to the city's most
common zip.

Usage:
    python scraper.py [output.csv] [start_page] [end_page]
"""

import re
import sys
import time
import urllib.request

import pandas as pd

BASE_URL = "https://www.squareyards.com/sale/property-for-sale-in-vadodara?page={}"
LOCALITY_BASE = "https://www.squareyards.com/sale/property-for-sale-in-{}-vadodara?page={}"
MB_URL = "https://www.magicbricks.com/property-for-sale-in-vadodara-pppfs?page={}"
MB_LOCALITY_URL = "https://www.magicbricks.com/property-for-sale-in-{}-vadodara-pppfs?page={}"
MB_MAX_CITY_PAGES = 40
MB_MAX_LOCALITY_PAGES = 5
LOCALITIES = [
    "atladara", "bhayli", "gotri", "kalali", "sama-savli-road", "savli",
    "sayajigunj", "sevasi", "tandalja", "vadodara-airport", "vadodara-savli-road",
    "vasna-bhayli-road", "waghodia-road", "al kapuri", "akota", "fatehgunj",
    "manjalpur", "karelibaug", "nizampura", "makarpura", "harni", "diwalipura",
    "vasna", "new-vip-road", "tarsali", "subhanpura", "new-alkapuri", "race-course",
]
DEFAULT_PAGES = (1, 57)
LOCALITY_PAGES = 5
DELAY_SECONDS = 2.5
OLD_DATASET = "real_state_dataset_vadodara.csv"
OUTPUT = "real_state_dataset_vadodara_real.csv"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
}

# Real Vadodara locality PINs (India Post). Localities absent here fall back
# to the most common zip in the existing dataset, then to 390022.
VADODARA_ZIPS = {
    "Akota": 390020, "Alkapuri": 390007, "Amit Nagar": 390023, "Atladara": 390012,
    "Bhayli": 391410, "Chhani": 391740, "Diwalipura": 390002, "Fatehgunj": 390002,
    "Gotri": 390021, "Gotri Road": 390021, "Harni": 390022, "Karelibaug": 390018,
    "Makarpura": 390010, "Manjalpur": 390011, "New Alkapuri": 390019, "New VIP Road": 390018,
    "Nizampura": 390002, "Race Course": 390007, "Sama": 390024, "Sevasi": 391101,
    "Subhanpura": 390023, "Tarsali": 390009, "Vasna": 390007, "Waghodia": 390025,
    "Padra": 391440, "Savli": 391770, "Halol": 389350, "Chansad": 391105,
    "Bhadran Nagar": 390012, "Lalbaug": 390002, "Soma Talav": 390002,
}

PRICE_UNIT = {"lac": 100_000, "lakh": 100_000, "cr": 10_000_000, "crore": 10_000_000,
              "thousand": 1_000, "k": 1_000, "l": 100_000}


def fetch_page(page):
    url = BASE_URL.format(page)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def parse_price(text):
    """Parse '₹ 65 L', '₹ 1.2 Cr', '₹ 39.72 Lac', '₹ 5.85 Lac to 1.25 Cr' -> INR int."""
    m = re.search(r"₹\s?([\d,]+(?:\.\d+)?)\s?(Lac|Lakh|Cr|Crore|Thousand|K|L)\b", text, re.I)
    if not m:
        return None
    unit = m.group(2).lower()
    value = float(m.group(1).replace(",", ""))
    return int(value * PRICE_UNIT[unit])


def parse_area(text):
    m = re.search(r"(\d[\d,]*)\s*Sq\.?\s?Ft\.?", text, re.I)
    return int(m.group(1).replace(",", "")) if m else None


def parse_config(text):
    m = re.search(r"(\d+(?:\.\d+)?)\s*BHK\s*\+\s*(\d+)\s*Bath", text, re.I)
    if m:
        return round_bhk(m.group(1)), int(m.group(2))
    m = re.search(r"(\d+(?:\.\d+)?)\s*BHK", text, re.I)
    if m:
        return round_bhk(m.group(1)), 1
    m = re.search(r"(\d+)\s*RK", text, re.I)
    if m:
        return int(m.group(1)), 1
    return None, None


def round_bhk(value):
    """2.5 BHK -> 3, 2 BHK -> 2 (fractional configs count the study as a room)."""
    f = float(value)
    return int(f) + (1 if f != int(f) else 0)


def parse_cards(html):
    """Split HTML into chunks starting at each SquareYards listing-card."""
    chunks = re.split(r'(?=<article[^>]*class="[^"]*listing-card)', html)
    rows = []
    for chunk in chunks:
        if "listing-card" not in chunk:
            continue
        text = re.sub(r"<script.*?</script>|<style.*?</style>", "", chunk, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)

        title_m = re.search(r"(\d+(?:\.\d+)?)\s*BHK\s*(?:Flat|Apartment|Villa|House|Builder Floor|Plot|Penthouse|Studio)?\s*for Sale in ([^,]+?)(?:, Vadodara| located at|$)", text, re.I)
        locality = title_m.group(2).strip() if title_m else None
        ptype_m = re.search(r"\d+\s*BHK\s+([A-Za-z ]+?)\s+for Sale in", text, re.I)
        ptype = ptype_m.group(1).strip() if ptype_m else "Flat"

        price = parse_price(text)
        area = parse_area(text)
        bhk, bath = parse_config(text)

        if price is None or area is None or bhk is None or locality is None:
            continue
        if not (200 <= area <= 20000 and 1 <= bhk <= 10 and 1 <= (bath or 1) <= 10):
            continue
        per_sqft = price / area
        if not (500 <= per_sqft <= 20000):
            continue

        furn = "Unknown"
        fm = re.search(r"Furnishing\s*([A-Za-z -]+)", text)
        if fm:
            furn = fm.group(1).strip()

        rows.append({
            "locality": locality,
            "bathroom": bath or 1,
            "bedroom": bhk,
            "per_sqft": round(per_sqft),
            "ptype": ptype,
            "furn": furn,
        })
    return rows


def parse_mb_cards(html):
    """Parse MagicBricks SRP cards into the same row shape as parse_cards."""
    rows = []
    chunks = re.split(r'(?=<h2 class="mb-srp__card--title")', html)
    for chunk in chunks:
        if "mb-srp__card--title" not in chunk:
            continue
        title_m = re.search(r'<h2 class="mb-srp__card--title"[^>]*>(.*?)</h2>', chunk, re.S)
        title = re.sub(r"<[^>]+>", " ", title_m.group(1)) if title_m else ""
        title = re.sub(r"\s+", " ", title).strip()
        bhk_m = re.search(r"(\d+)\s*BHK", title, re.I)
        loc_m = re.search(r"for Sale in ([A-Za-z][A-Za-z -]*?)(?: Vadodara|$)", title)
        locality = loc_m.group(1).strip() if loc_m else None
        ptype_m = re.search(r"\d+\s*BHK\s+([A-Za-z ]+?)\s+for Sale in", title, re.I)
        ptype = ptype_m.group(1).strip() if ptype_m else "Flat"

        price = None
        price_m = re.search(r'mb-srp__card__price--amount">(.*?)</div>', chunk, re.S)
        if price_m:
            price_text = re.sub(r"<[^>]+>", " ", price_m.group(1))
            price_text = re.sub(r"\s+", " ", price_text).strip()
            if price_text and "Request" not in price_text:
                pm = re.search(r"₹\s?([\d,]+(?:\.\d+)?)\s?(Lac|Lakh|Cr|Crore)", price_text, re.I)
                if pm:
                    unit = pm.group(2).lower()
                    price = int(float(pm.group(1).replace(",", "")) * PRICE_UNIT[unit])

        area = None
        am = re.search(r'data-summary="carpet-area"[^>]*>.*?mb-srp__card__summary--value">([\d,]+)', chunk, re.S)
        if am:
            area = int(am.group(1).replace(",", ""))
        if area is None:
            am2 = re.search(r'([\d,]+)\s*(?:Sq-ft|Sq\.?\s?ft|sqft)', chunk, re.I)
            if am2:
                area = int(am2.group(1).replace(",", ""))

        bath = None
        bm = re.search(r'data-summary="bathroom"[^>]*>.*?mb-srp__card__summary--value">(\d+)', chunk, re.S)
        if bm:
            bath = int(bm.group(1))

        furn = None
        fm = re.search(r'data-summary="furnishing"[^>]*>.*?mb-srp__card__summary--value">([^<]+)', chunk, re.S)
        if fm:
            furn = fm.group(1).strip()

        if bhk_m is None or price is None or area is None or locality is None:
            continue
        bhk = int(bhk_m.group(1))
        if not (200 <= area <= 20000 and 1 <= bhk <= 10 and 1 <= (bath or 1) <= 10):
            continue
        per_sqft = price / area
        if not (500 <= per_sqft <= 20000):
            continue
        rows.append({
            "locality": locality,
            "bedroom": bhk,
            "bathroom": bath or 1,
            "per_sqft": round(per_sqft),
            "ptype": ptype,
            "furn": furn or "Unknown",
        })
    return rows


def zip_map_from(old_csv):
    df = pd.read_csv(old_csv)
    zips = df.groupby("area_name")["zip code"].agg(lambda s: s.mode().iloc[0]).to_dict()
    fallback = int(df["zip code"].mode().iloc[0])
    return zips, fallback


def save_csv(all_rows, out, zips, fallback_zip):
    records = []
    for i, r in enumerate(all_rows, start=1):
        records.append({
            "sr no": i,
            "city": "Vadodara",
            "zip code": zips.get(r["locality"], fallback_zip),
            "No Bathroom": r["bathroom"],
            "No bedroom": r["bedroom"],
            "price  per squrefoot": r["per_sqft"],
            "area_name": r["locality"],
            "property type": r.get("ptype", "Flat"),
            "furnishing": r.get("furn", "Unknown"),
        })
    df = pd.DataFrame(records, columns=[
        "sr no", "city", "zip code", "No Bathroom", "No bedroom",
        "price  per squrefoot", "area_name", "property type", "furnishing",
    ])
    df.to_csv(out, index=False)
    print(f"[saved {len(df)} rows to {out}]", flush=True)
    return df


def harvest(url, seen, all_rows, label, parser=parse_cards):
    """Fetch one page, parse cards, dedupe, append. Returns new count."""
    try:
        html = fetch_url(url)
    except Exception as e:
        print(f"{label} failed: {e}", file=sys.stderr, flush=True)
        return 0
    cards = parser(html)
    new = 0
    for r in cards:
        key = (r["locality"], r["bedroom"], r["bathroom"], r["per_sqft"],
               r.get("ptype", "Flat"), r.get("furn", "Unknown"))
        if key in seen:
            continue
        seen.add(key)
        all_rows.append(r)
        new += 1
    print(f"{label}: {len(cards)} cards, {new} new (total {len(all_rows)})", flush=True)
    return new


def fetch_url(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else OUTPUT
    start = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PAGES[0]
    end = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_PAGES[1]
    skip_sy = "--skip-sy" in sys.argv

    zips, fallback_zip = zip_map_from(OLD_DATASET)
    zips.update(VADODARA_ZIPS)
    fallback_zip = VADODARA_ZIPS.get("Harni", fallback_zip)

    # Resume from an existing output CSV if present.
    all_rows = []
    seen = set()
    try:
        existing = pd.read_csv(out)
        for _, r in existing.iterrows():
            key = (r["area_name"], int(r["No bedroom"]), int(r["No Bathroom"]),
                   int(r["price  per squrefoot"]))
            seen.add(key)
            all_rows.append({
                "locality": r["area_name"],
                "bedroom": int(r["No bedroom"]),
                "bathroom": int(r["No Bathroom"]),
                "per_sqft": int(r["price  per squrefoot"]),
                "ptype": r.get("property type", "Flat"),
                "furn": r.get("furnishing", "Unknown"),
            })
        print(f"resumed {len(all_rows)} existing rows")
    except FileNotFoundError:
        pass

    if not skip_sy:
        for page in range(start, end + 1):
            harvest(BASE_URL.format(page), seen, all_rows, f"city page {page}")
            time.sleep(DELAY_SECONDS)
        save_csv(all_rows, out, zips, fallback_zip)

        for loc in LOCALITIES:
            stale = 0
            for page in range(1, LOCALITY_PAGES + 1):
                new = harvest(LOCALITY_BASE.format(loc, page), seen, all_rows, f"locality {loc} page {page}")
                time.sleep(DELAY_SECONDS)
                stale = stale + 1 if new == 0 else 0
                if stale >= 2:
                    break
        save_csv(all_rows, out, zips, fallback_zip)

    # MagicBricks: city pages then locality pages.
    stale = 0
    for page in range(1, MB_MAX_CITY_PAGES + 1):
        new = harvest(MB_URL.format(page), seen, all_rows, f"mb city page {page}", parse_mb_cards)
        time.sleep(DELAY_SECONDS)
        stale = stale + 1 if new == 0 else 0
        if stale >= 3:
            break
    save_csv(all_rows, out, zips, fallback_zip)

    for loc in LOCALITIES:
        stale = 0
        for page in range(1, MB_MAX_LOCALITY_PAGES + 1):
            new = harvest(MB_LOCALITY_URL.format(loc, page), seen, all_rows,
                          f"mb locality {loc} page {page}", parse_mb_cards)
            time.sleep(DELAY_SECONDS)
            stale = stale + 1 if new == 0 else 0
            if stale >= 2:
                break
    save_csv(all_rows, out, zips, fallback_zip)

    df = save_csv(all_rows, out, zips, fallback_zip)
    print(df.groupby("area_name")["price  per squrefoot"]
            .agg(["count", "mean"])
            .sort_values("count", ascending=False)
            .head(15))


if __name__ == "__main__":
    main()
