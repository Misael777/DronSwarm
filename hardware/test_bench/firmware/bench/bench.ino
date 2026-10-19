// DronSwarm · firmware del banco de empuje (ESP32, Arduino core 2.x). Ver hardware/test_bench/README.md.
//
// Bibliotecas: "HX711" (bogde), "Adafruit INA228", "Adafruit MAX31855". NO compilado en el entorno del agente:
// compilar y probar con Arduino IDE 2 antes del primer ensayo (S10-02), sin hélice.
//
// Serie a 921600 baudios. Salida: una línea CSV cada 20 ms (50 Hz):
//   t_ms,throttle_us,thrust_raw,torque_a_raw,torque_b_raw,rpm,v_bus,i_bus,esc_v,esc_i,esc_erpm,esc_temp,motor_temp
// Comandos (terminados en \n):
//   T<us>   throttle 1000-2000 µs (rampa limitada a 200 µs/s)      S   parada inmediata (1000 µs)
//   Z       tara de las 3 celdas                                    A   armar (habilita PWM; requiere T1000 antes)
// Seguridad: sin comandos durante 1 s → parada. Corriente > I_LIMIT o temperatura > T_LIMIT → parada y "ABORT".

#include <Adafruit_INA228.h>
#include <Adafruit_MAX31855.h>
#include <HX711.h>

const int PIN_THR_DT = 32, PIN_THR_SCK = 33, PIN_TA_DT = 25, PIN_TA_SCK = 26, PIN_TB_DT = 27, PIN_TB_SCK = 14;
const int PIN_PWM = 18, PIN_RPM = 34, PIN_ESC_RX = 16, PIN_TC_CS = 5;
const float I_LIMIT = 60.0;      // A, se ajusta por motor (DS-I 20, DS-D 60)
const float T_LIMIT = 95.0;      // °C del estator
const int PWM_FREQ = 50, PWM_BITS = 16;

HX711 thrust, torqueA, torqueB;
Adafruit_INA228 ina;
Adafruit_MAX31855 tc(PIN_TC_CS);
volatile uint32_t rpmPulses = 0, lastPulseUs = 0, periodUs = 0;
int targetUs = 1000, currentUs = 1000;
bool armed = false;
uint32_t lastCmdMs = 0, lastSampleMs = 0, lastRampMs = 0;
float escV = 0, escI = 0, escTemp = 0;
uint32_t escErpm = 0;
uint8_t kiss[10];
int kissLen = 0;

void IRAM_ATTR onPulse() {
  uint32_t now = micros();
  if (now - lastPulseUs > 300) {          // rebote: máx. ~200,000 rpm
    periodUs = now - lastPulseUs;
    lastPulseUs = now;
    rpmPulses++;
  }
}

void writeUs(int us) {
  currentUs = constrain(us, 1000, 2000);
  ledcWrite(0, (uint32_t)((currentUs / 20000.0) * ((1 << PWM_BITS) - 1)));
}

void stopMotor(const char *why) {
  targetUs = 1000;
  writeUs(1000);
  armed = false;
  if (why) { Serial.print("ABORT,"); Serial.println(why); }
}

// Telemetría KISS (BLHeli32/AM32): 10 bytes cada vez que se pide; aquí se lee el flujo automático si está activo
void readEsc() {
  while (Serial2.available()) {
    kiss[kissLen++] = Serial2.read();
    if (kissLen == 10) {
      escTemp = kiss[0];
      escV = ((kiss[1] << 8) | kiss[2]) / 100.0;
      escI = ((kiss[3] << 8) | kiss[4]) / 100.0;
      escErpm = ((kiss[7] << 8) | kiss[8]) * 100;
      kissLen = 0;
    }
  }
}

void handleCommand(String c) {
  lastCmdMs = millis();
  if (c.length() == 0) return;
  char k = c.charAt(0);
  if (k == 'S') stopMotor(nullptr);
  else if (k == 'Z') { thrust.tare(20); torqueA.tare(20); torqueB.tare(20); Serial.println("OK,tare"); }
  else if (k == 'A') { armed = (currentUs == 1000); Serial.println(armed ? "OK,armed" : "ERR,throttle"); }
  else if (k == 'T') targetUs = constrain(c.substring(1).toInt(), 1000, 2000);
}

void setup() {
  Serial.begin(921600);
  Serial2.begin(115200, SERIAL_8N1, PIN_ESC_RX, -1);
  ledcSetup(0, PWM_FREQ, PWM_BITS);
  ledcAttachPin(PIN_PWM, 0);
  writeUs(1000);
  thrust.begin(PIN_THR_DT, PIN_THR_SCK);
  torqueA.begin(PIN_TA_DT, PIN_TA_SCK);
  torqueB.begin(PIN_TB_DT, PIN_TB_SCK);
  pinMode(PIN_RPM, INPUT);
  attachInterrupt(digitalPinToInterrupt(PIN_RPM), onPulse, FALLING);
  if (!ina.begin()) Serial.println("WARN,ina228");
  else { ina.setShunt(0.000375, 200.0); }      // shunt 200 A / 75 mV
  Serial.println("t_ms,throttle_us,thrust_raw,torque_a_raw,torque_b_raw,rpm,v_bus,i_bus,esc_v,esc_i,esc_erpm,esc_temp,motor_temp");
}

void loop() {
  static String line;
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n') { handleCommand(line); line = ""; } else line += ch;
  }
  readEsc();
  uint32_t now = millis();
  if (armed && now - lastCmdMs > 1000) stopMotor("timeout");      // el PC dejó de hablar
  if (now - lastRampMs >= 10) {                                      // rampa de 200 µs/s
    lastRampMs = now;
    int step = 2;
    int next = armed ? currentUs + constrain(targetUs - currentUs, -step, step) : 1000;
    writeUs(next);
  }
  if (now - lastSampleMs >= 20) {
    lastSampleMs = now;
    float rpm = (periodUs > 0 && micros() - lastPulseUs < 500000) ? 60e6 / periodUs : 0;
    float v = ina.readBusVoltage() / 1000.0, i = ina.readCurrent() / 1000.0;
    float mt = tc.readCelsius();
    if (armed && (i > I_LIMIT || (!isnan(mt) && mt > T_LIMIT))) stopMotor(i > I_LIMIT ? "current" : "temperature");
    Serial.printf("%lu,%d,%ld,%ld,%ld,%.0f,%.3f,%.3f,%.2f,%.2f,%lu,%.0f,%.1f\n", now, currentUs,
                  thrust.is_ready() ? thrust.read() : 0L, torqueA.is_ready() ? torqueA.read() : 0L,
                  torqueB.is_ready() ? torqueB.read() : 0L, rpm, v, i, escV, escI, escErpm, escTemp, mt);
  }
}
