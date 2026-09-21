"""
BELTSENTINEL AI - ADDITIVE SIH INTELLIGENCE LAYER

This module adds software-only capabilities without changing the
existing telemetry, fusion, detection, or dashboard contracts:

* persistent normalized health snapshots
* trend/degradation analysis
* short-horizon risk projection
* maintenance recommendations
* digital-twin-style conveyor state
* future sensor readiness metadata
* SCADA/PLC-ready normalized payload

The prediction is a prototype risk forecast, not a certified failure
prediction model. It uses the project's live risk score plus recent
sensor trends and AI detections.
"""

import math
import os
import sqlite3
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(BASE_DIR, "database", "beltsentinel.db")

SENSOR_CATALOG = {
    "encoder": {"status": "ACTIVE", "hardware": "Rotary encoder", "role": "Speed/position/joint localization"},
    "vibration": {"status": "ACTIVE", "hardware": "SW-420", "role": "Mechanical vibration/activity"},
    "acoustic": {"status": "ACTIVE", "hardware": "LM393", "role": "Acoustic event/activity"},
    "temperature_humidity": {"status": "ACTIVE", "hardware": "DHT11", "role": "Ambient/process condition"},
    "motor_current": {"status": "SOFTWARE_READY", "hardware": "ACS712 30A", "role": "Drive load/current anomaly"},
    "load": {"status": "FUTURE", "hardware": "Load cell / industrial load sensor", "role": "Belt loading"},
    "tension": {"status": "FUTURE", "hardware": "Tension sensor", "role": "Belt tension"},
    "belt_alignment": {"status": "FUTURE", "hardware": "Tracking/alignment sensor", "role": "Misalignment"},
    "thermal": {"status": "FUTURE", "hardware": "Thermal camera", "role": "Hotspot/overheating inspection"},
}


def _connect():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_intelligence_database():
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS intelligence_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            encoder_pulses REAL DEFAULT 0,
            vibration REAL DEFAULT 0,
            acoustic REAL DEFAULT 0,
            acoustic_raw REAL DEFAULT 0,
            temperature REAL DEFAULT 0,
            humidity REAL DEFAULT 0,
            current_amps REAL DEFAULT 0,
            risk_score REAL DEFAULT 0,
            risk_level TEXT DEFAULT 'NORMAL',
            detection TEXT DEFAULT 'NORMAL',
            confidence REAL DEFAULT 0,
            joint TEXT,
            source TEXT DEFAULT 'LIVE'
        )
    """)
    conn.commit()
    conn.close()


def _num(value, default=0.0):
    try:
        value = float(value)
        return value if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def record_snapshot(telemetry, risk, detection=None):
    telemetry = telemetry if isinstance(telemetry, dict) else {}
    risk = risk if isinstance(risk, dict) else {}
    detection = detection if isinstance(detection, dict) else {}
    conn = _connect()
    conn.execute("""
        INSERT INTO intelligence_snapshots (
            timestamp, encoder_pulses, vibration, acoustic, acoustic_raw,
            temperature, humidity, current_amps, risk_score, risk_level,
            detection, confidence, joint, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        _num(telemetry.get("encoder_pulses")),
        _num(telemetry.get("vibration_events_per_sec", telemetry.get("vibration_pulses"))),
        _num(telemetry.get("acoustic_events_per_sec", telemetry.get("acoustic_pulses"))),
        _num(telemetry.get("acoustic_raw")),
        _num(telemetry.get("temperature")),
        _num(telemetry.get("humidity")),
        _num(telemetry.get("current_amps")),
        _num(risk.get("risk_score")),
        str(risk.get("risk_level", "NORMAL")),
        str(detection.get("detection", "NORMAL")),
        _num(detection.get("confidence")),
        detection.get("joint") or risk.get("joint"),
        "LIVE"
    ))
    conn.commit()
    conn.close()


def recent_snapshots(limit=120):
    limit = max(1, min(int(limit), 2000))
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM intelligence_snapshots ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in reversed(rows)]


def _linear_slope(values):
    if len(values) < 3:
        return 0.0
    n = len(values)
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    den = sum((i - x_mean) ** 2 for i in range(n))
    if den == 0:
        return 0.0
    return sum((i - x_mean) * (y - y_mean) for i, y in enumerate(values)) / den


def _trend_score(values, scale):
    if len(values) < 3 or scale <= 0:
        return 0.0
    slope = _linear_slope(values)
    return max(0.0, min(25.0, slope / scale * 100.0))


def _latest(rows):
    return rows[-1] if rows else {}


def calculate_prediction(limit=120):
    rows = recent_snapshots(limit)
    latest = _latest(rows)
    if not latest:
        return {
            "available": False,
            "message": "Collecting telemetry history before predictive analysis can start.",
            "data_points": 0,
        }

    risk_values = [_num(r["risk_score"]) for r in rows]
    vibration_values = [_num(r["vibration"]) for r in rows]
    acoustic_values = [_num(r["acoustic"]) for r in rows]
    temperature_values = [_num(r["temperature"]) for r in rows]
    current_values = [_num(r["current_amps"]) for r in rows]

    trend_components = {
        "risk": round(_trend_score(risk_values, 4.0), 2),
        "vibration": round(_trend_score(vibration_values, 1.5), 2),
        "acoustic": round(_trend_score(acoustic_values, 1.5), 2),
        "temperature": round(_trend_score(temperature_values, 1.0), 2),
        "motor_current": round(_trend_score(current_values, 0.75), 2),
    }

    latest_risk = _num(latest.get("risk_score"))
    trend_pressure = (
        trend_components["risk"] * 0.45
        + trend_components["vibration"] * 0.18
        + trend_components["acoustic"] * 0.12
        + trend_components["temperature"] * 0.10
        + trend_components["motor_current"] * 0.15
    )
    forecast_score = max(0.0, min(100.0, latest_risk * 0.72 + trend_pressure))

    if forecast_score >= 75:
        forecast_level = "HIGH"
        horizon = "Immediate inspection / next operating cycle"
    elif forecast_score >= 50:
        forecast_level = "ELEVATED"
        horizon = "Prioritize inspection within the next maintenance window"
    elif forecast_score >= 25:
        forecast_level = "WATCH"
        horizon = "Continue monitoring and review trend"
    else:
        forecast_level = "LOW"
        horizon = "Routine monitoring"

    recommendations = []
    if latest_risk >= 70 or forecast_score >= 75:
        recommendations.append("Inspect the current conveyor section and nearest joint before continued heavy operation.")
    if trend_components["vibration"] >= 8:
        recommendations.append("Check idlers, bearings, pulley alignment and belt mechanical condition for increasing vibration.")
    if trend_components["acoustic"] >= 8:
        recommendations.append("Inspect for abnormal rubbing, splice activity or mechanical impact around the current joint.")
    if trend_components["temperature"] >= 8:
        recommendations.append("Inspect drive/pulley/bearing areas for abnormal heating and verify ventilation.")
    if trend_components["motor_current"] >= 8:
        recommendations.append("Check drive loading, belt friction and mechanical resistance; ACS712 should be calibrated when enabled.")
    if not recommendations:
        recommendations.append("No immediate predictive-maintenance action is indicated; continue collecting history.")

    return {
        "available": True,
        "data_points": len(rows),
        "latest_timestamp": latest.get("timestamp"),
        "current_risk_score": round(latest_risk, 2),
        "forecast_score": round(forecast_score, 2),
        "forecast_level": forecast_level,
        "inspection_horizon": horizon,
        "trend_components": trend_components,
        "trend_direction": "DETERIORATING" if trend_pressure >= 8 else "STABLE_OR_IMPROVING",
        "current_joint": latest.get("joint"),
        "dominant_detection": latest.get("detection", "NORMAL"),
        "recommendations": recommendations,
        "method": "Prototype trend + risk projection; not a certified failure-time prediction model.",
    }


def digital_twin_state(telemetry, risk, current_joint):
    telemetry = telemetry if isinstance(telemetry, dict) else {}
    risk = risk if isinstance(risk, dict) else {}
    current_joint = current_joint if isinstance(current_joint, dict) else {}
    joint_id = current_joint.get("joint_id", 1)
    joints = []
    for i in range(1, 6):
        status = "CURRENT" if i == joint_id else "MONITORING"
        if str(risk.get("joint", "")).lower() == f"joint {i}".lower() and risk.get("damage_detected"):
            status = "DAMAGE DETECTED"
        joints.append({"joint_id": i, "name": f"Joint {i}", "status": status})

    return {
        "model": "BELTSENTINEL AI Conveyor Digital Twin",
        "prototype": {"belt_length_cm": 120, "joint_count": 5, "joint_spacing_cm": 24},
        "state": "DEGRADED" if _num(risk.get("risk_score")) >= 30 else "HEALTHY",
        "current_joint": current_joint,
        "belt": {
            "encoder_pulses": _num(telemetry.get("encoder_pulses")),
            "speed_signal": "ENCODER_POSITION",
            "motor_running": bool(telemetry.get("motor_running", False)),
            "motor_pwm": _num(telemetry.get("motor_pwm")),
        },
        "health": {
            "risk_level": risk.get("risk_level", "NORMAL"),
            "risk_score": _num(risk.get("risk_score")),
            "damage_detected": bool(risk.get("damage_detected", False)),
        },
        "environment": {
            "temperature_c": _num(telemetry.get("temperature")),
            "humidity_pct": _num(telemetry.get("humidity")),
        },
        "mechanical": {
            "vibration": _num(telemetry.get("vibration_events_per_sec", telemetry.get("vibration_pulses"))),
            "acoustic": _num(telemetry.get("acoustic_events_per_sec", telemetry.get("acoustic_pulses"))),
            "motor_current_a": _num(telemetry.get("current_amps")),
        },
        "joints": joints,
        "note": "Software digital-twin representation for the 120 cm prototype; physical geometry/PLC integration can be added later.",
    }


def maintenance_recommendations(risk, prediction):
    risk = risk if isinstance(risk, dict) else {}
    prediction = prediction if isinstance(prediction, dict) else {}
    items = []
    level = str(risk.get("risk_level", "NORMAL")).upper()
    if level == "CRITICAL":
        priority = "CRITICAL"
        action = "Stop/secure the prototype if safe to do so and inspect the indicated joint/defect immediately."
    elif level in ("WARNING", "HIGH"):
        priority = "HIGH"
        action = "Schedule targeted inspection of the current joint and review sensor trends."
    else:
        priority = "ROUTINE"
        action = "Continue monitoring and collect additional history."
    items.append({"priority": priority, "action": action, "basis": risk.get("message", "Current risk state")})
    for recommendation in prediction.get("recommendations", []):
        items.append({"priority": "PREDICTIVE", "action": recommendation, "basis": prediction.get("trend_direction", "history")})
    return items


def future_sensor_readiness():
    return {
        "design": "Additive sensor adapter registry",
        "sensors": SENSOR_CATALOG,
        "integration_contract": {
            "endpoint": "/api/esp32/telemetry",
            "accepted_future_fields": ["belt_load_kg", "belt_tension_kn", "alignment_mm", "thermal_max_c", "thermal_hotspot_count"],
            "rule": "Unknown optional fields are ignored by the current backend, allowing future firmware to add sensors incrementally.",
        },
    }


def scada_ready_payload(telemetry, risk, current_joint):
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "asset": "CV-01",
        "asset_type": "CONVEYOR_BELT",
        "operating_mode": "LIVE",
        "position": current_joint,
        "telemetry": telemetry,
        "health": {
            "risk_level": risk.get("risk_level", "NORMAL"),
            "risk_score": _num(risk.get("risk_score")),
            "status": risk.get("status", "NORMAL"),
        },
        "protocol_ready": ["REST/HTTP", "JSON", "PLC/SCADA adapter-ready"],
        "not_connected": True,
    }
