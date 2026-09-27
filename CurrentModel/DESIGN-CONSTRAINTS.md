# Design constraints (fixed rules for every revision)

These rules come from the design owner. Don't trade any of them away for weight or print time without asking first.

## Navigation
- **The thrusters sit exactly on the equator (z = 0), the vertical midpoint of the hull.** This is required for navigation: thrust at the midpoint gives yaw, surge and sway without pitching or rolling the ship. The stem/swivel axis is on the equator ring rib (`OUT_Z = 0` in `airship_slice.py`, which asserts a rib there). Don't move the thrusters up or down to shorten the ducts.

## Air path
- **The central intake shaft stays solid and smooth over its whole height.** Air drawn over the top of the hull and down the shaft gives the craft its Coanda flow, and windows or obstructions in the shaft ruin it.
  - No windows in the shaft wall.
  - Nothing inside the shaft bore: no ledges, spiders or wires. The motor stands on a pedestal on the keel, below the fan.
  - The top of the intake is a rounded bellmouth where the hull skin rolls into the shaft.
- **The fan housing (plenum) and the ducts are airtight.** The keel is solid only under the fan housing. Everywhere else the structure is lattice, and the ducts' own walls carry the air.
- **The ducts never get smaller** (Ø24 mm bore, ending in a Ø32 bulb and a Ø22 stem). Only their walls are thinned, to the printable minimum.

## Outside shape
- **The hull's outside is a smooth ellipsoid (207.765 × 104 mm semi-axes).** The pipes and ducts run inside it. Only the thruster stems and servo gear hubs pass through round holes in the skin, and only the 5 joint pegs per slice stick out, into the neighbouring slice.

## Weight and printing (Prusa MK3S+, 0.4 mm nozzle)
- **Walls are 0.86 mm** (2 perimeters of 0.45 mm at 0.2 mm layers). That's the minimum that prints airtight, and nothing structural is thinner. Ribs are 2.0 mm wide.
- **Anything that isn't structurally essential is hollow.** The skin is two columns of large oval cells, and every junction is a hollow diamond. The seam junctions are hollow half-diamonds, which stop short of a continuous 1 mm edge strip so the seams stay contiguous.
- **No decks in the bench model.** The only floor is the fan-housing ceiling.
- **8 identical slices plug together**, with pegs on the +22.5° seam and holes on the −22.5° seam.
- **Service:** the 88 mm impeller must drop through the 94.75 mm shaft from the top.

## Scope
- The bench model is the smallest and hardest prototype to fly: lift grows with size³ and structure only with size². Hydrogen ballonets and hover are deferred to a larger model (see `OPEN-QUESTIONS.md`).
