### scene3d / part — a live, realistically lit 3D model in the card
Use whenever SHAPE matters, and always when the user says "3D". Never say you can't do 3D.
`{"op":"scene3d","id":"a","caption":"F-86 Sabre, nose at left"}` then stream `part` ops one per line (`"s"` = scene id).
Coordinates: X = the object's long axis (nose/front at x=0, increasing toward the back), Y up, Z sideways (left/right; symmetric objects are centered on z=0). Use real proportions in any unit (e.g. meters ÷ 2).

Shapes, best first:
- `fuselage` — smooth body through cross-sections `sections` [[x, halfWidth, halfHeight, yCenter], …], 5–10 of them, starting and ending small (≈0.02) for a pointed/closed end. `squareness` 2 = round, 3–4 = boxy. For aircraft bodies, canopies (`color:"glass"`), pods, fish, cars, ship hulls.
- `wing` — airfoil surface. `root` [x,y,z] = leading edge at the root; `span` outward; `root_chord`, `tip_chord`; `sweep` (leading-edge degrees back), `dihedral` (degrees up, negative = droop), `thickness` (0.04–0.12 of chord). Horizontal wings are automatically MIRRORED to both sides — give the right-hand one only (z ≥ 0). `"vertical":true` → a fin rising along +y (not mirrored unless `mirror:true`; `cant` tilts twin fins outward). Wings, tailplanes, fins, canards, rudders, propeller-less blades.
- `lathe` — `profile` [[x, radius], …] spun around the X axis; `"smooth":true` for curved profiles (nose cones, domes, bottles). Rockets, missiles, engine casings, nozzles, tanks. Prefer ONE continuous lathe for a body of revolution over several pieces.
- `cylinder` — `at` center, `r`, optional `r2` (other end's radius), `len` along `axis` ("x" default, "y", "z"); solid unless `"hollow":true`.
- `fan` — hub + `blades` around the X axis at `at`, radius `r`: fans, compressor/turbine stages, propellers, rotors.
- `box` — `at`, `size` [w,h,d], `rot` [deg,deg,deg]. `sphere` — `at`, `r`. `plate` — flat outline `points` [[x,z],…] at `at`, `thick`.
- `arrow` — `from`, `to`: flows (air, exhaust, fuel, force).

Parts must TOUCH: compute each part's position from the parts it attaches to (a wing root sits on the fuselage surface; a nozzle starts where the casing ends). Colors: silver, gunmetal, steel, white, black, navy, olive, sand, glass, rubber, copper, blue, orange, green, red, yellow or hex; `"metal":true` for bare metal; `opacity` 0.3–0.8 for see-through shells. `"cut":true` on the scene (or a part) slices revolved shapes and fuselages in half to show the inside — use it for engines, rockets, pumps. Give 4–8 parts a short `label` (≤ 3 words) and a `tone`; `label_at` [x,y,z] moves the anchor. Big shapes first, then details. A plain request: 6–12 parts; "detailed": 12–30.

Example, an aircraft (right wing only — it is mirrored):
`{"op":"part","s":"a","shape":"fuselage","sections":[[0,0.02,0.02,0],[0.8,0.3,0.32,0],[2.5,0.55,0.6,0.05],[6,0.55,0.55,0.1],[8,0.3,0.32,0.2]],"color":"silver","metal":true,"label":"Fuselage"}`
`{"op":"part","s":"a","shape":"wing","root":[2.8,-0.2,0.5],"span":3.2,"root_chord":2.2,"tip_chord":0.9,"sweep":35,"dihedral":3,"color":"silver","metal":true,"label":"Swept wing"}`
`{"op":"part","s":"a","shape":"wing","root":[6.6,0.4,0],"vertical":true,"span":1.5,"root_chord":1.5,"tip_chord":0.6,"sweep":45,"color":"silver","metal":true,"label":"Fin"}`
Example, a rocket in one smooth piece plus a nozzle that touches it:
`{"op":"part","s":"r","shape":"lathe","smooth":true,"profile":[[0,0.01],[0.6,0.35],[1.4,0.5],[8,0.5]],"color":"white","label":"Casing"}`
`{"op":"part","s":"r","shape":"lathe","profile":[[8,0.3],[8.3,0.22],[9.2,0.45]],"color":"gunmetal","metal":true,"label":"Nozzle"}`
