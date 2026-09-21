#include <Arduino.h>
#include <DHT.h>

// ============================================================
// BELTSENTINEL AI
// ESP32 SENSOR + MOTOR CONTROLLER
// ============================================================
// Hardware mapping used by the current prototype:
// PEC11R A -> GPIO32
// PEC11R B -> GPIO33
// PEC11R C -> GND
// DHT11 DATA -> GPIO4
// SW-420 DO -> GPIO27
// LM393 DO -> GPIO26
// LM393 AO -> GPIO34
// L298N ENA -> GPIO25
// L298N IN1 -> GPIO18
// L298N IN2 -> GPIO19
// ACS712 -> NOT CONNECTED
// ============================================================

#define ENCODER_A_PIN 32
#define ENCODER_B_PIN 33

#define DHT_PIN 4
#define DHT_TYPE DHT11

#define VIBRATION_DO_PIN 27
#define ACOUSTIC_DO_PIN 26
#define ACOUSTIC_AO_PIN 34

#define MOTOR_ENA_PIN 25
#define MOTOR_IN1_PIN 18
#define MOTOR_IN2_PIN 19

DHT dht(DHT_PIN, DHT_TYPE);

volatile long encoderCount = 0;
volatile unsigned long vibrationEvents = 0;
volatile unsigned long acousticEvents = 0;

unsigned long lastVibrationEventMs = 0;
unsigned long lastAcousticEventMs = 0;
unsigned long lastTelemetryMs = 0;

unsigned long lastVibrationCounter = 0;
unsigned long lastAcousticCounter = 0;

int motorPwm = 150;
bool motorRunning = false;

const unsigned long TELEMETRY_INTERVAL_MS = 1000;
const unsigned long VIBRATION_DEBOUNCE_MS = 50;
const unsigned long ACOUSTIC_DEBOUNCE_MS = 20;

// ------------------------------------------------------------
// Encoder ISR
// ------------------------------------------------------------
void IRAM_ATTR encoderISR() {
  bool a = digitalRead(ENCODER_A_PIN);
  bool b = digitalRead(ENCODER_B_PIN);

  if (a == b) {
    encoderCount++;
  } else {
    encoderCount--;
  }
}

// ------------------------------------------------------------
// Sensor event handlers
// ------------------------------------------------------------
void IRAM_ATTR vibrationISR() {
  unsigned long now = millis();
  if (now - lastVibrationEventMs >= VIBRATION_DEBOUNCE_MS) {
    vibrationEvents++;
    lastVibrationEventMs = now;
  }
}

void IRAM_ATTR acousticISR() {
  unsigned long now = millis();
  if (now - lastAcousticEventMs >= ACOUSTIC_DEBOUNCE_MS) {
    acousticEvents++;
    lastAcousticEventMs = now;
  }
}

// ------------------------------------------------------------
// Motor control
// ------------------------------------------------------------
void stopMotor() {
  analogWrite(MOTOR_ENA_PIN, 0);
  digitalWrite(MOTOR_IN1_PIN, LOW);
  digitalWrite(MOTOR_IN2_PIN, LOW);
  motorRunning = false;
}

void startMotor() {
  digitalWrite(MOTOR_IN1_PIN, HIGH);
  digitalWrite(MOTOR_IN2_PIN, LOW);
  analogWrite(MOTOR_ENA_PIN, motorPwm);
  motorRunning = true;
}

void setMotorPwm(int value) {
  motorPwm = constrain(value, 0, 255);
  if (motorRunning) {
    analogWrite(MOTOR_ENA_PIN, motorPwm);
  }
}

// ------------------------------------------------------------
// Setup
// ------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(ENCODER_A_PIN, INPUT_PULLUP);
  pinMode(ENCODER_B_PIN, INPUT_PULLUP);

  pinMode(VIBRATION_DO_PIN, INPUT);
  pinMode(ACOUSTIC_DO_PIN, INPUT);
  pinMode(ACOUSTIC_AO_PIN, INPUT);

  pinMode(MOTOR_ENA_PIN, OUTPUT);
  pinMode(MOTOR_IN1_PIN, OUTPUT);
  pinMode(MOTOR_IN2_PIN, OUTPUT);

  stopMotor();
  dht.begin();

  attachInterrupt(
    digitalPinToInterrupt(ENCODER_A_PIN),
    encoderISR,
    CHANGE
  );

  attachInterrupt(
    digitalPinToInterrupt(VIBRATION_DO_PIN),
    vibrationISR,
    CHANGE
  );

  attachInterrupt(
    digitalPinToInterrupt(ACOUSTIC_DO_PIN),
    acousticISR,
    CHANGE
  );

  Serial.println();
  Serial.println("============================================================");
  Serial.println("BELTSENTINEL AI - ESP32 CONTROLLER");
  Serial.println("============================================================");
  Serial.println("Commands:");
  Serial.println("  S = start motor");
  Serial.println("  X = stop motor");
  Serial.println("  + = increase PWM");
  Serial.println("  - = decrease PWM");
  Serial.println();
}

// ------------------------------------------------------------
// Serial commands
// ------------------------------------------------------------
void handleSerialCommand() {
  while (Serial.available()) {
    char command = Serial.read();

    if (command == 'S' || command == 's') {
      startMotor();
      Serial.println("Motor: STARTED");
    }
    else if (command == 'X' || command == 'x') {
      stopMotor();
      Serial.println("Motor: STOPPED");
    }
    else if (command == '+') {
      setMotorPwm(motorPwm + 10);
      Serial.print("Motor PWM: ");
      Serial.println(motorPwm);
    }
    else if (command == '-') {
      setMotorPwm(motorPwm - 10);
      Serial.print("Motor PWM: ");
      Serial.println(motorPwm);
    }
  }
}

// ------------------------------------------------------------
// Telemetry
// ------------------------------------------------------------
void publishTelemetry() {
  noInterrupts();
  long encoderSnapshot = encoderCount;
  unsigned long vibrationSnapshot = vibrationEvents;
  unsigned long acousticSnapshot = acousticEvents;
  interrupts();

  unsigned long vibrationPerSecond = vibrationSnapshot - lastVibrationCounter;
  unsigned long acousticPerSecond = acousticSnapshot - lastAcousticCounter;

  lastVibrationCounter = vibrationSnapshot;
  lastAcousticCounter = acousticSnapshot;

  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();

  if (isnan(temperature)) temperature = 0.0;
  if (isnan(humidity)) humidity = 0.0;

  int acousticRaw = analogRead(ACOUSTIC_AO_PIN);

  Serial.println();
  Serial.println("ESP32 TELEMETRY");
  Serial.println("------------------------------------------------------------");
  Serial.print("Encoder Count       : ");
  Serial.println(encoderSnapshot);
  Serial.print("Vibration Events/s  : ");
  Serial.println(vibrationPerSecond);
  Serial.print("Acoustic Events/s   : ");
  Serial.println(acousticPerSecond);
  Serial.print("Acoustic Raw        : ");
  Serial.println(acousticRaw);
  Serial.print("Temperature         : ");
  Serial.print(temperature, 1);
  Serial.println(" C");
  Serial.print("Humidity            : ");
  Serial.print(humidity, 1);
  Serial.println(" %");
  Serial.print("Motor Status        : ");
  Serial.println(motorRunning ? "RUNNING" : "STOPPED");
  Serial.print("Motor PWM           : ");
  Serial.println(motorPwm);
  Serial.println("Motor Current       : NOT CONNECTED");

  Serial.print("JSON: {");
  Serial.print("\"encoder_pulses\":");
  Serial.print(encoderSnapshot);
  Serial.print(",\"vibration_events_per_sec\":");
  Serial.print(vibrationPerSecond);
  Serial.print(",\"acoustic_events_per_sec\":");
  Serial.print(acousticPerSecond);
  Serial.print(",\"acoustic_raw\":");
  Serial.print(acousticRaw);
  Serial.print(",\"temperature\":");
  Serial.print(temperature, 1);
  Serial.print(",\"humidity\":");
  Serial.print(humidity, 1);
  Serial.print(",\"current_amps\":0.0");
  Serial.print(",\"motor_running\":");
  Serial.print(motorRunning ? "true" : "false");
  Serial.print(",\"motor_pwm\":");
  Serial.print(motorPwm);
  Serial.println("}");
}

// ------------------------------------------------------------
// Main loop
// ------------------------------------------------------------
void loop() {
  handleSerialCommand();

  unsigned long now = millis();

  if (now - lastTelemetryMs >= TELEMETRY_INTERVAL_MS) {
    lastTelemetryMs = now;
    publishTelemetry();
  }
}
