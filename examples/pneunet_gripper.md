# Example 2 — PneuNet two-finger gripper

Native-Grasshopper pneunet: chamber sizes and finger profile driven by
Graph Mappers, meshed with TriRemesh, cavities become internal voids
automatically (SofaBody.hollow, default on) — no boolean difference
anywhere. One finger designed flat, oriented twice into a gripper,
carried by a SofaProtocol pick-and-place.

## Stage A — finger body (Graph Mapper #1 = overall profile)

1. Range (0→1, 19 steps) → t
2. Graph Mapper #1 (Bezier) ← t — finger height along length
3. Remap Numbers → 10→14 = section heights h
4. Construct Point (90·t, 0, 0) → YZ Plane at each station
5. Rectangle on those planes: X domain −8→8, Y domain 0→h
6. Loft (Normal) → Cap Holes → solid finger Brep (L 90, W 16)

## Stage B — chamber network (Graph Mapper #2 = chamber sizes)

7. Series: start 12, step 9.5, count 8 → chamber x positions
8. Range(0→1, 8) → Graph Mapper #2 → Remap 5→9 → chamber heights h_i
9. Construct Point (x_i, 0, 3 + h_i/2) → Center Box X 2.75 / Y 6 / Z h_i/2
   (5.5 × 12 × h_i chambers; 2 mm side walls, sits above the 2 mm
   bottom layer)
10. Channel: Center Box at (45, 0, 4), X 38 / Y 2 / Z 1.5
11. Solid Union (chambers + channel) → one cavity-network Brep

## Stage C — meshes (native refinement showcase)

12. TriRemesh (finger Brep, TargetLength ≈ 2.5) → SofaBody.geo
13. TriRemesh (cavity Brep, TargetLength ≈ 2) → SofaCavity.geo
    TargetLength sliders = FEM surface resolution, fully native.

## Stage D — single-finger inflation test

* SofaCavity: mesh 13, channel 1
* SofaRegion: Center Box (45, 0, 1) X 46 / Y 9 / Z 1.3, E 2000
  (strain-limiting bottom layer — the pneunet bends instead of
  ballooning; MU-membrane mechanism)
* SofaBody: geo 12, name finger1, E 80, nu 0.4, mass 0.02,
  meshSize 0.4, fixation Center Box (3, 0, 7) 4/9/8, monitorPts
  (x, 0, 13) x = 15…85, exportShape 10
* PressureProfile ch1: [0, 2] / [0, 60]
* SofaScene gravityZ 0 → write → SetupPreview (voids visible in the
  tet surface, slab at bottom, box swallowing the base) → SofaRun GUI
* Success: finger curls toward the bottom layer. More curl: pressure up
  or thinner top walls. Ballooning: region E up.

## Stage E — gripper assembly

* SofaBody ×2 (finger1/finger2, same geo/cavity/region wires), each
  with an Orient component: World XY → vertical plane, fingertip down,
  bottom layer facing the object, gap ≈ 20 mm.
* collisionGeo on both fingers (the TriRemesh mesh).
* SofaProtocol (both bodies): times [0, 1, 2.5, 3.5],
  offsets (0,0,0) (0,0,−30) (0,0,−30) (0,0,30) — down, hold, lift.
* PressureProfile ch1 (both cavities on ch1):
  times [0, 1, 1.2, 2.3, 4], values [0, 0, 55, 55, 55] — inflate
  during the hold, keep gripping through the lift.
* SofaTarget: Sphere r 12 at the grasp point, mass 0.01.
* SofaScene: floorZ at the sphere's resting height, gravityZ −9810.
* Results: SofaShape frame slider for the grasp playback (GIF),
  SofaResults pressures + fingertip trajectories.

## Tuning notes

* Chamber walls ≥ 2 mm and TriRemesh TargetLength ≤ wall thickness —
  at least ~2 elements through the membrane.
* Target slips: raise pressure, narrow the gap, or soften fingers.
* Target flies away on contact: slow the protocol descent, lower mass
  asymmetry, check the floor catches it.
