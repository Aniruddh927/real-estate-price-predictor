import pickle

import pandas as pd

from preprocessing import CATEGORICAL_FEATURES, NUMERIC_FEATURES


model = pickle.load(open("model.pkl", "rb"))


def predict_price(input_data):
    """
    input_data: dict with feature values for a single property.
    Returns predicted price per sqft.
    """
    df = pd.DataFrame([input_data])
    df = df[CATEGORICAL_FEATURES + NUMERIC_FEATURES]
    prediction = model.predict(df)
    return float(prediction[0])
