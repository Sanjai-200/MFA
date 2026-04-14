"""
ml/risk_engine.py
Uses YOUR model.pkl with exact same feature pipeline as your smart MFA project:
  device, location, loginCount, hour, failedAttempts
  device:   1=Mobile, 0=Laptop/Desktop
  location: 0=India/Unknown (safe), 1=Foreign (risky)
  model returns: 0=safe, 1=risky
"""
import os, pickle
import pandas as pd
from config import MODEL_PATH

_model = None

def _load():
    global _model
    if _model is None and os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, "rb") as f:
            _model = pickle.load(f)
    return _model

def safe_int(value, default=0):
    try: return int(value)
    except: return default

def parse_time(time_str):
    try: return int(str(time_str).split(":")[0])
    except: return 12

def parse_location(location):
    """0 = India/Unknown (safe), 1 = Foreign (risky)"""
    if not location: return 0
    loc = str(location).strip().lower()
    if loc in ["india", "unknown", ""]: return 0
    return 1

def parse_device(device):
    """1 = Mobile, 0 = Laptop/Desktop"""
    if not device: return 0
    if "mobile" in str(device).strip().lower(): return 1
    return 0

def encode(data: dict) -> pd.DataFrame:
    """Exact same encode() as your smart MFA app.py"""
    device         = parse_device(data.get("device"))
    location       = parse_location(data.get("location"))
    loginCount     = safe_int(data.get("loginCount"),     1)
    failedAttempts = safe_int(data.get("failedAttempts"), 0)
    hour           = parse_time(data.get("time"))

    df = pd.DataFrame(
        [[device, location, loginCount, hour, failedAttempts]],
        columns=["device", "location", "loginCount", "hour", "failedAttempts"]
    )
    print("RISK ENGINE INPUT:", df.values.tolist())
    return df

def predict_risk(data: dict):
    """
    Returns (prediction: int, label: str, score: float)
    prediction: 0=safe, 1=risky  (from your model)
    label: 'low' or 'high'
    score: 0.0 or 1.0
    """
    model = _load()
    if model is None:
        # fallback heuristic if model.pkl not found
        hour   = parse_time(data.get("time"))
        failed = safe_int(data.get("failedAttempts"), 0)
        risky  = (hour < 6 or hour > 22 or failed >= 3)
        pred   = 1 if risky else 0
    else:
        df   = encode(data)
        pred = int(model.predict(df)[0])

    print(f"PREDICTION: {pred} (0=safe, 1=risky)")
    label = "high" if pred == 1 else "low"
    return pred, label, float(pred)
