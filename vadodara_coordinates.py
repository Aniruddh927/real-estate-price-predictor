"""
Approximate latitude/longitude for the Vadodara localities that appear in
real_state_dataset_vadodara_random.csv.

NOTE: The dataset only records `area_name` + `zip code`, not an exact
address, so there is no ground-truth coordinate per house. These are
centroid coordinates for each locality (accurate to roughly a few hundred
meters), good enough to place pins on a map. For production-grade accuracy,
replace this with a real geocoding call (Google Geocoding API / OpenStreetMap
Nominatim) keyed on `area_name + ", Vadodara"`.
"""

AREA_COORDINATES = {
    "Fatehgunj":      (22.3181, 73.1929),
    "Nizampura":      (22.3253, 73.1846),
    "Diwalipura":     (22.2988, 73.1875),
    "Vasna":          (22.2874, 73.1746),
    "Alkapuri":       (22.3095, 73.1706),
    "Sama":           (22.3315, 73.1590),
    "Tarsali":        (22.2688, 73.1668),
    "Makarpura":      (22.2519, 73.1699),
    "Manjalpur":      (22.2721, 73.1889),
    "Karelibaug":     (22.3266, 73.2028),
    "Waghodia Road":  (22.3220, 73.2270),
    "Akota":          (22.2965, 73.1747),
    "Gotri":          (22.3106, 73.1521),
    "Harni":          (22.3346, 73.2117),
    "New VIP Road":   (22.3245, 73.1490),
    "Amit Nagar":     (22.3286, 73.2093),
    "Bhayli":         (22.2695, 73.1259),
}

# Fallback: Vadodara city centre, used if an area_name isn't in the table above
CITY_CENTER = (22.3072, 73.1812)


def get_coordinates(area_name):
    """Return (lat, lon) for a Vadodara locality, falling back to the city centre."""
    return AREA_COORDINATES.get(area_name, CITY_CENTER)
