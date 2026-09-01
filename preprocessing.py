import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

# Features used by the model
CATEGORICAL_FEATURES = ['city', 'area_name', 'zip code', 'property type', 'furnishing']
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


class LocalityMeanEncoder(BaseEstimator, TransformerMixin):
    """Replace categorical columns with their smoothed mean of the target.

    encoding(c) = (sum_y(c) + smooth * global_mean) / (count(c) + smooth)

    Unknown categories map to the global mean. Fits inside each
    cross-validation fold, so there is no target leakage. Keeps the
    numeric columns unchanged.
    """

    def __init__(self, smooth=10.0, cols=None):
        self.smooth = smooth
        self.cols = cols

    def fit(self, X, y):
        X = X.reset_index(drop=True)
        y = pd.Series(y).reset_index(drop=True)
        cols = list(self.cols or X.columns)
        self.global_mean_ = float(y.mean())
        self.means_ = {}
        for c in cols:
            agg = pd.DataFrame({"cat": X[c], "y": y}).groupby("cat")["y"].agg(["sum", "count"])
            enc = (agg["sum"] + self.smooth * self.global_mean_) / (agg["count"] + self.smooth)
            self.means_[c] = enc.to_dict()
        self.cols_ = cols
        return self

    def transform(self, X):
        X = X.copy()
        for c in self.cols_:
            X[c] = X[c].map(self.means_[c]).fillna(self.global_mean_)
        return X


def build_preprocessor():
    """
    Returns a transformer that target-encodes the categorical columns
    (city, area_name, zip code) as smoothed means of the target, keeping
    the numeric columns unchanged. High-cardinality categories (229
    localities, most with a handful of listings) carry far more signal
    as a locality-average price than as one-hot bits.
    """
    return LocalityMeanEncoder(cols=CATEGORICAL_FEATURES)
