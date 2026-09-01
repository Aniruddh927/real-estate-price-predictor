"""
Remaps the dataset's zip codes to verified Vadodara PINs for localities
whose scraped value fell back to a wrong default. Localities not in the
map keep their current zip. Run after re-scraping/cleaning:

    python remap_pincodes.py
"""

import pandas as pd

PIN = {
    # core city areas (verified)
    "Alkapuri": 390007, "Vasna": 390007, "Vasna Road": 390007,
    "Vasna-Bhayli Road": 390007, "Saiyed Vasna": 390007, "Race Course": 390007,
    "Fatehgunj": 390002, "Nizampura": 390002, "Diwalipura": 390002, "Lalbaug": 390002,
    "Manjalpur": 390011, "Karelibaug": 390018, "Akota": 390020, "Akota Road": 390020,
    "Gotri": 390021, "Gotri Road": 390021, "Harni": 390022, "Sama": 390024,
    "Sama-Savli Road": 390024, "Sama Savli Road": 390024, "Tarsali": 390009,
    "Subhanpura": 390023, "Waghodia Road": 390025, "Waghodia": 391760,
    "Waghodia-Savli Road": 391760, "Makarpura": 390014, "Makarpura Road": 390014,
    "Atladra": 390012, "Atladara": 390012, "Kalali": 390012, "Tandalja": 390012,
    "Bhayli": 391410, "Sevasi": 391101, "Chhani": 391740, "Chhani Road": 391740,
    "New Vip Road": 390021, "New Vip Road Area": 390021, "New Vip Road Baikunth": 390021,
    "New VIP Road": 390021, "VIP Road": 390021, "Amit Nagar": 390018,
    "Padra": 391440, "Savli": 391770, "Halol": 389350, "Chansad": 391105,
}

d = pd.read_csv("real_state_dataset_vadodara.csv")
before = d["zip code"].value_counts().to_dict()
mapped = d["area_name"].map(PIN)
n = mapped.notna().sum()
d.loc[mapped.notna(), "zip code"] = mapped[mapped.notna()].astype(int)
d["zip code"] = d["zip code"].astype(int)
d.to_csv("real_state_dataset_vadodara.csv", index=False)
print(f"remapped {n} rows ({len(d)} total)")
print("zip distribution now:")
print(d["zip code"].value_counts().head(12).to_string())
