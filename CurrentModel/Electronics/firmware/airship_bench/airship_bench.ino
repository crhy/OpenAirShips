// OpenAirShips 926 firmware: tethered bench demo and self-contained builds.
//
// The ESP32 opens a Wi-Fi access point "OpenAirShip" (password below).
// Browse to http://192.168.4.1 for sliders: fan throttle, lift, surge, sway
// and yaw. The mixer (mixer.h) turns those into swivel angles.
//
// Outputs, chosen at build time:
// - default: a PCA9685 board. Channels 0..N-1 drive the swivel servos and
//   channel 8 drives the fan's ESC.
// - OAS_DIRECT_PWM: the ESP32 drives the servos and ESC itself (LEDC, 50 Hz),
//   with no PCA9685 board. Lighter, for self-contained builds; pins below.
// Thruster layout: OAS_THRUSTERS / OAS_FIRST_AZ_DEG (see mixer.h). For the
// 12-slice, 4-thruster double-Kobra build, put these three lines at the top:
//   #define OAS_DIRECT_PWM
//   #define OAS_THRUSTERS 4
//   #define OAS_FIRST_AZ_DEG 15.0f
// Battery (self-contained builds): the pack voltage through a 100k/22k
// divider on BATT_PIN. Below BATT_CUTOFF_V per cell the fan stops and the
// servos centre, so the pack isn't over-discharged.
//
// Safety: the fan stays at zero until you press ARM. It returns to zero if
// the page stops sending for FAILSAFE_MS, or when you press STOP. Remove
// the impeller for first power-up and for calibrating the ESC.
//
// Libraries: "Adafruit PWM Servo Driver Library" (PCA9685 builds only); WiFi
// and WebServer come with the ESP32 core (3.x). Board: "ESP32 Dev Module".
#include <WiFi.h>
#include <WebServer.h>
#ifndef OAS_DIRECT_PWM
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#endif
#include "mixer.h"

// ---- configuration ---------------------------------------------------------
const char* AP_SSID = "OpenAirShip";
const char* AP_PASS = "airship926";       // change me (8+ characters)
const uint8_t ESC_CHANNEL = 8;           // PCA9685 channel
#ifdef OAS_DIRECT_PWM
const uint8_t SERVO_PINS[8] = {25, 26, 27, 14, 16, 17, 18, 19};   // thruster i on SERVO_PINS[i]
static_assert(mixer::kThrusters <= 8, "one servo pin per thruster");
const uint8_t ESC_PIN = 13;
#endif
const int BATT_PIN = 34;                  // ADC via a 100k / 22k divider (-1: no battery)
const int BATT_CELLS = 4;
const float BATT_DIVIDER = (100.0f + 22.0f) / 22.0f;
const float BATT_CUTOFF_V = 3.4f;         // per cell
const int ESC_MIN_US = 1000, ESC_MAX_US = 2000;
const float THROTTLE_LIMIT = 0.6f;        // bench cap; raise once the fan is proven
const uint32_t FAILSAFE_MS = 1000;
const float SERVO_TRIM_DEG[mixer::kThrusters] = {};   // per-servo trim, degrees

// ---- state -----------------------------------------------------------------
#ifndef OAS_DIRECT_PWM
Adafruit_PWMServoDriver pwm(0x40);
#endif
WebServer server(80);
mixer::Command cmd;
float throttle = 0.0f;
bool armed = false;
bool battLow = false;
float battVolts = 0.0f;
uint32_t lastCommandMs = 0;

#ifdef OAS_DIRECT_PWM
void writeUs(uint8_t pin, int us) {
  // 50 Hz frame = 20000 us across 2^14 ticks
  ledcWrite(pin, (uint32_t)us * 16384UL / 20000UL);
}
#else
void writeUs(uint8_t ch, int us) {
  // 50 Hz frame = 20000 us across 4096 ticks
  pwm.setPWM(ch, 0, (uint16_t)((uint32_t)us * 4096UL / 20000UL));
}
#endif

void applyOutputs() {
  for (int i = 0; i < mixer::kThrusters; ++i) {
    int us = mixer::pulseUs(battLow ? 0.0f : mixer::angleDeg(cmd, i), SERVO_TRIM_DEG[i]);
#ifdef OAS_DIRECT_PWM
    writeUs(SERVO_PINS[i], us);
#else
    writeUs(i, us);
#endif
  }
  float t = (armed && !battLow) ? mixer::clampf(throttle, 0, 1) * THROTTLE_LIMIT : 0.0f;
  int esc = ESC_MIN_US + (int)(t * (ESC_MAX_US - ESC_MIN_US));
#ifdef OAS_DIRECT_PWM
  writeUs(ESC_PIN, esc);
#else
  writeUs(ESC_CHANNEL, esc);
#endif
}

void checkBattery() {
  if (BATT_PIN < 0) return;
  battVolts = analogReadMilliVolts(BATT_PIN) / 1000.0f * BATT_DIVIDER;
  if (battVolts > 1.0f && battVolts < BATT_CUTOFF_V * BATT_CELLS && !battLow) {
    battLow = true;                        // stays latched until reset
    armed = false;
    applyOutputs();
    Serial.printf("battery low (%.2f V): fan stopped\n", battVolts);
  }
}

float arg(const char* name, float fallback) {
  return server.hasArg(name) ? server.arg(name).toFloat() : fallback;
}

void handleCommand() {
  throttle = mixer::clampf(arg("t", throttle), 0, 1);
  cmd.lift = mixer::clampf(arg("l", cmd.lift), -1, 1);
  cmd.surge = mixer::clampf(arg("x", cmd.surge), -1, 1);
  cmd.sway = mixer::clampf(arg("y", cmd.sway), -1, 1);
  cmd.yaw = mixer::clampf(arg("n", cmd.yaw), -1, 1);
  if (server.hasArg("arm")) armed = server.arg("arm") == "1";
  lastCommandMs = millis();
  applyOutputs();
  String json = "{\"armed\":" + String(armed ? "true" : "false") +
                ",\"battery\":" + String(battVolts, 2) + ",\"battLow\":" + String(battLow ? "true" : "false") +
                ",\"angles\":[";
  for (int i = 0; i < mixer::kThrusters; ++i)
    json += String(mixer::angleDeg(cmd, i), 1) + (i < mixer::kThrusters - 1 ? "," : "]}");
  server.send(200, "application/json", json);
}

const char PAGE[] PROGMEM = R"HTML(<!doctype html><meta name=viewport content="width=device-width">
<title>OpenAirShip bench</title><style>body{font:16px sans-serif;margin:16px}label{display:block;margin:14px 0 4px}
input{width:100%}button{font-size:18px;padding:10px 20px;margin:8px 8px 0 0}#s{font-family:monospace}</style>
<h2>OpenAirShip 926 bench</h2>
<button onclick="arm(1)">ARM</button><button onclick="arm(0)" style="background:#e33;color:#fff">STOP</button>
<label>Fan throttle <span id=tv>0</span></label><input id=t type=range min=0 max=1 step=0.01 value=0>
<label>Lift</label><input id=l type=range min=-1 max=1 step=0.05 value=1>
<label>Surge (X)</label><input id=x type=range min=-1 max=1 step=0.05 value=0>
<label>Sway (Y)</label><input id=y type=range min=-1 max=1 step=0.05 value=0>
<label>Yaw</label><input id=n type=range min=-1 max=1 step=0.05 value=0>
<p id=s></p><script>
let a=null;const q=i=>document.getElementById(i);
function send(){let u='/cmd?'+['t','l','x','y','n'].map(k=>k+'='+q(k).value).join('&');
if(a!==null){u+='&arm='+a;a=null}q('tv').textContent=q('t').value;
fetch(u).then(r=>r.json()).then(j=>q('s').textContent=(j.battLow?'BATTERY LOW ':'')+(j.armed?'ARMED ':'safe ')+(j.battery>1?j.battery.toFixed(1)+' V ':'')+'angles '+j.angles.join(' ')).catch(()=>q('s').textContent='no link')}
function arm(v){if(!v)q('t').value=0;a=v;send()}
setInterval(send,200);</script>)HTML";

void setup() {
  Serial.begin(115200);
#ifdef OAS_DIRECT_PWM
  for (int i = 0; i < mixer::kThrusters; ++i) ledcAttach(SERVO_PINS[i], 50, 14);
  ledcAttach(ESC_PIN, 50, 14);
#else
  Wire.begin();                            // SDA 21, SCL 22
  pwm.begin();
  pwm.setOscillatorFrequency(27000000);
  pwm.setPWMFreq(50);
#endif
  applyOutputs();                          // servos centred, ESC at minimum (arms it)
  WiFi.softAP(AP_SSID, AP_PASS);
  server.on("/", [] { server.send_P(200, "text/html", PAGE); });
  server.on("/cmd", handleCommand);
  server.begin();
  Serial.printf("OpenAirShip bench: join %s, open http://%s\n", AP_SSID,
                WiFi.softAPIP().toString().c_str());
}

void loop() {
  server.handleClient();
  static uint32_t lastBattMs = 0;
  if (millis() - lastBattMs > 500) {
    lastBattMs = millis();
    checkBattery();
  }
  if (armed && millis() - lastCommandMs > FAILSAFE_MS) {
    armed = false;                         // lost the page: stop the fan
    throttle = 0;
    applyOutputs();
    Serial.println("failsafe: no command, fan stopped");
  }
}
