import json
import os
import re

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from model import predict_price
from nearest_houses import find_nearest_houses
from vadodara_coordinates import get_coordinates
from pymongo import MongoClient
from flask_bcrypt import Bcrypt
import pandas as pd

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", 'super_secret_key_for_real_estate')

# MongoDB Configuration
client = MongoClient(os.environ.get("MONGO_URI", 'mongodb://localhost:27017/'))
db = client['real_estate_db']
users_collection = db['users']

bcrypt = Bcrypt(app)

# Load dataset for locating nearest houses
df = pd.read_csv("real_state_dataset_vadodara.csv")


@app.route("/")
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template("index.html", user_name=session.get('user_name'))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        existing_user = users_collection.find_one({"email": email})
        if existing_user:
            return render_template("register.html", error="User already exists with this email")

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        users_collection.insert_one({
            "name": name,
            "email": email,
            "password": hashed_password
        })
        return redirect(url_for('login'))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = users_collection.find_one({"email": email})
        if user and bcrypt.check_password_hash(user["password"], password):
            session['user_id'] = str(user['_id'])
            session['user_name'] = user['name']
            return redirect(url_for('home'))

        return render_template("login.html", error="Invalid email or password")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))


# Curated Vadodara PINs for the app's dropdown areas that have few or no
# scraped listings; used only when the dataset has no match at all.
FALLBACK_AREA_ZIPS = {
    "Fatehgunj": [390002], "Nizampura": [390002], "Diwalipura": [390002],
    "Vasna": [390007], "Alkapuri": [390007], "Sama": [390024], "Tarsali": [390009],
    "Makarpura": [390010], "Manjalpur": [390011], "Karelibaug": [390018],
    "Waghodia Road": [390025], "Akota": [390020], "Gotri": [390021],
    "Harni": [390022], "New VIP Road": [390018], "Amit Nagar": [390023],
    "Bhayli": [391410],
}


@app.route("/api/area_lookup")
def area_lookup():
    """Map pincode -> areas (or area -> pincodes) from the live dataset."""
    if 'user_id' not in session:
        return jsonify({"found": False, "areas": [], "zips": []})
    area = request.args.get("area")
    if area:
        zips = df[df["area_name"] == area]["zip code"].dropna().unique()
        if len(zips) == 0:
            # Dropdown names may differ from dataset names ("Vasna" vs
            # "Vasna Road"): fall back to a case-insensitive substring match.
            zips = df[df["area_name"].str.contains(re.escape(area), case=False, na=False)]["zip code"].dropna().unique()
        if len(zips) == 0:
            # No real listings at all (e.g. Amit Nagar): use the curated PIN.
            zips = FALLBACK_AREA_ZIPS.get(area, [])
        zips = sorted(int(z) for z in zips)
        return jsonify({"found": len(zips) > 0, "areas": [], "zips": zips})

    try:
        zipcode = int(request.args.get("zip", ""))
    except (TypeError, ValueError):
        return jsonify({"found": False, "areas": [], "zips": []})
    # Most frequent areas first; cap at 8 so pincodes like 390022 (50+ names,
    # many society names) don't flood the dropdown.
    counts = df[df["zip code"] == zipcode]["area_name"].dropna().value_counts()
    areas = [str(a) for a in counts.head(8).index]
    return jsonify({"found": len(areas) > 0, "areas": areas, "zips": []})


@app.route("/predict", methods=["POST"])
def predict():
    try:
        city = request.form["city"]
        area_name = request.form.get("area_name", "not specified")
        zipcode = int(request.form["zipcode"])
        bathroom = int(request.form["bathroom"])
        bedroom = int(request.form["bedroom"])
        property_type = request.form.get("property_type", "Flat")
        furnishing = request.form.get("furnishing", "Unknown")
    except (KeyError, ValueError):
        return render_template(
            "index.html",
            error="Please fill in all fields with valid numbers (e.g. zip 390007, beds 2).",
            user_name=session.get('user_name')
        )

    input_data = {
        "city": city,
        "area_name": area_name,
        "zip code": zipcode,
        "No Bathroom": bathroom,
        "No bedroom": bedroom,
        "property type": property_type,
        "furnishing": furnishing,
    }

    # Predict price
    prediction = predict_price(input_data)

    # Locate nearest available houses, ranked by how closely they match
    # the requested bed/bath count (same zip code first, same city as fallback)
    nearest_houses = find_nearest_houses(
        df, city=city, area_name=area_name, zipcode=zipcode,
        bathroom=bathroom, bedroom=bedroom, top_n=5
    )

    # Where the user's own search sits on the map
    search_lat, search_lon = get_coordinates(area_name)
    search_location = {
        "lat": search_lat,
        "lon": search_lon,
        "area_name": area_name,
        "predicted_price": round(prediction, 2),
    }

    return render_template(
        "index.html",
        prediction=prediction,
        nearest_houses=nearest_houses,
        nearest_houses_json=json.dumps(nearest_houses),
        search_location_json=json.dumps(search_location),
        user_name=session.get('user_name')
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
    )
