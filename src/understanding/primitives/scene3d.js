// Live 3D scenes built from streamed parts. Needs THREE (web/vendor/three.min.js).
U.css(`
.card.wide3d { --card-w: 760px; }
.scene3d { position: relative; height: 430px; margin: 6px -8px; border-radius: 10px; overflow: hidden;
  background: radial-gradient(ellipse at 50% 40%, #ffffff 0%, #f1ece0 70%); }
.scene3d canvas { display: block; width: 100%; height: 100%; }
.scene3d .lbl { position: absolute; transform: translate(-50%, -100%); white-space: nowrap; pointer-events: none;
  font-family: var(--hand); font-weight: 700; font-size: 13.5px; color: var(--ink); background: rgba(255,255,255,.92);
  border-left: 3px solid var(--tone, var(--green)); padding: 1px 7px; border-radius: 5px;
  box-shadow: 0 2px 8px rgba(0,0,0,.18); animation: fade .4s both; }
.scene3d svg.leaders { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
.scene3d svg.leaders line { stroke: #2b2a27; stroke-width: 1.3; }
.scene3d svg.leaders circle { fill: #fff; stroke: #2b2a27; stroke-width: 1.5; }
.scene3d .cap { position: absolute; left: 0; right: 0; bottom: 6px; text-align: center; font-size: 12px; color: var(--muted); }
`);

(() => {
  const NAMED = { blue: "#3d7fd9", orange: "#e8833a", green: "#3a9d5d", purple: "#8a5cd6", gray: "#9a958a",
    steel: "#b8bcc4", dark: "#4a4d55", red: "#d9534f", yellow: "#f0b429", copper: "#c8763a",
    white: "#f2f2ee", black: "#2a2b2e", silver: "#c3c7cd", gunmetal: "#5b6168", navy: "#2f4166",
    olive: "#6b7a4b", sand: "#c9b78f", glass: "#6fa8dc", rubber: "#30302e" };
  const color = (c, dflt = "#b8bcc4") => new THREE.Color(NAMED[c] || c || dflt);
  const deg = (v) => ((+v || 0) * Math.PI) / 180;
  const v3 = (a, d = [0, 0, 0]) => new THREE.Vector3(...(Array.isArray(a) && a.length === 3 ? a.map(Number) : d));

  // Revolved shapes are built around +Y by three.js; rotate them onto the X axis
  // (our convention: X = the object's long axis, front at small x).
  const ALONG = { x: [0, 0, -Math.PI / 2], y: [0, 0, 0], z: [Math.PI / 2, 0, 0] };
  function orient(mesh, axis) {
    const r = ALONG[axis || "x"] || ALONG.x;
    mesh.rotation.set(...r);
  }

  function material(op, S) {
    return new THREE.MeshStandardMaterial({
      color: color(op.color), metalness: op.metal ? 0.75 : 0.2, roughness: op.metal ? 0.3 : 0.45,
      side: THREE.DoubleSide, transparent: op.opacity != null, opacity: op.opacity ?? 1,
    });
  }

  // Cutaways keep the far half (z <= 0) so the camera (+z) looks into the open side.
  // three.js revolves with z = r·cos(phi), so phi in [π/2, 3π/2].
  const sweep = (S, op) => (op.cut ?? S.cut ? [Math.PI / 2, Math.PI] : [0, Math.PI * 2]);

  const BUILD = {
    lathe(op, S) {
      // profile: [[x, radius], ...] along the long axis
      let pts = (op.profile || []).map(([x, r]) => new THREE.Vector2(Math.max(0.001, +r), +x));
      if (pts.length < 2) return null;
      // "smooth": spline through the profile (nose cones, bottles, domes) instead of straight segments.
      if (op.smooth && pts.length >= 3) pts = new THREE.SplineCurve(pts).getPoints(pts.length * 16);
      const [t0, tl] = sweep(S, op);
      const m = new THREE.Mesh(new THREE.LatheGeometry(pts, 96, t0, tl), material(op, S));
      orient(m, op.axis);
      m.position.copy(v3(op.at));
      return m;
    },
    cylinder(op, S) {
      const r = +op.r || 0.5, r2 = op.r2 != null ? +op.r2 : r, len = +op.len || 1;
      const [t0, tl] = sweep(S, op);
      const m = new THREE.Mesh(new THREE.CylinderGeometry(r2, r, len, 72, 1, !!op.hollow, t0, tl), material(op, S));
      orient(m, op.axis);
      m.position.copy(v3(op.at));
      return m;
    },
    fan(op, S) {
      // Hub + blades in the plane perpendicular to the long axis.
      const g = new THREE.Group(), r = +op.r || 1, n = Math.min(40, +op.blades || 16);
      const mat = material(op, S);
      const [h0, hl] = sweep(S, op);
      g.add(new THREE.Mesh(new THREE.CylinderGeometry(r * 0.22, r * 0.22, r * 0.25, 32, 1, false, h0, hl), mat));
      for (let i = 0; i < n; i++) {
        const a = (i / n) * Math.PI * 2;
        if ((op.cut ?? S.cut) && Math.cos(a) > 0.05) continue; // cutaway: keep the far half
        // Group space: hub axis is local Y (rotated onto world X below), so blades
        // fan out in the local X–Z plane; each blade's long side points radially.
        const blade = new THREE.Mesh(new THREE.BoxGeometry(r * 0.16, r * 0.05, r * 0.78), mat);
        blade.position.set(Math.sin(a) * r * 0.6, 0, Math.cos(a) * r * 0.6);
        blade.rotation.set(0, a, 0);
        blade.rotateZ(0.5); // blade twist
        g.add(blade);
      }
      g.rotation.set(0, 0, -Math.PI / 2);
      if (op.axis && op.axis !== "x") orient(g, op.axis);
      g.position.copy(v3(op.at));
      return g;
    },
    fuselage(op, S) {
      // Smooth body lofted through cross-sections [x, halfWidth, halfHeight, yCenter?].
      const st = (op.sections || []).map((q) => q.map(Number)).filter((q) => q.length >= 3).sort((a, b) => a[0] - b[0]);
      if (st.length < 2) return null;
      const P = (i) => new THREE.Vector3(st[i][0], Math.max(0.001, st[i][1]), Math.max(0.001, st[i][2]));
      const shape = new THREE.CatmullRomCurve3(st.map((_, i) => P(i)), false, "centripetal");
      const yc = new THREE.CatmullRomCurve3(st.map((q) => new THREE.Vector3(q[0], q[3] || 0, 0)), false, "centripetal");
      const N = Math.min(240, st.length * 24), R = 72, e = 2 / Math.max(1.5, +op.squareness || 2.2);
      const cut = op.cut ?? S.cut, th0 = cut ? Math.PI / 2 : 0, thl = cut ? Math.PI : Math.PI * 2;
      const pos = [], idx = [];
      for (let i = 0; i <= N; i++) {
        const a = shape.getPoint(i / N), c = yc.getPoint(i / N).y;
        for (let j = 0; j <= R; j++) {
          const t = th0 + (j / R) * thl, sn = Math.sin(t), cs = Math.cos(t);
          pos.push(a.x, c + a.z * Math.sign(sn) * Math.abs(sn) ** e, a.y * Math.sign(cs) * Math.abs(cs) ** e);
        }
      }
      for (let i = 0; i < N; i++)
        for (let j = 0; j < R; j++) {
          const k = i * (R + 1) + j;
          idx.push(k, k + R + 1, k + 1, k + 1, k + R + 1, k + R + 2);
        }
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
      g.setIndex(idx);
      g.computeVertexNormals();
      const m = new THREE.Mesh(g, material(op, S));
      m.position.copy(v3(op.at));
      return m;
    },
    wing(op, S) {
      // Airfoil-section surface: leading-edge root at `root`, extends `span` outward (+z,
      // or +y when vertical), swept back by `sweep`°, tapered root_chord→tip_chord,
      // tilted by `dihedral`°. Horizontal wings are mirrored across z=0 by default.
      const span = +op.span || 2, rc = +op.root_chord || 1.5, tc = op.tip_chord != null ? +op.tip_chord : rc * 0.4;
      const sw = deg(op.sweep ?? 30), dih = deg(op.dihedral || 0), th = +op.thickness || 0.06;
      const vertical = !!op.vertical, [rx, ry, rz] = (op.root || op.at || [0, 0, 0]).map(Number);
      const C = 28, K = 8, pos = [], idx = [];
      const xs = [...Array(C + 1)].map((_, i) => 0.5 * (1 - Math.cos((Math.PI * i) / C))); // cosine spacing
      const yt = (x) => 5 * th * (0.2969 * Math.sqrt(x) - 0.126 * x - 0.3516 * x * x + 0.2843 * x ** 3 - 0.1036 * x ** 4);
      const ring = [...xs.map((x) => [x, yt(x)]), ...xs.slice(1, -1).reverse().map((x) => [x, -yt(x)])]; // closed airfoil
      for (let k = 0; k <= K; k++) {
        const s = k / K, c = rc + (tc - rc) * s, d = s * span, le = rx + d * Math.tan(sw);
        for (const [x, t] of ring) {
          const px = le + x * c, thick = t * c;
          if (vertical) pos.push(px, ry + d, rz + thick);
          else pos.push(px, ry + d * Math.sin(dih) + thick, rz + d * Math.cos(dih));
        }
      }
      const n = ring.length;
      for (let k = 0; k < K; k++)
        for (let j = 0; j < n; j++) {
          const a = k * n + j, b = k * n + ((j + 1) % n);
          idx.push(a, a + n, b, b, a + n, b + n);
        }
      // tip cap (fan around the tip section's first vertex)
      const tip = K * n;
      for (let j = 1; j < n - 1; j++) idx.push(tip, tip + j, tip + j + 1);
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
      g.setIndex(idx);
      g.computeVertexNormals();
      const mat = material(op, S), grp = new THREE.Group(), half = new THREE.Mesh(g, mat);
      grp.add(half);
      if (op.cant) half.rotateX(-deg(op.cant)); // twin fins leaning outward
      if (op.mirror ?? !vertical) {
        const other = half.clone();
        other.scale.z = -1; // three.js flips winding for negative scale, so lighting stays correct
        if (op.cant) other.rotation.x = deg(op.cant);
        grp.add(other);
      }
      return grp;
    },
    box(op, S) {
      const [w, h, d] = (op.size || [1, 1, 1]).map(Number);
      const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), material(op, S));
      m.position.copy(v3(op.at));
      const [rx, ry, rz] = op.rot || [0, 0, 0];
      m.rotation.set(deg(rx), deg(ry), deg(rz));
      return m;
    },
    sphere(op, S) {
      const m = new THREE.Mesh(new THREE.SphereGeometry(+op.r || 0.5, 64, 32), material(op, S));
      m.position.copy(v3(op.at));
      return m;
    },
    plate(op, S) {
      // Flat outline in the X–Z plane (wings, fins), extruded by `thick`.
      const pts = op.points || [];
      if (pts.length < 3) return null;
      const shape = new THREE.Shape(pts.map(([x, z]) => new THREE.Vector2(+x, +z)));
      const geo = new THREE.ExtrudeGeometry(shape, { depth: +op.thick || 0.05, bevelEnabled: false });
      const m = new THREE.Mesh(geo, material(op, S));
      m.rotation.set(Math.PI / 2, 0, 0);
      const [rx, ry, rz] = op.rot || [0, 0, 0];
      m.rotation.x += deg(rx);
      m.rotation.y += deg(ry);
      m.rotation.z += deg(rz);
      m.position.copy(v3(op.at));
      return m;
    },
    arrow(op) {
      const from = v3(op.from), to = v3(op.to, [1, 0, 0]);
      const dir = to.clone().sub(from), len = dir.length() || 1;
      return new THREE.ArrowHelper(dir.normalize(), from, len, color(op.color, "#3d7fd9"), len * 0.25, len * 0.12);
    },
  };

  // Technical-illustration look: dark edge lines on every mesh.
  function outline(obj) {
    obj.traverse((m) => {
      if (!m.isMesh) return;
      const e = new THREE.LineSegments(new THREE.EdgesGeometry(m.geometry, 35),
        new THREE.LineBasicMaterial({ color: 0x2b2a27, transparent: true, opacity: 0.35 }));
      m.add(e);
    });
  }

  // A tiny "photo studio": a warm room with three soft boxes, prefiltered for
  // image-based lighting. Gives materials real highlights and reflections.
  function studio(renderer) {
    const env = new THREE.Scene();
    env.add(new THREE.Mesh(new THREE.SphereGeometry(20, 32, 16), new THREE.MeshBasicMaterial({ color: 0x8f8a80, side: THREE.BackSide })));
    const box = (x, y, z, w, h, k) => {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(k, k, k), side: THREE.DoubleSide }));
      m.position.set(x, y, z);
      m.lookAt(0, 0, 0);
      env.add(m);
    };
    box(0, 12, 2, 14, 8, 4); // key light overhead
    box(12, 4, 8, 6, 8, 2.2); // right soft box
    box(-12, 3, -6, 6, 6, 1.2); // fill
    const pm = new THREE.PMREMGenerator(renderer);
    const tex = pm.fromScene(env, 0.04).texture;
    pm.dispose();
    return tex;
  }

  function fit(S) {
    const box = new THREE.Box3();
    for (const p of S.parts) box.expandByObject(p.obj);
    if (box.isEmpty()) return;
    const size = box.getSize(new THREE.Vector3()), center = box.getCenter(new THREE.Vector3());
    S.center.copy(center);
    S.radius = Math.max(size.x, size.y, size.z) * 0.5 || 1;
    const R = S.radius;
    S.ground.position.set(center.x, box.min.y - R * 0.04, center.z);
    S.ground.scale.setScalar(R * 8);
    S.sun.position.set(center.x + R * 1.5, center.y + R * 4, center.z + R * 2);
    S.sun.target.position.copy(center);
    Object.assign(S.sun.shadow.camera, { left: -R * 2, right: R * 2, top: R * 2, bottom: -R * 2, near: 0.01, far: R * 12 });
    S.sun.shadow.camera.updateProjectionMatrix();
    // Label rows are decided in world space (stable while the camera rocks):
    // upper parts label above the model from their top, lower parts below from their bottom.
    for (const p of S.parts) {
      p.row = (p.fixedAnchor ? p.fixedAnchor.y : p.cy) >= S.center.y ? 0 : 1;
      p.anchor.copy(p.fixedAnchor || (p.row === 0 ? p.top : p.bottom));
    }
    S.balancedFor = -1;
  }

  function frame(S, t) {
    if (!S.el.isConnected) {
      // Card cleared: stop the loop and release GPU memory and the WebGL context
      // (an all-day overlay would otherwise pile up contexts until GC).
      S.scene.traverse((o) => {
        o.geometry?.dispose();
        o.material?.dispose();
      });
      S.renderer.dispose();
      S.renderer.forceContextLoss();
      return;
    }
    // Rock ±35° around a front three-quarter view, so a cutaway stays readable.
    const spin = S.spin === "full" ? t * 0.00035 : -0.5 + Math.sin(t * 0.0005) * 0.6;
    const dist = S.radius * 2.6;
    const elev = deg(S.elev ?? 24);
    S.cam.position.set(
      S.center.x + Math.sin(spin) * Math.cos(elev) * dist,
      S.center.y + Math.sin(elev) * dist,
      S.center.z + Math.cos(spin) * Math.cos(elev) * dist
    );
    S.cam.lookAt(S.center);
    // Pop-in for freshly streamed parts.
    for (const p of S.parts) {
      if (p.born == null) p.born = t;
      const k = Math.min(1, (t - p.born) / 350);
      p.obj.scale.setScalar(0.001 + 0.999 * (1 - Math.pow(1 - k, 3)));
    }
    S.renderer.render(S.scene, S.cam);
    labels(S);
    requestAnimationFrame((tt) => frame(S, tt));
  }

  // Callout labels: two rows (above / below the model). Each label stays at its
  // part's screen x where possible; within a row, labels are pushed apart so
  // they never overlap. Leader lines run from the label to the part.
  function labels(S) {
    const w = S.el.clientWidth, h = S.el.clientHeight;
    const items = S.parts.filter((p) => p.lbl).map((p) => {
      const a = p.anchor.clone().project(S.cam);
      return { p, ax: (a.x * 0.5 + 0.5) * w, ay: (-a.y * 0.5 + 0.5) * h, lw: p.lbl.offsetWidth + 8 };
    });
    // Once per new part (not per frame, so labels don't jump): if a row's labels
    // are wider than the scene, move the parts nearest the middle to the other row.
    if (S.balancedFor !== items.length) {
      S.balancedFor = items.length;
      const width = (row) => row.reduce((t, i) => t + i.lw + 6, 6);
      for (let guard = 0; guard < items.length; guard++) {
        const r0 = items.filter((i) => i.p.row === 0), r1 = items.filter((i) => i.p.row === 1);
        const [big, small, to] = width(r0) > width(r1) ? [r0, r1, 1] : [r1, r0, 0];
        if (width(big) <= w) break;
        const mover = big.reduce((m, i) => (Math.abs(i.p.cy - S.center.y) < Math.abs(m.p.cy - S.center.y) ? i : m));
        if (width(small) + mover.lw + 6 > w) break;
        mover.p.row = to;
        if (!mover.p.fixedAnchor) mover.p.anchor.copy(to === 0 ? mover.p.top : mover.p.bottom);
        const a = mover.p.anchor.clone().project(S.cam);
        mover.ax = (a.x * 0.5 + 0.5) * w;
        mover.ay = (-a.y * 0.5 + 0.5) * h;
      }
    }
    const rows = [items.filter((i) => i.p.row === 0), items.filter((i) => i.p.row === 1)];
    S.leaders.innerHTML = "";
    rows.forEach((row, r) => {
      row.sort((a, b) => a.ax - b.ax);
      let cursor = 6;
      for (const it of row) {
        it.x = Math.max(cursor, Math.min(it.ax - it.lw / 2, w - it.lw - 6));
        cursor = it.x + it.lw + 6;
      }
      // If the row ran off the right edge, shift it back left.
      const over = cursor - 6 - (w - 6);
      if (over > 0) for (const it of row) it.x = Math.max(6, it.x - over);
      for (const it of row) {
        const ly = r === 0 ? 14 : h - 40;
        Object.assign(it.p.lbl.style, { left: `${it.x + it.lw / 2}px`, top: `${ly + 22}px` });
        const ln = document.createElementNS("http://www.w3.org/2000/svg", "line");
        const cx = Math.min(Math.max(it.ax, it.x + 4), it.x + it.lw - 12);
        Object.entries({ x1: it.ax, y1: it.ay, x2: cx, y2: r === 0 ? ly + 22 : ly + 2 }).forEach(([k, v]) => ln.setAttribute(k, v));
        S.leaders.appendChild(ln);
        const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        Object.entries({ cx: it.ax, cy: it.ay, r: 3 }).forEach(([k, v]) => dot.setAttribute(k, v));
        S.leaders.appendChild(dot);
      }
    });
  }

  function get(U, id) {
    U.state.scenes ||= {};
    id = id || U.state.lastScene || "s";
    if (!U.state.scenes[id]) U.apply({ op: "scene3d", id });
    U.state.lastScene = id;
    return U.state.scenes[id];
  }

  U.register("scene3d", (op, U) => {
    if (typeof THREE === "undefined") return console.error("scene3d: three.js not loaded");
    const body = U.card();
    U.cardEl.classList.add("wide", "wide3d");
    const el = U.el("div", "scene3d", body);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.max(2, devicePixelRatio || 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    el.appendChild(renderer.domElement);
    const leaders = U.svg("svg", { class: "leaders" }, el);
    if (op.caption) U.el("div", "cap", el, op.caption);
    const scene = new THREE.Scene();
    scene.environment = studio(renderer); // soft reflections make shapes read as solid objects
    scene.add(new THREE.HemisphereLight(0xffffff, 0xb9b1a0, 0.5));
    const sun = new THREE.DirectionalLight(0xffffff, 2.2);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.radius = 6;
    scene.add(sun, sun.target);
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.ShadowMaterial({ opacity: 0.18 }));
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);
    const cam = new THREE.PerspectiveCamera(32, 1, 0.01, 1000);
    const S = { id: op.id || "s", el, renderer, scene, cam, leaders, parts: [], center: new THREE.Vector3(), sun, ground,
      radius: 1, cut: !!op.cut, spin: op.spin, elev: op.elev };
    const resize = () => {
      const w = el.clientWidth || 600, h = el.clientHeight || 340;
      renderer.setSize(w, h, false);
      cam.aspect = w / h;
      cam.updateProjectionMatrix();
    };
    new ResizeObserver(resize).observe(el);
    resize();
    U.state.scenes ||= {};
    U.state.scenes[S.id] = S;
    U.state.lastScene = S.id;
    requestAnimationFrame((t) => frame(S, t));
  });

  U.register("part", (op, U) => {
    if (typeof THREE === "undefined") return;
    const S = get(U, op.s);
    const make = BUILD[op.shape];
    if (!make) return console.warn("scene3d: unknown shape", op.shape);
    const obj = make(op, S);
    if (!obj) return console.warn("scene3d: bad part", op.id);
    if (["box", "plate", "cylinder", "fan"].includes(op.shape)) outline(obj);
    obj.traverse((m) => { if (m.isMesh) m.castShadow = true; });
    S.scene.add(obj);
    const b = new THREE.Box3().setFromObject(obj);
    const mx = (b.min.x + b.max.x) / 2, mz = (b.min.z + b.max.z) / 2;
    const part = {
      obj, anchor: new THREE.Vector3(), row: 0, cy: (b.min.y + b.max.y) / 2,
      top: new THREE.Vector3(mx, b.max.y, mz), bottom: new THREE.Vector3(mx, b.min.y, mz),
      fixedAnchor: op.label_at ? v3(op.label_at) : null,
    };
    if (op.label) {
      const tone = op.tone || "green";
      part.lbl = U.el("div", `lbl tone-${tone}`, S.el, op.label);
      // Tones outside the CSS palette (red, copper, …) still color the border.
      if (!["blue", "orange", "green", "purple", "gray"].includes(tone)) part.lbl.style.setProperty("--tone", NAMED[tone] || tone);
    }
    S.parts.push(part);
    fit(S);
  });
})();
