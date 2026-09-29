// Thrust-vector mixer for the airship's swivelling thrusters.
//
// OAS_THRUSTERS thrusters (default 8) sit evenly round the equator: thruster
// i at azimuth psi_i = OAS_FIRST_AZ_DEG + 360 / OAS_THRUSTERS * i degrees
// (default 22.5 + 45 i; the 12-slice, 4-thruster build uses 15 + 90 i). It
// swivels about its radial axis. At angle phi = 0 its jet points straight
// down, so it pushes the ship up. Positive phi tilts the push toward the
// seam's tangential direction t_i = (-sin psi_i, cos psi_i), which is
// counter-clockwise seen from above.
//
// All thrusters share one plenum and one fan, so they all push with about
// the same force T. The fan throttle sets T; the mixer only picks angles:
//   tangential part h_i = yaw + surge * t_i.x + sway * t_i.y
//   phi_i           = asin(h_i / K), K = sqrt(max|h_j|^2 + lift^2)
// A thruster can only push along "up" and t_i. Summed over 8 evenly spaced
// thrusters, the tangential parts still add up to any horizontal force
// (sum of t_i t_i^T = N/2 I for N >= 3 evenly spaced), plus a pure yaw torque.
#pragma once
#include <math.h>

#ifndef OAS_THRUSTERS
#define OAS_THRUSTERS 8
#endif
#ifndef OAS_FIRST_AZ_DEG
#define OAS_FIRST_AZ_DEG 22.5f
#endif

namespace mixer {

constexpr int kThrusters = OAS_THRUSTERS;
constexpr float kPi = 3.14159265358979f;
constexpr float kMaxAngleDeg = 90.0f;  // 1:1 gears on a 180 deg servo

struct Command {
  float lift = 1.0f;   // +1 = all jets down (push up), -1 = push down
  float surge = 0.0f;  // +X, ship frame
  float sway = 0.0f;   // +Y, ship frame
  float yaw = 0.0f;    // +CCW seen from above
};

inline float azimuthDeg(int i) { return OAS_FIRST_AZ_DEG + 360.0f / kThrusters * i; }

inline float clampf(float x, float lo, float hi) {
  return x < lo ? lo : (x > hi ? hi : x);
}

// Horizontal push wanted from thruster i (unscaled).
inline float horizontal(const Command& c, int i) {
  const float psi = azimuthDeg(i) * kPi / 180.0f;
  return c.yaw + c.surge * -sinf(psi) + c.sway * cosf(psi);
}

// Swivel angle in degrees for thruster i. All thrusters share one scale K,
// so sin(phi_i) = h_i / K stays proportional to h_i: the horizontal forces
// and the yaw torque come out exactly in the ratio asked for, with no
// cross-coupling, even with only 4 thrusters. K is the largest |h_i| combined
// with the lift, so the biggest tilt is atan(h_max / lift). The jets can't
// point up, so a negative lift counts as none.
inline float angleDeg(const Command& c, int i) {
  float hmax = 0.0f;
  for (int j = 0; j < kThrusters; ++j) hmax = fmaxf(hmax, fabsf(horizontal(c, j)));
  const float up = fmaxf(c.lift, 0.0f);
  const float k = sqrtf(hmax * hmax + up * up);
  if (k < 1e-6f) return 0.0f;
  const float s = clampf(horizontal(c, i) / k, -1.0f, 1.0f);
  return clampf(asinf(s) * 180.0f / kPi, -kMaxAngleDeg, kMaxAngleDeg);
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
