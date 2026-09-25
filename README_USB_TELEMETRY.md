# BELTSENTINEL AI — USB TELEMETRY READY SETUP

This version removes the need to run a separate Python serial bridge.
The **Flask backend automatically detects the ESP32 USB/COM port**, reads
`TELEMETRY_JSON:` lines at 115200 baud, and posts the telemetry into the
existing `/api/esp32/telemetry` pipeline.

## 1. Install dependencies

From the project root:

```powershell
python -m pip install -r requirements.txt
```

## 2. Connect ESP32 by USB

- Upload the USB telemetry firmware to the ESP32.
- Close Arduino IDE Serial Monitor/Serial Plotter before starting the backend.
  Only one program can normally own the COM port at a time.
- Keep the ESP32 connected by USB.

The ESP32 must send lines beginning with:

```text
TELEMETRY_JSON:{...}
```

## 3. Start the backend

```powershell
python -m backend.app
```

You should see:

```text
ESP32 USB TELEMETRY BRIDGE: STARTING
ESP32_SERIAL_PORT: AUTO-DETECT
```

When the board is detected:

```text
ESP32 USB SERIAL CONNECTED: COMx @ 115200
```

Then every telemetry packet should produce:

```text
ESP32 TELEMETRY -> BACKEND: HTTP 200 | {...}
```

## 4. Open the dashboard

Open:

```text
http://127.0.0.1:5000/
```

The existing dashboard structure is preserved. Values should update about once
per second.

## 5. Diagnostic endpoints

Current live telemetry:

```text
http://127.0.0.1:5000/api/telemetry
```

ESP32 USB bridge status:

```text
http://127.0.0.1:5000/api/esp32/status
```

The serial status endpoint reports the detected COM port, received packet
count, posted packet count, and the latest bridge error if any.

## 6. If the COM port is not auto-detected

Find the ESP32 COM port in Windows Device Manager and put this in `.env`:

```text
ESP32_SERIAL_PORT=COM5
ESP32_SERIAL_BAUD=115200
```

Replace `COM5` with the actual port. Restart the backend.

## 7. Important

Do **not** run the old standalone serial bridge at the same time as this
version. The Flask backend is now the serial bridge.

The ACS712 is intentionally still reported as `0.0 A` because it is not
connected. That is expected.
