// Thrust-vector mixer for the 8-thruster airship bench demo.
//
// Thruster i sits on seam i, at azimuth psi_i = 22.5 + 45 * i degrees. It
// swivels about its radial axis. At angle phi = 0 its jet points straight
// down, so it pushes the ship up. Positive phi tilts the push toward the
// seam's tangential direction t_i = (-sin psi_i, cos psi_i), which is
// counter-clockwise seen from above.
//
// All thrusters share one plenum and one fan, so they all push with about
// the same force T. The fan throttle sets T; the mixer only picks angles:
//   vertical part   v_i = lift
//   tangential part h_i = yaw + surge * t_i.x + sway * t_i.y
//   phi_i           = atan2(h_i, v_i), limited to the swivel's travel
// A thruster can only push along "up" and t_i. Summed over 8 evenly spaced
// thrusters, the tangential parts still add up to any horizontal force
// (sum of t_i t_i^T = 4 I), plus a pure yaw torque.
#pragma once
#include <math.h>

namespace mixer {

constexpr int kThrusters = 8;
constexpr float kPi = 3.14159265358979f;
constexpr float kMaxAngleDeg = 90.0f;  // 1:1 gears on a 180 deg servo

struct Command {
  float lift = 1.0f;   // +1 = all jets down (push up), -1 = push down
  float surge = 0.0f;  // +X, ship frame
  float sway = 0.0f;   // +Y, ship frame
  float yaw = 0.0f;    // +CCW seen from above
};

inline float azimuthDeg(int i) { return 22.5f + 45.0f * i; }

inline float clampf(float x, float lo, float hi) {
  return x < lo ? lo : (x > hi ? hi : x);
}

// Swivel angle in degrees for thruster i.
inline float angleDeg(const Command& c, int i) {
  const float psi = azimuthDeg(i) * kPi / 180.0f;
  const float tx = -sinf(psi), ty = cosf(psi);
  const float h = c.yaw + c.surge * tx + c.sway * ty;
  const float v = c.lift;
  if (fabsf(h) < 1e-6f && fabsf(v) < 1e-6f) return 0.0f;
  return clampf(atan2f(h, v) * 180.0f / kPi, -kMaxAngleDeg, kMaxAngleDeg);
}

// Net force/torque direction for checking: sum of unit thrust vectors.
struct Wrench { float fx, fy, fz, mz; };
inline Wrench net(const Command& c) {
  Wrench w{0, 0, 0, 0};
  for (int i = 0; i < kThrusters; ++i) {
    const float psi = azimuthDeg(i) * kPi / 180.0f;
    const float phi = angleDeg(c, i) * kPi / 180.0f;
    const float tx = -sinf(psi), ty = cosf(psi);
    w.fx += sinf(phi) * tx;
    w.fy += sinf(phi) * ty;
    w.fz += cosf(phi);
    w.mz += sinf(phi);  // x radius: tangential push = torque about Z
  }
  return w;
}

// Servo pulse for a swivel angle. The 1:1 gear pair reverses direction,
// hence sign = -1; trim is per servo, in degrees.
inline int pulseUs(float angle_deg, float trim_deg = 0.0f, int sign = -1,
                   int us_min = 500, int us_max = 2500) {
  const float a = clampf(sign * angle_deg + trim_deg, -90.0f, 90.0f);
  return (int)lroundf(us_min + (a + 90.0f) / 180.0f * (us_max - us_min));
}

}  // namespace mixer
