// OpenAirShips 926: tethered bench demo firmware (ESP32 + PCA9685), v0.
//
// The ESP32 opens a Wi-Fi access point "OpenAirShip" (password below).
// Browse to http://192.168.4.1 for sliders: fan throttle, lift, surge, sway
// and yaw. The mixer (mixer.h) turns those into 8 swivel angles.
// PCA9685 channels 0-7 drive the MG90S swivel servos, channel 8 drives the
// fan's ESC.
//
// Safety: the fan stays at zero until you press ARM. It returns to zero if
// the page stops sending for FAILSAFE_MS, or when you press STOP. Remove
// the impeller for first power-up and for calibrating the ESC.
//
// Libraries: "Adafruit PWM Servo Driver Library"; WiFi and WebServer come
// with the ESP32 core. Board: "ESP32 Dev Module".
#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Adafruit_PWMServoDriver.h>
#include "mixer.h"

// ---- configuration ---------------------------------------------------------
const char* AP_SSID = "OpenAirShip";
const char* AP_PASS = "airship926";       // change me (8+ characters)
const uint8_t ESC_CHANNEL = 8;
const int ESC_MIN_US = 1000, ESC_MAX_US = 2000;
const float THROTTLE_LIMIT = 0.6f;        // bench cap; raise once the fan is proven
const uint32_t FAILSAFE_MS = 1000;
const float SERVO_TRIM_DEG[mixer::kThrusters] = {0, 0, 0, 0, 0, 0, 0, 0};

// ---- state -----------------------------------------------------------------
Adafruit_PWMServoDriver pwm(0x40);
WebServer server(80);
mixer::Command cmd;
float throttle = 0.0f;
bool armed = false;
uint32_t lastCommandMs = 0;

void writeUs(uint8_t ch, int us) {
  // 50 Hz frame = 20000 us across 4096 ticks
  pwm.setPWM(ch, 0, (uint16_t)((uint32_t)us * 4096UL / 20000UL));
}

void applyOutputs() {
  for (int i = 0; i < mixer::kThrusters; ++i)
    writeUs(i, mixer::pulseUs(mixer::angleDeg(cmd, i), SERVO_TRIM_DEG[i]));
  float t = armed ? mixer::clampf(throttle, 0, 1) * THROTTLE_LIMIT : 0.0f;
  writeUs(ESC_CHANNEL, ESC_MIN_US + (int)(t * (ESC_MAX_US - ESC_MIN_US)));
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
  String json = "{\"armed\":" + String(armed ? "true" : "false") + ",\"angles\":[";
  for (int i = 0; i < mixer::kThrusters; ++i)
    json += String(mixer::angleDeg(cmd, i), 1) + (i < 7 ? "," : "]}");
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
fetch(u).then(r=>r.json()).then(j=>q('s').textContent=(j.armed?'ARMED ':'safe ')+'angles '+j.angles.join(' ')).catch(()=>q('s').textContent='no link')}
function arm(v){if(!v)q('t').value=0;a=v;send()}
setInterval(send,200);</script>)HTML";

void setup() {
  Serial.begin(115200);
  Wire.begin();                            // SDA 21, SCL 22
  pwm.begin();
  pwm.setOscillatorFrequency(27000000);
  pwm.setPWMFreq(50);
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
  if (armed && millis() - lastCommandMs > FAILSAFE_MS) {
    armed = false;                         // lost the page: stop the fan
    throttle = 0;
    applyOutputs();
    Serial.println("failsafe: no command, fan stopped");
  }
}
