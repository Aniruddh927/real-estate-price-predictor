"""
Finds the nearest available houses to a user's search criteria and attaches
map-ready coordinates to each one, so the Flask app can render them as pins
on a Leaflet map alongside the predicted price.
"""

import hashlib

from vadodara_coordinates import get_coordinates

# How far (in degrees, ~roughly meters) individual houses in the same
# locality are spread out around that locality's centroid, purely so
# multiple pins in one area don't sit exactly on top of each other.
JITTER_SPAN = 0.006  # ~600m


def _stable_jitter(seed_text, span=JITTER_SPAN):
    """
    Deterministic pseudo-random offset in [-span, span], derived from a
    stable seed (e.g. the row's sr_no) so the same house always renders
    at the same point on the map instead of jumping around on refresh.
    """
    digest = hashlib.md5(seed_text.encode()).hexdigest()
    # Use two independent hex chunks for the lat/lon offsets
    lat_frac = (int(digest[:8], 16) / 0xFFFFFFFF) * 2 - 1
    lon_frac = (int(digest[8:16], 16) / 0xFFFFFFFF) * 2 - 1
    return lat_frac * span, lon_frac * span


def _similarity_score(row, bedroom, bathroom):
    """Lower is closer: how well a listing matches the requested bed/bath."""
    return abs(row["No bedroom"] - bedroom) + abs(row["No Bathroom"] - bathroom)


def find_nearest_houses(df, city, area_name, zipcode, bathroom, bedroom, top_n=5):
    """
    Returns up to `top_n` listings ranked by how closely they match the
    requested bed/bath count, preferring the same zip code, then falling
    back to the same city if the zip code has no listings. Each result
    includes jittered lat/lon so it can be dropped straight onto a map.
    """
    candidates = df[df["zip code"] == zipcode]
    if candidates.empty:
        candidates = df[df["city"] == city]
    if candidates.empty:
        return []

    candidates = candidates.copy()
    candidates["_score"] = candidates.apply(
        lambda row: _similarity_score(row, bedroom, bathroom), axis=1
    )
    candidates = candidates.sort_values("_score").head(top_n)

    results = []
    for _, row in candidates.iterrows():
        area = row.get("area_name", area_name)
        base_lat, base_lon = get_coordinates(area)
        seed = f"{row.get('sr no', '')}-{area}-{row.get('zip code', '')}"
        d_lat, d_lon = _stable_jitter(seed)

        results.append({
            "city": row.get("city", "Unknown"),
            "area_name": area,
            "zip_code": int(row.get("zip code", zipcode)),
            "bathroom": row.get("No Bathroom", "N/A"),
            "bedroom": row.get("No bedroom", "N/A"),
            "price_per_sqft": row.get("price  per squrefoot", "N/A"),
            "lat": base_lat + d_lat,
            "lon": base_lon + d_lon,
        })
    return results
