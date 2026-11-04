// Renderer core. Primitives register handlers; Python streams ops into U.apply().
// Coordinates in ops are screenshot pixels; U.sx/U.sy map them to the viewport.
(() => {
  const $ = (id) => document.getElementById(id);
  const MAX_CAPTIONS = 3;

  const U = (window.U = {
    handlers: {},
    frame: { imgW: innerWidth, imgH: innerHeight },
    cardEl: null,
    state: {},

    css(text) {
      const s = document.createElement("style");
      s.textContent = text;
      document.head.appendChild(s);
    },

    register(name, fn) {
      this.handlers[name] = fn;
    },

    apply(op) {
      const h = this.handlers[op.op];
      if (!h) return console.warn("unknown op", op.op);
      try {
        h(op, this);
      } catch (e) {
        console.error("op failed", op.op, e);
      }
      this.fit();
    },

    setSafeTop(px) {
      document.documentElement.style.setProperty("--safe-top", `${px}px`);
    },

    begin(turn) {
      this.clear();
      this.frame = { imgW: turn.imgW || innerWidth, imgH: turn.imgH || innerHeight };
      this.anchors = turn.anchors || [];
      this._lastLayout = undefined; // first report comes when the card (or end) appears
      this.status(turn.question ? `“${turn.question}”` : "", true);
    },

    end(error) {
      this.reportLayout(); // card-less drawings (only screen labels) get their ✕ now
      if (error) this.status(error, false, true);
      else this.status(null);
    },

    clear() {
      $("screen").innerHTML = "";
      $("screen-svg").innerHTML = SVG_DEFS;
      $("cards").innerHTML = "";
      $("floating-caption").innerHTML = "";
      this.cardEl = null;
      this.state = {};
      this.marks = []; // on-screen annotation rects, in viewport px
    },

    // Primitives that draw on the screen report what they cover, so the card
    // can get out of the way and labels can avoid each other.
    mark(rect) {
      this.marks.push(rect);
      this.reflowCard();
    },

    overlaps(a, b, pad = 6) {
      return a.x < b.x + b.w + pad && b.x < a.x + a.w + pad && a.y < b.y + b.h + pad && b.y < a.y + a.h + pad;
    },

    cardRect() {
      if (!this.cardEl) return null;
      const r = this.cardEl.getBoundingClientRect();
      return { x: r.left, y: r.top, w: r.width, h: r.height };
    },

    // Unless the model pinned the card to exact coordinates, keep it on
    // whichever side covers fewer annotations.
    reflowCard() {
      const c = this.cardEl;
      if (!c || c.dataset.fixed) return;
      const r = this.cardRect();
      // Covering a pinned point is worse than covering a label (labels can move).
      const cover = (x) => {
        const box = { x, y: r.y, w: r.w, h: r.h };
        const hits = (list) => list.filter((m) => this.overlaps(box, m, 0)).length;
        return 3 * hits(this.marks) + hits(this.state.labels || []);
      };
      const leftX = 28, rightX = innerWidth - r.w - 28;
      const side = c.dataset.side === "left" ? "left" : "right";
      const here = cover(side === "left" ? leftX : rightX), there = cover(side === "left" ? rightX : leftX);
      if (there < here) this.placeCard({ side: side === "left" ? "right" : "left" });
    },

    // Place a w×h label near (x,y): try the preferred offset, then nearby
    // alternatives, picking the first spot that hits no other label or the card.
    placeLabel(x, y, w, h, dx, dy) {
      const tries = [];
      for (const sx of [1, -1]) for (const k of [0, 1, -1, 2, -2, 3, -3]) tries.push([sx * dx, dy + k * (h + 8)]);
      const card = this.cardRect();
      let best = null;
      for (const [ox, oy] of tries) {
        const [lx, ly] = this.clampBox(x + ox - (ox < 0 ? w : 0), y + oy - h / 2, w, h);
        const r = { x: lx, y: ly, w, h };
        const clash = (this.state.labels || []).some((o) => this.overlaps(r, o)) || (card && this.overlaps(r, card));
        if (!clash) { best = r; break; }
        best ||= r;
      }
      (this.state.labels ||= []).push(best);
      return best;
    },

    // Find quoted on-screen text among the OCR anchors. Returns one viewport
    // rect per covered line (so multi-line quotes highlight like a marker),
    // or null. Falls back to the longest matching prefix of the quote, since
    // the model sometimes paraphrases the tail.
    findQuote(quote) {
      const norm = (t) => t.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
      const lines = (this.anchors || []).map((a) => ({ a, n: norm(a.t) })).filter((l) => l.n);
      if (!lines.length || !quote) return null;
      let full = "";
      for (const l of lines) {
        l.start = full.length;
        full += l.n + " ";
        l.end = l.start + l.n.length;
      }
      const words = norm(String(quote)).split(" ");
      const padded = " " + full; // match whole words only: "in the" must not hit "within the"
      const minWords = words.length < 3 ? words.length : Math.max(3, Math.ceil(words.length / 2));
      let from = -1, len = 0;
      for (let k = words.length; k >= minWords; k--) {
        const q = words.slice(0, k).join(" ");
        from = padded.indexOf(" " + q + " "); // index in padded of the space = q's index in full
        if (from >= 0) {
          len = k === words.length ? q.length : Math.min(full.length - from, norm(String(quote)).length);
          break;
        }
      }
      if (from < 0) return null;
      const to = from + len;
      const rects = [];
      for (const l of lines) {
        if (l.end <= from || l.start >= to) continue;
        // Approximate the covered part of the line by character position.
        const a = l.a, n = l.n.length || 1;
        const f0 = Math.max(0, from - l.start) / n, f1 = Math.min(n, to - l.start) / n;
        rects.push({ x: this.sx(a.x + a.w * f0), y: this.sy(a.y), w: this.sx(a.w * (f1 - f0)), h: this.sy(a.h) });
      }
      return rects.length ? rects : null;
    },

    sx(x) {
      return (x * innerWidth) / this.frame.imgW;
    },
    sy(y) {
      return (y * innerHeight) / this.frame.imgH;
    },

    el(tag, cls, parent, text) {
      const e = document.createElement(tag);
      if (cls) e.className = cls;
      if (text != null) e.textContent = text;
      if (parent) parent.appendChild(e);
      return e;
    },

    svg(tag, attrs, parent) {
      const e = document.createElementNS("http://www.w3.org/2000/svg", tag);
      for (const [k, v] of Object.entries(attrs || {})) e.setAttribute(k, v);
      if (parent) parent.appendChild(e);
      return e;
    },

    screenSvg() {
      return $("screen-svg");
    },
    screenLayer() {
      return $("screen");
    },

    // The explainer card. Created lazily so ops like "step" work even if the
    // model forgot to open a card first.
    card(opts = {}) {
      if (!this.cardEl) {
        const c = this.el("div", "card", $("cards"));
        this.el("div", "card-title", c);
        this.el("div", "card-body", c);
        this.el("div", "card-captions", c);
        this.cardEl = c;
        // Content keeps growing after an op (typewriter, fonts, layout), so refit on any resize.
        new ResizeObserver(() => this.fit()).observe(c);
        c.addEventListener("animationend", () => this.reportLayout());
      }
      const c = this.cardEl;
      if (opts.title != null) c.querySelector(".card-title").textContent = opts.title;
      if (opts.side || opts.x != null) this.placeCard(opts);
      else if (!c.dataset.placed) this.placeCard({ side: "right" });
      if (opts.side || opts.x != null) this.reflowCard();
      return c.querySelector(".card-body");
    },

    placeCard({ side = "right", x, y }) {
      const c = this.cardEl;
      c.dataset.placed = "1";
      c.dataset.side = side;
      if (x != null || y != null) c.dataset.fixed = "1";
      c.style.left = c.style.right = "";
      c.style.top = y != null ? `${this.sy(y)}px` : "";
      if (x != null) c.style.left = `${this.sx(x)}px`;
      else if (side === "left") c.style.left = "28px";
      else if (side === "center") c.style.left = `calc(50% - var(--card-w) / 2)`;
      else c.style.right = "28px";
    },

    caption(text) {
      const host = this.cardEl ? this.cardEl.querySelector(".card-captions") : $("floating-caption");
      const line = this.el("div", "caption", host);
      typewrite(line, text);
      while (host.children.length > MAX_CAPTIONS) host.removeChild(host.firstChild);
      [...host.children].forEach((e, i, all) => e.classList.toggle("old", i < all.length - 1));
    },

    status(text, busy = false, error = false) {
      const s = $("status");
      if (!text && !busy) {
        s.className = "hidden";
        return;
      }
      s.className = (busy ? "busy" : "") + (error ? " error" : "");
      s.querySelector(".status-text").textContent = text || "";
    },

    // Tell Python where the card is so the native ✕ button can sit on its corner.
    reportLayout() {
      const h = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.layout;
      if (!h) return;
      const r = this.cardEl && this.cardEl.getBoundingClientRect();
      const rect = r ? { x: r.left, y: r.top, w: r.width, h: r.height } : null;
      const key = JSON.stringify(rect);
      if (key !== this._lastLayout) {
        this._lastLayout = key;
        h.postMessage(rect);
      }
    },

    // Shrink the card when content outgrows the viewport; the overlay is
    // click-through so it can't scroll.
    fit() {
      this.reportLayout();
      const c = this.cardEl;
      if (!c) return;
      this.reflowCard();
      const top = parseFloat(getComputedStyle(c).top) || 72;
      const natural = c.offsetHeight; // layout height, unaffected by transform
      const scale = Math.max(0.5, Math.min(1, (innerHeight - top - 24) / natural));
      c.style.transformOrigin = c.dataset.side === "left" ? "top left" : "top right";
      c.style.transform = scale < 1 ? `scale(${scale})` : "";
      this.reportLayout();
    },

    // Clamp a label's top-left so it stays on screen.
    clampBox(x, y, w, h) {
      return [Math.min(Math.max(8, x), innerWidth - w - 8), Math.min(Math.max(8, y), innerHeight - h - 8)];
    },
  });

  const SVG_DEFS = `<defs><marker id="arrowhead" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker></defs>`;

  function typewrite(el, text) {
    let i = 0;
    const step = () => {
      i = Math.min(text.length, i + 2);
      el.textContent = text.slice(0, i);
      if (i < text.length) setTimeout(step, 14);
    };
    step();
  }

  U.register("clear", () => U.clear());
  window.addEventListener("DOMContentLoaded", () => U.clear());
})();
