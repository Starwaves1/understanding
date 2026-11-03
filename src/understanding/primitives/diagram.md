### diagram / node / edge — boxes and arrows inside the card
`{"op":"diagram","id":"d1"}` then stream nodes and edges one per line:
`{"op":"node","d":"d1","id":"in","label":"[18, 47]","sub":"input","col":0,"row":0,"tone":"blue"}`
`{"op":"node","d":"d1","id":"out","label":"56","sub":"target","col":1,"row":0,"tone":"orange"}`
`{"op":"edge","d":"d1","from":"in","to":"out","label":"predicts"}`
Place nodes on a grid with `col`/`row` (0-based, max 3 columns, max 5 rows). `label` ≤ 3 words or a short literal value; `sub` is an optional tiny caption above the box. `tone`: blue | orange | green | purple | gray (blue=input, orange=output/target, green=result). Emit a node before any edge that uses it.
