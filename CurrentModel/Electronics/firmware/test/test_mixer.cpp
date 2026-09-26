// Host test for mixer.h:  g++ -std=c++17 -I../airship_bench test_mixer.cpp && ./a.out
#include <cstdio>
#include <cmath>
#include "mixer.h"

static int failures = 0;
static void check(bool ok, const char* what) {
  std::printf("%s  %s\n", ok ? "ok  " : "FAIL", what);
  if (!ok) ++failures;
}
static bool near(float a, float b, float tol = 1e-3f) { return std::fabs(a - b) < tol; }

int main() {
  using namespace mixer;
  Command c;

  // Pure lift: every jet straight down, no side force or torque.
  bool all0 = true;
  for (int i = 0; i < kThrusters; ++i) all0 &= near(angleDeg(c, i), 0);
  Wrench w = net(c);
  check(all0 && near(w.fz, 8) && near(w.fx, 0) && near(w.fy, 0) && near(w.mz, 0),
        "lift only: all angles 0, net force straight up");

  // Yaw: every thruster tilts the same way, no net sideways force.
  c = Command{}; c.yaw = 1.0f;
  bool same = true;
  for (int i = 0; i < kThrusters; ++i) same &= near(angleDeg(c, i), 45.0f);
  w = net(c);
  check(same && w.mz > 5 && near(w.fx, 0) && near(w.fy, 0), "yaw: all +45 deg, pure torque");

  // Surge +X: net force along +X, none along Y, no torque.
  c = Command{}; c.surge = 0.5f;
  w = net(c);
  check(w.fx > 1 && near(w.fy, 0) && near(w.mz, 0, 1e-2f), "surge +X: force along +X only");

  // Sway +Y: net force along +Y, none along X.
  c = Command{}; c.sway = 0.5f;
  w = net(c);
  check(w.fy > 1 && near(w.fx, 0) && near(w.mz, 0, 1e-2f), "sway +Y: force along +Y only");

  // Limits and servo pulses.
  c = Command{}; c.lift = 0; c.yaw = 1;
  check(near(angleDeg(c, 0), 90), "no lift, yaw: 90 deg (travel limit)");
  c = Command{}; c.lift = -1; c.yaw = 0.2f;
  check(angleDeg(c, 0) <= 90 && angleDeg(c, 0) >= -90, "push down is clamped to +-90");
  check(pulseUs(0) == 1500 && pulseUs(90) == 500 && pulseUs(-90) == 2500,
        "pulse: 0 -> 1500 us, gears reverse direction");

  std::printf("%s\n", failures ? "FAILED" : "all passed");
  return failures ? 1 : 0;
}
