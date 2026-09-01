import pickle
import pandas as pd


model = pickle.load(open("model.pkl", "rb"))


def predict_price(input_data):
    """
    input_data: dict with keys 'city', 'zip code', 'No Bathroom', 'No bedroom'
    """
    df = pd.DataFrame([input_data])
    prediction = model.predict(df)
    return float(prediction[0])
