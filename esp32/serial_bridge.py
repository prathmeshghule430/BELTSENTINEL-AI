import serial
import requests
import json
import time

# ============================================================
# BELTSENTINEL AI
# ESP32 → FLASK SERIAL BRIDGE
# ============================================================

SERIAL_PORT = "COM11"
BAUD_RATE = 115200

FLASK_URL = "http://127.0.0.1:5000/api/esp32/telemetry"

print("=" * 60)
print("              BELTSENTINEL AI")
print("          ESP32 → FLASK BRIDGE")
print("=" * 60)

print()
print(f"Serial Port : {SERIAL_PORT}")
print(f"Baud Rate   : {BAUD_RATE}")
print(f"Flask URL   : {FLASK_URL}")
print()

# ============================================================
# CONNECT TO ESP32
# ============================================================

try:

    esp32 = serial.Serial(
        SERIAL_PORT,
        BAUD_RATE,
        timeout=1
    )

    time.sleep(2)

    print("ESP32 SERIAL CONNECTED")
    print("-" * 60)

except Exception as e:

    print("ERROR: Could not connect to ESP32")
    print(e)

    raise SystemExit


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    try:

        line = esp32.readline().decode(
            "utf-8",
            errors="ignore"
        ).strip()

        if not line:
            continue

        # We only process JSON lines
        if not line.startswith("{"):
            continue

        try:

            data = json.loads(line)

        except json.JSONDecodeError:

            print("Invalid JSON:")
            print(line)

            continue

        # ----------------------------------------------------
        # DISPLAY
        # ----------------------------------------------------

        print()
        print("ESP32 TELEMETRY")
        print("-" * 60)

        print(json.dumps(
            data,
            indent=2
        ))

        # ----------------------------------------------------
        # SEND TO FLASK
        # ----------------------------------------------------

        try:

            response = requests.post(
                FLASK_URL,
                json=data,
                timeout=2
            )

            print(
                f"Flask response: "
                f"{response.status_code}"
            )

            if response.status_code != 200:

                print(
                    "Flask response:",
                    response.text
                )

        except requests.exceptions.RequestException as e:

            print("Flask connection error:")
            print(e)

    except KeyboardInterrupt:

        print()
        print("Stopping serial bridge...")

        break

    except Exception as e:

        print("Unexpected error:")
        print(e)

        time.sleep(1)


# ============================================================
# CLEANUP
# ============================================================

try:
    esp32.close()
except:
    pass

print("Serial connection closed.")