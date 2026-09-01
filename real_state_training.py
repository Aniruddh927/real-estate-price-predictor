import pickle

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.pipeline import Pipeline
from sklearn.metrics import r2_score, mean_absolute_error

from preprocessing import load_dataset, clean_data, split_features_target, build_preprocessor

RANDOM_STATE = 42
DATASET_PATH = "real_state_dataset_vadodara_random.csv"

data = load_dataset(DATASET_PATH)
data = clean_data(data)

X, y = split_features_target(data)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=RANDOM_STATE
)

preprocessor = build_preprocessor()

model = RandomForestRegressor(n_estimators=300, random_state=RANDOM_STATE)
pipeline = Pipeline([("preprocessor", preprocessor), ("model", model)])
pipeline.fit(X_train, y_train)

preds = pipeline.predict(X_test)
r2 = r2_score(y_test, preds)
mae = mean_absolute_error(y_test, preds)


cv = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
cv_scores = cross_val_score(pipeline, X, y, cv=cv, scoring="r2")

print(f"RandomForest: R2={r2:.4f}  MAE={mae:.2f}  "
      f"CV R2={cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")


with open("model.pkl", "wb") as f:
    pickle.dump(pipeline, f)

print("Model trained and saved successfully as model.pkl")
