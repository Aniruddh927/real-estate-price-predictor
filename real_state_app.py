import json
import os

from flask import Flask, render_template, request, redirect, url_for, session
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
df = pd.read_csv("real_state_dataset_vadodara_random.csv")


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


@app.route("/predict", methods=["POST"])
def predict():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    city = request.form["city"]
    area_name = request.form.get("area_name", "not specified")
    zipcode = int(request.form["zipcode"])
    bathroom = int(request.form["bathroom"])
    bedroom = int(request.form["bedroom"])

    input_data = {
        "city": city,
        "area_name": area_name,
        "zip code": zipcode,
        "No Bathroom": bathroom,
        "No bedroom": bedroom
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
