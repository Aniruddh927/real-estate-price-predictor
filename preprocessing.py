import pandas as pd
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer

# Features used by the model
CATEGORICAL_FEATURES = ['city', 'area_name', 'zip code']
NUMERIC_FEATURES = ['No Bathroom', 'No bedroom']
TARGET = 'price  per squrefoot'


def load_dataset(path):
    data = pd.read_csv(path)
    return data


def clean_data(data):
    data = data.copy()

    data = data.dropna()
    data = data.drop_duplicates()

    return data


def split_features_target(data):
    X = data[CATEGORICAL_FEATURES + NUMERIC_FEATURES]
    y = data[TARGET]
    return X, y


def build_preprocessor():
    """
    Returns a ColumnTransformer that:
      - one-hot encodes city, area_name, and zip code (categories, not
        numbers with meaningful magnitude)
      - scales the numeric features (bathroom/bedroom counts)
    """
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore'), CATEGORICAL_FEATURES),
            ('num', StandardScaler(), NUMERIC_FEATURES),
        ]
    )
    return preprocessor
