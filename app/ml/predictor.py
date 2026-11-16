import os
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.preprocessing import StandardScaler

MODEL_PATH = os.path.join(os.path.dirname(__file__), "pulseguard_model.joblib")


class PredictiveMaintenanceEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_or_train()
        return cls._instance

    def _load_or_train(self):
        if os.path.exists(MODEL_PATH):
            bundle = joblib.load(MODEL_PATH)
            self.scaler = bundle["scaler"]
            self.rul_model = bundle["rul_model"]
            self.anomaly_model = bundle["anomaly_model"]
            return

        rng = np.random.default_rng(42)
        n_samples = 5000
        health = rng.uniform(0.0, 1.0, n_samples)

        temp = 65.0 + (1.0 - health) * 55.0 + rng.normal(0, 2.5, n_samples)
        vibration = 1.2 + (1.0 - health) ** 2 * 14.0 + rng.normal(0, 0.4, n_samples)
        rpm = 3000.0 - (1.0 - health) * 450.0 + rng.normal(0, 40.0, n_samples)
        pressure = 15.0 - (1.0 - health) * 4.5 + rng.normal(0, 0.3, n_samples)

        X = np.column_stack([temp, vibration, rpm, pressure])
        y_rul = health * 150.0

        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.rul_model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        self.rul_model.fit(X_scaled, y_rul)

        self.anomaly_model = IsolationForest(contamination=0.08, random_state=42)
        self.anomaly_model.fit(X_scaled)

        joblib.dump(
            {
                "scaler": self.scaler,
                "rul_model": self.rul_model,
                "anomaly_model": self.anomaly_model,
            },
            MODEL_PATH,
        )

    def predict(self, temp: float, vibration: float, rpm: float, pressure: float) -> dict:
        features = np.array([[temp, vibration, rpm, pressure]])
        scaled = self.scaler.transform(features)

        predicted_rul = float(np.clip(self.rul_model.predict(scaled)[0], 0.0, 150.0))
        raw_anomaly = float(self.anomaly_model.decision_function(scaled)[0])
        is_anomaly = bool(self.anomaly_model.predict(scaled)[0] == -1)

        return {
            "predicted_rul": round(predicted_rul, 2),
            "anomaly_score": round(raw_anomaly, 4),
            "is_anomaly": is_anomaly,
        }
