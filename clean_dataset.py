import pandas as pd
import re

d = pd.read_csv("real_state_dataset_vadodara_real.csv")

# Normalize locality names: case, punctuation, common variants.
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

# Normalize property type and furnishing.
TYPE_VARIANTS = {
    "Flat": "Flat", "Apartment": "Flat", "Multistorey Apartment": "Flat",
    "House": "House", "Villa": "Villa", "Penthouse": "Penthouse",
    "Builder Floor": "Builder Floor", "Studio Apartment": "Studio", "Studio": "Studio",
    "Villa": "Villa",
}
def norm_type(s):
    s = str(s).strip()
    for k, v in TYPE_VARIANTS.items():
        if k.lower() in s.lower():
            return v
    return "Flat"

d["property type"] = d.get("property type", "Flat").map(norm_type)
d["furnishing"] = d.get("furnishing", "Unknown").map(
    lambda s: "Furnished" if "furnish" in str(s).lower() and "unfurnish" not in str(s).lower()
    else ("Semi-Furnished" if "semi" in str(s).lower() else ("Unfurnished" if "unfurnish" in str(s).lower() else "Unknown"))
)

# Clip extreme per-sqft outliers (keep 3rd..97th percentile band).
lo, hi = d["price  per squrefoot"].quantile([0.03, 0.97])
before = len(d)
d = d[(d["price  per squrefoot"] >= lo) & (d["price  per squrefoot"] <= hi)]
print(f"outlier clip: {before} -> {len(d)} rows (band {lo:.0f}-{hi:.0f})")

before = len(d)
d = d.drop_duplicates(subset=["area_name", "No bedroom", "No Bathroom",
                              "price  per squrefoot", "property type", "furnishing"])
print(f"dup drop: {before} -> {len(d)}")

d = d.sort_values(["area_name", "No bedroom"]).reset_index(drop=True)
d["sr no"] = range(1, len(d) + 1)

cols = ["sr no", "city", "zip code", "No Bathroom", "No bedroom",
        "price  per squrefoot", "area_name", "property type", "furnishing"]
d = d[cols]
d.to_csv("real_state_dataset_vadodara.csv", index=False)
print("saved real_state_dataset_vadodara.csv:", len(d), "rows,", d["area_name"].nunique(), "areas")
print(d.groupby("property type")["price  per squrefoot"].agg(["count", "mean"]).to_string())
print(d.groupby("furnishing")["price  per squrefoot"].agg(["count", "mean"]).to_string())
