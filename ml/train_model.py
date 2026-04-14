"""
ml/train_model.py — Train and save the risk detection model
Run once: python ml/train_model.py
"""
import pickle, numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

np.random.seed(42)
N = 3000

hours    = np.random.randint(0, 24, N)
new_dev  = np.random.randint(0, 2, N)
new_loc  = np.random.randint(0, 2, N)
failed   = np.random.randint(0, 6, N)

X = np.column_stack([hours, new_dev, new_loc, failed])
y = (
    ((hours < 6) | (hours > 22)) |
    ((new_dev == 1) & (new_loc == 1)) |
    (failed >= 3)
).astype(int)

# add 5% noise
flip = np.random.choice(N, int(N * 0.05), replace=False)
y[flip] = 1 - y[flip]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)
print(classification_report(y_test, model.predict(X_test)))

with open("model.pkl", "wb") as f:
    pickle.dump(model, f)
print("Saved → model.pkl")
