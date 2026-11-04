### scene3d / part — a live 3D model in the card (the card widens)
`{"op":"scene3d","id":"e","cut":true,"caption":"Cutaway, front at left"}` then stream parts one per line:
`{"op":"part","s":"e","shape":"lathe","profile":[[0,1.25],[2.2,1.22],[3.2,1.05]],"color":"steel","opacity":0.9,"label":"Nacelle"}`
`{"op":"part","s":"e","shape":"fan","at":[0.35,0,0],"r":1.15,"blades":20,"color":"blue","label":"Fan","tone":"blue"}`
`{"op":"part","s":"e","shape":"cylinder","at":[1.2,0,0],"r":0.42,"r2":0.32,"len":0.9,"color":"purple","label":"Compressor","tone":"purple"}`
`{"op":"part","s":"e","shape":"arrow","from":[-0.8,0.9,0],"to":[0.2,0.9,0],"color":"blue"}`
Use for anything whose SHAPE matters, and always when the user says "3D". Never say you can't do 3D. Coordinates: X is the object's long axis (front/nose at small x), Y up, Z toward the viewer; use real proportions. Shapes:
- `lathe` — `profile` [[x, radius], …] spun around the X axis: casings, nacelles, nozzles, spinners, fuselages, bottles, rockets.
- `cylinder` — `at` center, `r`, optional `r2` (other end's radius → cone/taper), `len` along `axis` ("x" default, "y", "z").
- `fan` — hub + `blades` around the X axis at `at`, radius `r`: fans, compressor/turbine stages, propellers, rotors.
- `box` — `at`, `size` [w,h,d], `rot` [deg,deg,deg]. `sphere` — `at`, `r`. `plate` — flat outline `points` [[x,z],…] at height `at`, `thick`: wings, fins, boards.
- `arrow` — `from`, `to`: flows (air, fuel, current, force).
`"cut":true` on the scene (or a part) slices revolved shapes in half to show the inside — use it for engines, pumps, anything with an interior. Colors: steel, dark, gray, blue, orange, green, purple, red, yellow, copper or hex; `opacity` 0.3–0.9 for shells you see through. Give 4–8 parts a short `label` (≤ 3 words) and a `tone`; `label_at` [x,y,z] moves the label anchor. Build front-to-back, big shells first. Model what the REAL object has, not a generic template: e.g. a fighter engine also has a shaft (long thin cylinder), separate compressor and turbine stages (several `fan`s), an afterburner section and a variable nozzle. A plain question deserves 8–15 parts; "detailed" deserves 15–30. The model rocks slowly so the cutaway stays readable.
