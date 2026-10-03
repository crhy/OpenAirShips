"""Airflow design analysis: impeller -> plenum -> 8 ducts -> stems -> air multipliers.

The chain is solved backwards from thrust, using the dimensions of the CAD
model (SimplifiedSlice/airship_slice.py and Propulsion/propulsion.py), and
writes AIRFLOW.md with every number it uses.

Model (per thruster; all 8 share the plenum, so each carries Q/8):
  Slot jet      V_j = Cv * sqrt(2 dp_slot / rho),  q_i = Cd * A_slot * V_j
  Thrust        T_i = phi * mdot_i * V_j   (phi = thrust augmentation of the
                entrained secondary flow; Coanda ejectors measure 1.1 to 1.6)
  Losses        dp = sum K * rho * v^2 / 2 over: duct entry, duct friction,
                duct bends, the dead-end turn into the stem, stem friction,
                and the stem's dump into the ring plenum
  Fan           static pressure  dp = psi_s * rho * u2^2
                (psi_s ~ 0.30 for an open, backward-curved impeller with no
                volute); air power = shaft power * eta_s
  Motor         shaft power = eta_m * V * I;  loaded speed ~ 0.8 * KV * V

Everything in SI units unless a name says otherwise.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "CAD Files", "SimplifiedSlice"))
sys.path.insert(0, os.path.join(HERE, "..", "CAD Files", "Propulsion"))
import airship_slice as hull      # noqa: E402
import propulsion as prop         # noqa: E402

# ---- air -------------------------------------------------------------------
RHO, MU = 1.204, 1.81e-5          # 20 C, sea level
RHO_H2 = 0.0838

# ---- coefficients (with the range we believe) ------------------------------
CD, CV = 0.85, 0.95               # slot discharge / velocity coefficients
PHI_AUG = 1.3                     # thrust augmentation (1.1 .. 1.6)
PSI_S = 0.30                      # fan static pressure coefficient (0.25 .. 0.40)
ETA_FAN = 0.42                    # fan static efficiency: printed impeller in the rev E shrouded housing
                                  # (0.35 .. 0.5; the open v0 impeller was ~0.35)
ETA_MOTOR = 0.75
K = dict(duct_entry=0.5, duct_bends=0.3, dead_end_turn=1.2,
         stem_entry=0.5, stem_dump=1.0)
ROUGH = 0.1e-3                    # printed-duct roughness, m
N_THR = 8
C_EYE_MAX = 22.0                  # m/s: keep the impeller inlet below this
C_PLENUM_MAX = 8.0                # m/s: radial velocity in the plenum

# ---- motor options -----------------------------------------------------------
MOTORS = {
    "A2212 1000KV, 3S": dict(kv=1000, volts=11.1, amps=15.0, grams=50),
    "A2212 1000KV, 4S": dict(kv=1000, volts=14.8, amps=15.0, grams=50),
    "A2212 1400KV, 3S": dict(kv=1400, volts=11.1, amps=18.0, grams=50),
    "2207 1750KV, 4S": dict(kv=1750, volts=14.8, amps=25.0, grams=32),
    "2207 2400KV, 4S": dict(kv=2400, volts=14.8, amps=35.0, grams=32),
}
V0 = dict(slot=0.8, stem=13.0, eye=22.0, b2=9.0, motor="A2212 1000KV, 3S")   # the first design
TIP_MAX = 75.0                    # m/s: rim speed limit for a printed (PETG) impeller

# ---- geometry from the CAD model --------------------------------------------
path = hull.duct_path()
DUCT_L = sum((b - a).Length for a, b in zip(path, path[1:])) / 1000
DUCT_D = hull.DUCT_BORE / 1000
DUCT_MOUTH_R = path[0].x / 1000
STEM_L = 0.030
SLOT_R = (prop.RT + prop.RC - 1.0) / 1000     # radius of the slot lip
D2 = 2 * prop.IMP_R2 / 1000
MOTOR_R = prop.MOTOR_D / 2 / 1000


def friction_factor(re, d):
    """Haaland's approximation (turbulent) or laminar."""
    if re < 2300:
        return 64 / max(re, 1)
    return (-1.8 * math.log10((ROUGH / d / 3.7) ** 1.11 + 6.9 / re)) ** -2


def path_losses(q_i, duct_d, stem_d):
    """Pressure lost between plenum and slot feed, for one thruster (Pa)."""
    a_d, a_s = math.pi * duct_d ** 2 / 4, math.pi * stem_d ** 2 / 4
    v_d, v_s = q_i / a_d, q_i / a_s
    qd, qs = RHO * v_d ** 2 / 2, RHO * v_s ** 2 / 2
    f_d = friction_factor(RHO * v_d * duct_d / MU, duct_d)
    f_s = friction_factor(RHO * v_s * stem_d / MU, stem_d)
    parts = {
        "duct entry": K["duct_entry"] * qd,
        "duct friction": f_d * DUCT_L / duct_d * qd,
        "duct bends": K["duct_bends"] * qd,
        "turn into stem": K["dead_end_turn"] * qs,
        "stem friction": f_s * STEM_L / stem_d * qs,
        "stem dump into ring": K["stem_dump"] * qs,
    }
    return parts, v_d, v_s


def solve(p_air, slot_w, duct_d=DUCT_D, stem_d=prop.STEM_ID / 1000, phi=PHI_AUG):
    """Operating point for a given air power delivered into the plenum."""
    a_slot = 2 * math.pi * SLOT_R * slot_w
    # all pressures scale with Q^2: find Q from Q * dp(Q) = p_air
    def total(q):
        q_i = q / N_THR
        v_j = q_i / (CD * a_slot)
        dp_slot = RHO * v_j ** 2 / (2 * CV ** 2)
        parts, v_d, v_s = path_losses(q_i, duct_d, stem_d)
        return dp_slot, parts, v_j, v_d, v_s
    lo, hi = 1e-5, 2.0
    for _ in range(100):
        q = math.sqrt(lo * hi)
        dp_slot, parts, *_ = total(q)
        if q * (dp_slot + sum(parts.values())) > p_air:
            hi = q
        else:
            lo = q
    dp_slot, parts, v_j, v_d, v_s = total(q)
    mdot = RHO * q
    thrust = phi * mdot * v_j
    return dict(q=q, dp_slot=dp_slot, parts=parts, dp=dp_slot + sum(parts.values()),
                v_j=v_j, v_d=v_d, v_s=v_s, thrust=thrust, a_slot=a_slot,
                jet_power=0.5 * mdot * v_j ** 2)


def solve_motor(m, slot_w, stem_d, phi=PHI_AUG, eta_fan=ETA_FAN, d2=D2):
    """Operating point limited by the motor's power *and* its loaded speed."""
    p_shaft, rpm_max = motor_limits(m)
    r = solve(p_shaft * eta_fan, slot_w, stem_d=stem_d, phi=phi)
    u2 = math.pi * d2 * rpm_max / 60
    dp_max = PSI_S * RHO * u2 ** 2
    limit = "power"
    if r["dp"] > dp_max:                          # speed-limited: back off the power
        lo, hi = 0.01, p_shaft * eta_fan
        for _ in range(60):
            mid = (lo + hi) / 2
            if solve(mid, slot_w, stem_d=stem_d, phi=phi)["dp"] > dp_max:
                hi = mid
            else:
                lo = mid
        r = solve(lo, slot_w, stem_d=stem_d, phi=phi)
        limit = "speed"
    r["limit"] = limit
    r["p_shaft_used"] = r["q"] * r["dp"] / eta_fan
    return r


def fan_for(dp, q, d2=D2):
    """Impeller speed and size needed to deliver dp at q."""
    u2 = math.sqrt(dp / (PSI_S * RHO))
    rpm = u2 / (math.pi * d2) * 60
    eye_r = math.sqrt(q / (math.pi * C_EYE_MAX) + MOTOR_R ** 2)
    b2 = q / (0.25 * math.pi * d2 * u2)          # exit width at flow coefficient 0.25
    return dict(u2=u2, rpm=rpm, eye_r=eye_r, b2=b2)


def motor_limits(m):
    p_shaft = ETA_MOTOR * m["volts"] * m["amps"]
    return p_shaft, 0.8 * m["kv"] * m["volts"]


def report():
    out = []
    w = out.append
    w("# Airflow analysis: impeller, ducts and air-multiplier thrusters\n")
    w("Generated by `airflow.py` from the current CAD dimensions. Rerun it after changing the model.\n")
    w("## Inputs\n")
    w(f"- Air: ρ = {RHO} kg/m³ (20 °C, sea level).")
    w(f"- **Ducts:** 8 × Ø{DUCT_D*1000:.0f} mm, {DUCT_L*1000:.0f} mm long, with the mouth at r = {DUCT_MOUTH_R*1000:.0f} mm on the keel.")
    w(f"- **Stem bore:** Ø{prop.STEM_ID:.0f} mm.")
    w(f"- **Air-multiplier slot:** at a radius of {SLOT_R*1000:.0f} mm, {prop.SLOT} mm wide in rev E.")
    w(f"- **Impeller:** Ø{D2*1000:.0f} mm, eye (blade inlet) radius {prop.IMP_R1:.0f} mm, blade height {prop.blade_top(prop.IMP_R1) - prop.IMP_PLATE_TOP:.0f}→{prop.IMP_B2:.0f} mm, running {prop.hull.SHROUD_GAP} mm under the housing's stationary shroud.")
    w(f"- **Coefficients (the main uncertainties):**")
    w(f"  - slot C_d = {CD}, C_v = {CV}")
    w(f"  - thrust augmentation φ = {PHI_AUG} (published Coanda ejectors: 1.1–1.6)")
    w(f"  - fan static pressure coefficient ψ = {PSI_S}, fan static efficiency η = {ETA_FAN}")
    w(f"  - motor efficiency {ETA_MOTOR}")
    w(f"  - loss coefficients K: {', '.join(f'{k.replace(chr(95), chr(32))} {v}' for k, v in K.items())}\n")

    # weight to lift
    weights = dict(hull=390, printed_propulsion=250, motor=50, servos=8 * 13.4,
                   esc=25, electronics=35, wiring=30)
    wt = sum(weights.values())
    lift_h2 = 12.74e-3 * (RHO - RHO_H2) * 1000
    w("## 1. What would hovering take?\n")
    w(f"- **Estimated all-up mass:** {wt:.0f} g ({', '.join(f'{k.replace(chr(95), chr(32))} {v:.0f}' for k, v in weights.items())}).")
    w(f"- **Hydrogen lift:** the 12.7 L above the main deck gives {lift_h2:.0f} g, so thrust has to carry about {wt - lift_h2:.0f} g, i.e. {(wt - lift_h2) * 9.81e-3:.1f} N.")
    t_hover = (wt - lift_h2) * 9.81e-3
    w("- **Jet speed sets the airflow needed:** thrust is φ·ṁ·V_j and jet power is ½ṁV_j², so a slower jet needs less power but more airflow.\n")
    w("| Jet speed V_j (m/s) | Air flow needed (L/s) | Jet power (W) | Slot area per thruster (mm²) | Duct speed in Ø24 (m/s) |")
    w("|---|---|---|---|---|")
    for vj in (15, 25, 40, 60):
        mdot = t_hover / (PHI_AUG * vj)
        q = mdot / RHO
        w(f"| {vj} | {q*1000:.0f} | {0.5*mdot*vj**2:.0f} | {q/N_THR/(CD*vj)*1e6:.0f} | {q/N_THR/(math.pi*DUCT_D**2/4):.0f} |")
    w("")
    w("**Conclusion: hovering on fan thrust isn't feasible at this scale.**")
    w("- **Slow jets:** below about 25 m/s the airflow runs to hundreds of L/s. That needs ducts of Ø60 mm or more and an impeller eye bigger than the whole shaft.")
    w("- **Fast jets:** above 40 m/s the jet power alone is over 100 W, before any losses. With fan and motor efficiency, the motor would need more than 400 W.")
    w("- **So the bench demo's job is to show controlled, vectored thrust, not to hover.**\n")

    w("## 2. The first design, v0 (0.8 mm slot, Ø13 stem)\n")
    rows = []
    for name, m in list(MOTORS.items())[:2]:
        p_shaft, rpm_max = motor_limits(m)
        r = solve_motor(m, V0["slot"] / 1000, V0["stem"] / 1000)
        f = fan_for(r["dp"], r["q"])
        rows.append((name, p_shaft, r, f, rpm_max))
    w("| Motor | Limited by | Shaft W used | Flow L/s | Plenum pressure Pa | Jet m/s | Stem m/s | Thrust N (gf) | Fan rpm |")
    w("|---|---|---|---|---|---|---|---|---|")
    for name, p_shaft, r, f, rpm_max in rows:
        w(f"| {name} | {r['limit']} | {r['p_shaft_used']:.0f} of {p_shaft:.0f} | {r['q']*1000:.1f} | {r['dp']:.0f} | {r['v_j']:.0f} | {r['v_s']:.0f} | "
          f"{r['thrust']:.2f} ({r['thrust']/9.81e-3:.0f}) | {f['rpm']:.0f} |")
    r = rows[0][2]
    w("\nWhere the pressure goes (3S case):\n")
    w("| Item | Pa | Share |")
    w("|---|---|---|")
    w(f"| slot (useful: makes the jet) | {r['dp_slot']:.0f} | {r['dp_slot']/r['dp']*100:.0f} % |")
    for k, v in r["parts"].items():
        w(f"| {k} | {v:.0f} | {v/r['dp']*100:.0f} % |")
    w("")
    w("**Findings:**")
    w("1. **Fan speed, not motor power, is the limit.** On an 88 mm open impeller, the A2212's loaded speed caps the plenum pressure (about 600 Pa on 3S, about 1,070 Pa on 4S) before the motor reaches its power.")
    w("2. **The 0.8 mm slot makes a small, fast jet** that spends its power on speed rather than on moving air.")
    w(f"3. **The Ø{V0['stem']:.0f} mm stem is a choke:** air in it moves about as fast as in the slot, so it throws away a similar amount of pressure.")
    w("")

    # ---- design sweep -------------------------------------------------------
    w("## 3. Design sweep: slot width, stem bore, battery\n")
    w("Each row is limited by whichever runs out first: the motor's power or its loaded speed on an 88 mm impeller. The impeller eye and exit width it would need are listed too.\n")
    w("| Motor | Slot mm | Stem Ø mm | Limited by | Flow L/s | Plenum Pa | Jet m/s | Thrust N (gf) | Fan rpm | Eye r mm | b2 mm |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    best = None
    for name, m in MOTORS.items():
        for slot in (0.8, 1.2, 1.6, 2.0, 2.5):
            for stem in (18, 22):
                r = solve_motor(m, slot / 1000, stem / 1000)
                f = fan_for(r["dp"], r["q"])
                ok = (f["eye_r"] * 1000 <= prop.IMP_R2 - 10 and f["b2"] * 1000 <= 20
                      and f["u2"] <= TIP_MAX)
                w(f"| {name} | {slot} | {stem} | {r['limit']} | {r['q']*1000:.0f} | {r['dp']:.0f} | {r['v_j']:.0f} | "
                  f"{r['thrust']:.2f} ({r['thrust']/9.81e-3:.0f}) | {f['rpm']:.0f}{'' if f['u2'] <= TIP_MAX else ' ✗'} | "
                  f"{f['eye_r']*1000:.0f}{'' if f['eye_r']*1000 <= prop.IMP_R2 - 10 else ' ✗'} | "
                  f"{f['b2']*1000:.0f}{'' if f['b2']*1000 <= 20 else ' ✗'} |")
                if ok and (best is None or r["thrust"] > best[0]["thrust"] + 1e-3):
                    best = (r, f, slot, stem, name)
    w(f"\n✗ = doesn't fit or isn't safe:")
    w(f"- the impeller eye must stay 10 mm inside the 44 mm rim")
    w(f"- the exit width is limited to 20 mm by the plenum height over the impeller")
    w(f"- the rim speed must stay ≤ {TIP_MAX:.0f} m/s for a printed impeller (PETG). The 2207 2400KV would make more thrust, but only above that speed.\n")

    r, f, slot, stem, mname = best
    m = MOTORS[mname]
    w("## 4. Recommended design point\n")
    w(f"The best feasible combination in the sweep: **{mname}**.\n")
    w(f"| | v0 | Recommended (built into rev E) |")
    w(f"|---|---|---|")
    w(f"| Air-multiplier slot | {V0['slot']} mm | **{slot} mm** |")
    w(f"| Stem bore | Ø{V0['stem']:.0f} mm | **Ø{stem} mm** (stem hole in the hull grows to Ø{stem + 3.4:.0f}) |")
    w(f"| Duct bore | Ø{DUCT_D*1000:.0f} mm | Ø{DUCT_D*1000:.0f} mm along its length (duct speed {r['v_d']:.0f} m/s: friction is negligible), "
      f"**flared to about Ø{stem + 10} mm over its last 25 mm** so the wider stem enters it cleanly |")
    w(f"| Impeller eye radius | {V0['eye']:.0f} mm | **{math.ceil(f['eye_r']*1000):.0f} mm** (inlet speed ≤ {C_EYE_MAX:.0f} m/s) |")
    w(f"| Impeller exit width b2 | {V0['b2']:.0f} mm | **{math.ceil(f['b2']*1000):.0f} mm** |")
    w(f"| Motor / battery | {V0['motor']} | **{mname}** |")
    w(f"| Fan speed | — | **{f['rpm']:.0f} rpm** (tip speed {f['u2']:.0f} m/s); motor shaft power used {r['p_shaft_used']:.0f} W, "
      f"about {r['p_shaft_used']/ETA_MOTOR/m['volts']:.0f} A at {m['volts']} V |")
    w(f"| Airflow | — | {r['q']*1000:.0f} L/s total, {r['q']*1000/N_THR:.1f} L/s per thruster |")
    w(f"| Plenum pressure | — | {r['dp']:.0f} Pa |")
    w(f"| Jet speed | — | {r['v_j']:.0f} m/s |")
    w(f"| **Total thrust** | — | **{r['thrust']:.2f} N ≈ {r['thrust']/9.81e-3:.0f} gf** ({r['thrust']/9.81e-3/N_THR:.0f} gf per thruster) |")
    lo = solve_motor(m, slot / 1000, stem / 1000, phi=1.1, eta_fan=0.35)["thrust"]
    hi = solve_motor(m, slot / 1000, stem / 1000, phi=1.6, eta_fan=0.50)["thrust"]
    w(f"\n**Uncertainty:** with φ between 1.1 and 1.6 and fan efficiency between 0.35 and 0.50, the thrust range is **{lo/9.81e-3:.0f}–{hi/9.81e-3:.0f} gf**. Measure φ and the fan curve on the bench, then rerun.\n")

    # ---- plenum -------------------------------------------------------------
    w("## 5. Plenum (fan chamber) sizing\n")
    q = r["q"]
    w(f"The plenum only has to carry {q*1000:.0f} L/s from the impeller rim (r = {prop.IMP_R2:.0f} mm) out to the duct mouths (r ≈ {DUCT_MOUTH_R*1000:.0f} mm), keeping the radial speed under {C_PLENUM_MAX:.0f} m/s:\n")
    w("| Radius mm | Height needed mm |")
    w("|---|---|")
    for rr in (44, 55, 65, DUCT_MOUTH_R * 1000):
        w(f"| {rr:.0f} | {q / (2 * math.pi * rr / 1000 * C_PLENUM_MAX) * 1000:.0f} |")
    w("")
    w(f"- **Impeller height:** the recommended impeller is about {math.ceil(f['b2']*1000)+2:.0f} mm tall at the rim, so the chamber needs about that height over the impeller (r ≤ {prop.IMP_R2:.0f} mm). The current floor at z = −70 above a keel at about −101 gives 31 mm there. That's enough, so **the floor can't come down much over the impeller**.")
    w("- **Shrouded fan:** the housing is the fan's shroud. The intake shaft is the impeller eye's diameter (Ø66) all the way up. Its wall turns over the blade tips with 1.5 mm clearance and runs out as the housing ceiling. (Up to v0 the shaft was Ø95 and narrowed at the bottom; it only had to be that wide for the impeller to drop in from the top, and the impeller now comes in through the keel hatch.)")
    w("  - The narrower intake speeds the air up from about 9 to about 18 m/s. With the bellmouth that costs about 20 Pa, around 1% of the fan pressure, and it gives the gas cells about 0.6 L more room.")
    w("  - In the open design there was a 3.4 mm annulus between the impeller tip and the shaft wall, right at the housing's highest-pressure point, so housing air leaked straight back up the shaft. The shroud closes it, and air can only leave through the ducts.")
    for e in (0.35, ETA_FAN, 0.50):
        t_ = solve_motor(m, slot / 1000, stem / 1000, eta_fan=e)["thrust"]
        w(f"  - fan efficiency {e:.2f}: {t_:.2f} N ≈ {t_/9.81e-3:.0f} gf")
    w(f"  - This analysis uses η = {ETA_FAN} for the shrouded housing (0.35 was the open impeller's estimate). Measure it on the bench.")
    w(f"- **As built (v0.2.1, flush mouths):** the ceiling is flat over the blade tips, then eases down to meet the ducts' tops at their mouths. The keel skin is the floor, and the ducts hug the hull curve from their mouths, so each duct runs straight on from the housing, flush top and bottom. The outer wall stands just past the mouths, at r = {hull.PLENUM_FLAT_R:.1f} mm. The duct mouths sit at r ≈ {DUCT_MOUTH_R*1000:.0f} mm, just outside the impeller tip.")
    w("  - The keel is solid only under this housing, out to its outer wall, and a removable bayonet hatch closes the middle and carries the motor. Outside it the skin is the oval lattice, right up to the wall; the ducts carry the air from there, and their own walls keep it airtight.")
    w("  - The intake mouth at the top is a rounded bellmouth (the skin rolls into the shaft over a 12 mm radius), which keeps the entry loss small. The shaft has no ledge or spider in it: the motor stands on the fan hatch.\n")

    w("## 6. What to measure on the bench\n")
    w("1. **Fan curve:** plenum pressure (MPXV7002DP) and motor power (INA226) against throttle, with the thrusters blanked off and then open.")
    w("2. **Thrust augmentation φ:**")
    w("   - thrust of one thruster on the scale, with the ring fitted and with a bare stem of the same flow")
    w("   - slot exit speed from a pitot tube, or from Q/A")
    w("3. **Losses:** pressure at the stem inlet against the plenum. This checks the duct and turn losses.")
    w("4. **Rerun:** put the measured coefficients into `airflow.py` and rerun it before cutting new parts.")
    open(os.path.join(HERE, "AIRFLOW.md"), "w").write("\n".join(out) + "\n")
    return best


if __name__ == "__main__":
    r, f, slot, stem, mname = report()
    print(f"best: {mname}, slot {slot} mm, stem {stem} mm -> {r['thrust']:.2f} N at {f['rpm']:.0f} rpm, "
          f"Q {r['q']*1000:.0f} L/s, dp {r['dp']:.0f} Pa, eye r {f['eye_r']*1000:.1f} mm, b2 {f['b2']*1000:.1f} mm")
