import pandas as pd
import re

d = pd.read_csv("real_state_dataset_vadodara_real.csv")

def norm(s):
    s = str(s).strip()
    s = re.sub(r"\s+", " ", s)
    return s.title()

d["area_name"] = d["area_name"].map(norm)

VARIANTS = {
    "Sama Savli Road": "Sama-Savli Road",
    "Sama-Savil Road": "Sama-Savli Road",
    "Sama Savil Road": "Sama-Savli Road",
    "Vadodara - Savli Road": "Sama-Savli Road",
    "Atladara": "Atladra",
    "Vasna Bhayli Main Road": "Vasna-Bhayli Road",
    "Vasna Bhayli Road": "Vasna-Bhayli Road",
    "Vadodara Airport": "Airport",
    "Makarpura Road": "Makarpura",
    "Gotri Road": "Gotri",
}
d["area_name"] = d["area_name"].map(lambda s: VARIANTS.get(s, s))

TYPE_VARIANTS = {
    "Flat": "Flat", "Apartment": "Flat", "Multistorey Apartment": "Flat",
    "House": "House", "Villa": "Villa", "Penthouse": "Penthouse",
    "Builder Floor": "Builder Floor", "Studio Apartment": "Studio", "Studio": "Studio",
}
def norm_type(s):
    s = str(s).strip()
    for k, v in TYPE_VARIANTS.items():
        if k.lower() in s.lower():
            return v
    return "Flat"

d["property type"] = d.get("property type", "Flat").map(norm_type)

def norm_furn(s):
    s = str(s).lower()
    if "unfurnish" in s:
        return "Unfurnished"
    if "semi" in s:
        return "Semi-Furnished"
    if "furnish" in s:
        return "Furnished"
    return "Unknown"

d["furnishing"] = d.get("furnishing", "Unknown").map(norm_furn)

def norm_status(s):
    s = str(s).lower()
    if "ready" in s:
        return "Ready to Move"
    if "under" in s or "construction" in s:
        return "Under Construction"
    return "Unknown"

d["status"] = d.get("status", "Unknown").map(norm_status)

def norm_txn(s):
    s = str(s).lower()
    if "new" in s:
        return "New"
    if "resale" in s:
        return "Resale"
    return "Unknown"

d["transaction"] = d.get("transaction", "Unknown").map(norm_txn)

def norm_facing(s):
    s = str(s).strip()
    return s if s and s != "Unknown" else "Other"

d["facing"] = d.get("facing", "Other").map(norm_facing)

def norm_own(s):
    s = str(s).strip()
    return "Freehold" if "freehold" in s.lower() else ("Leasehold" if "lease" in s.lower() else "Other")

d["ownership"] = d.get("ownership", "Other").map(norm_own)

d["area sqft"] = pd.to_numeric(d.get("area sqft"), errors="coerce")
d["floor"] = pd.to_numeric(d.get("floor"), errors="coerce")

# Drop rows without a usable area (needed as a feature)
before = len(d)
d = d.dropna(subset=["area sqft"])
print(f"area drop: {before} -> {len(d)}")

# Clip outliers
lo, hi = d["price  per squrefoot"].quantile([0.03, 0.97])
before = len(d)
d = d[(d["price  per squrefoot"] >= lo) & (d["price  per squrefoot"] <= hi)]
print(f"outlier clip: {before} -> {len(d)} (band {lo:.0f}-{hi:.0f})")

before = len(d)
d = d.drop_duplicates(subset=["area_name", "No bedroom", "No Bathroom",
                              "price  per squrefoot", "property type", "furnishing",
                              "status", "transaction", "facing", "ownership", "area sqft"])
print(f"dup drop: {before} -> {len(d)}")

d = d.sort_values(["area_name", "No bedroom"]).reset_index(drop=True)
d["sr no"] = range(1, len(d) + 1)

cols = ["sr no", "city", "zip code", "No Bathroom", "No bedroom",
        "price  per squrefoot", "area_name", "property type", "furnishing",
        "status", "transaction", "facing", "floor", "ownership", "area sqft"]
d = d[cols]
d.to_csv("real_state_dataset_vadodara.csv", index=False)
print("saved:", len(d), "rows,", d["area_name"].nunique(), "areas")
print(d.groupby("status")["price  per squrefoot"].agg(["count", "mean"]).to_string())
print(d.groupby("transaction")["price  per squrefoot"].agg(["count", "mean"]).to_string())
print(d.groupby("facing")["price  per squrefoot"].agg(["count", "mean"]).sort_values("count", ascending=False).head(5).to_string())
