import sqlite3
import os
from datetime import datetime


# =========================================================
# BELTSENTINEL AI
# DATABASE MODULE
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATABASE_DIR = os.path.join(
    BASE_DIR,
    "database"
)

DATABASE_PATH = os.path.join(
    DATABASE_DIR,
    "beltsentinel.db"
)


# =========================================================
# CREATE DATABASE DIRECTORY
# =========================================================

os.makedirs(
    DATABASE_DIR,
    exist_ok=True
)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


# =========================================================
# CREATE TABLES
# =========================================================

def initialize_database():

    connection = get_connection()

    cursor = connection.cursor()

    # -----------------------------------------------------
    # SENSOR TELEMETRY TABLE
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,

            encoder_pulses INTEGER,
            vibration_pulses INTEGER,

            acoustic_pulses INTEGER,
            acoustic_raw INTEGER,

            temperature REAL,
            humidity REAL,

            current_amps REAL
        )
    """)

    # -----------------------------------------------------
    # AI DETECTION TABLE
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,

            detection TEXT,
            confidence REAL,
            joint TEXT,
            status TEXT
        )
    """)

    # -----------------------------------------------------
    # ALERT TABLE
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,

            alert_type TEXT,
            severity TEXT,
            message TEXT,
            joint TEXT
        )
    """)

    connection.commit()

    connection.close()

    print("DATABASE INITIALIZED")
    print(f"Database location: {DATABASE_PATH}")


# =========================================================
# SAVE TELEMETRY
# =========================================================

def save_telemetry(data):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO telemetry (
            timestamp,
            encoder_pulses,
            vibration_pulses,
            acoustic_pulses,
            acoustic_raw,
            temperature,
            humidity,
            current_amps
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),

        data.get("encoder_pulses", 0),
        data.get("vibration_pulses", 0),

        data.get("acoustic_pulses", 0),
        data.get("acoustic_raw", 0),

        data.get("temperature", 0),
        data.get("humidity", 0),

        data.get("current_amps", 0)
    ))

    connection.commit()

    connection.close()


# =========================================================
# GET RECENT TELEMETRY
# =========================================================

def get_recent_telemetry(limit=100):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM telemetry
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# SAVE AI DETECTION
# =========================================================

def save_detection(
    detection,
    confidence,
    joint,
    status
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO detections (
            timestamp,
            detection,
            confidence,
            joint,
            status
        )

        VALUES (?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        detection,
        confidence,
        joint,
        status
    ))

    connection.commit()

    connection.close()


# =========================================================
# GET RECENT DETECTIONS
# =========================================================

def get_recent_detections(limit=200):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM detections
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()

    connection.close()

    return [dict(row) for row in rows]


# =========================================================
# SAVE ALERT
# =========================================================

def save_alert(
    alert_type,
    severity,
    message,
    joint=None
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO alerts (
            timestamp,
            alert_type,
            severity,
            message,
            joint
        )

        VALUES (?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        alert_type,
        severity,
        message,
        joint
    ))

    connection.commit()

    connection.close()


# =========================================================
# GET ALERTS
# =========================================================

def get_recent_alerts(limit=50):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM alerts
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# DATABASE TEST
# =========================================================

if __name__ == "__main__":

    initialize_database()

    print()
    print("Database test completed.")