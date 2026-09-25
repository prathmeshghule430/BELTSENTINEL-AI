import serial
import requests
import json
import time

# ============================================================
# BELTSENTINEL AI
# ESP32 -> FLASK SERIAL BRIDGE
# USB SERIAL VERSION
# ============================================================

SERIAL_PORT = "COM11"
BAUD_RATE = 115200

FLASK_URL = "http://127.0.0.1:5000/api/esp32/telemetry"

print("=" * 60)
print("              BELTSENTINEL AI")
print("          ESP32 -> FLASK SERIAL BRIDGE")
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
        port=SERIAL_PORT,
        baudrate=BAUD_RATE,
        timeout=1
    )

    time.sleep(2)
    esp32.reset_input_buffer()

    print("ESP32 SERIAL CONNECTED")
    print("-" * 60)

except serial.SerialException as e:
    print("ERROR: Could not connect to ESP32")
    print()
    print(e)
    print()
    print("Check:")
    print("1. ESP32 is connected by USB")
    print("2. COM7 is the correct COM port")
    print("3. Arduino Serial Monitor is CLOSED")
    print("4. No other program is using COM7")
    raise SystemExit(1)

except Exception as e:
    print("ERROR: Could not connect to ESP32")
    print(e)
    raise SystemExit(1)


# ============================================================
# MAIN LOOP
# ============================================================

try:

    while True:

        try:

            line = esp32.readline().decode(
                "utf-8",
                errors="ignore"
            ).strip()

            if not line:
                continue

            # Accept both:
            # {"encoder_pulses":123,...}
            #
            # and:
            # TELEMETRY: {"encoder_pulses":123,...}

            if line.startswith("TELEMETRY:"):
                line = line[len("TELEMETRY:"):].strip()

            # Ignore normal ESP32 messages
            if not line.startswith("{"):
                continue

            # ------------------------------------------------
            # PARSE JSON
            # ------------------------------------------------

            try:
                data = json.loads(line)

            except json.JSONDecodeError:
                print()
                print("INVALID JSON RECEIVED:")
                print(line)
                continue

            # ------------------------------------------------
            # DISPLAY TELEMETRY
            # ------------------------------------------------

            print()
            print("ESP32 TELEMETRY")
            print("-" * 60)

            print(json.dumps(data, indent=2))

            # ------------------------------------------------
            # SEND TELEMETRY TO FLASK
            # ------------------------------------------------

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
                print()
                print("FLASK CONNECTION ERROR:")
                print(e)

        except KeyboardInterrupt:
            print()
            print("Stopping serial bridge...")
            break

        except serial.SerialException as e:
            print()
            print("SERIAL CONNECTION ERROR:")
            print(e)
            print()
            print("Check the ESP32 USB connection.")
            break

        except Exception as e:
            print()
            print("UNEXPECTED ERROR:")
            print(e)
            time.sleep(1)

finally:

    # ========================================================
    # CLEANUP
    # ========================================================

    try:
        if esp32.is_open:
            esp32.close()
    except Exception:
        pass

    print()
    print("Serial connection closed.")
    print("Serial bridge stopped.")
