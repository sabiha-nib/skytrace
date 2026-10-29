// Canvas image viewer for SPHEREx cutouts (float MJy/sr arrays).
// Display scaling is a visual aid only; it never changes the data or the measurements.

import { b64ToFloat32, b64ToUint8, el, fmt } from "./util.js";

const STRETCH = {
  linear: (t) => t,
  asinh: (t) => Math.asinh(10 * t) / Math.asinh(10),
  log: (t) => Math.log10(1 + 999 * t) / 3,
  sqrt: (t) => Math.sqrt(t),
};

export function decodeFrame(p) {
  if (!p) return null;
  return { ...p, pixels: b64ToFloat32(p.data), mask: p.reject_mask ? b64ToUint8(p.reject_mask) : null };
}

function percentile(arr, q) {
  const v = Array.from(arr).filter(Number.isFinite).sort((a, b) => a - b);
  if (!v.length) return 0;
  return v[Math.min(v.length - 1, Math.max(0, Math.round((q / 100) * (v.length - 1))))];
}

export class ImageViewer {
  constructor(host, { label = "Sky image", onHover = null } = {}) {
    this.host = host;
    this.canvas = el("canvas", { role: "img", "aria-label": label, tabindex: "0" });
    this.caption = el("div", { class: "caption" });
    this.readout = el("div", { class: "readout", "aria-live": "off" });
    this.emptyEl = el("div", { class: "empty-state" });
    host.classList.add("viewer");
    host.append(this.canvas, this.caption, this.readout, this.emptyEl);
    this.opts = { frames: [], mode: "single", index: 0, fade: 0.5, stretch: { fn: "asinh", lo: 1, hi: 99.7 }, shared: true,
                  overlays: { predicted: true, centroid: true, refs: true, mask: false }, markers: [[], []], captions: [] };
    this.zoom = 1; this.panX = 0; this.panY = 0;
    this.onHover = onHover;
    this._bind();
    new ResizeObserver(() => this.render()).observe(host);
  }

  set(o) { Object.assign(this.opts, o); this._rescale(); this.render(); }
  empty(msg) { this.opts.frames = []; this.emptyEl.textContent = msg; this.emptyEl.hidden = false; this.render(); }

  _rescale() {
    const f = this.opts.frames.filter(Boolean);
    this.scales = f.map((fr) => [percentile(fr.pixels, this.opts.stretch.lo), percentile(fr.pixels, this.opts.stretch.hi)]);
    if (this.opts.shared && this.scales.length > 1) this.scales = this.scales.map(() => this.scales[0]);
    if (this.opts.mode === "diff" && f.length === 2) {
      const d = this._diffPixels();
      const a = Math.max(Math.abs(percentile(d, 1)), Math.abs(percentile(d, 99))) || 1;
      this.diffScale = a; this.diffData = d;
    }
  }

  _diffPixels() {
    const [A, B] = this.opts.frames;
    const ma = percentile(A.pixels, 50), mb = percentile(B.pixels, 50);
    const d = new Float32Array(A.pixels.length);
    for (let i = 0; i < d.length; i++) d[i] = (B.pixels[i] - mb) - (A.pixels[i] - ma);
    return d;
  }

  _imageFor(frame, scale) {
    const { width: w, height: h } = frame;
    const off = this._off || (this._off = document.createElement("canvas"));
    off.width = w; off.height = h;
    const ctx = off.getContext("2d");
    const img = ctx.createImageData(w, h);
    const fn = STRETCH[this.opts.stretch.fn] || STRETCH.asinh;
    const [lo, hi] = scale; const span = hi - lo || 1;
    const diff = this.opts.mode === "diff";
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const src = y * w + x, dst = ((h - 1 - y) * w + x) * 4;  // FITS row 0 at the bottom
        let r, g, b;
        if (diff) {
          const v = this.diffData[src];
          if (!Number.isFinite(v)) { r = g = b = 40; } else {
            // diverging: brighter in B -> warm, fainter in B -> cool
            const t = Math.max(-1, Math.min(1, v / this.diffScale));
            r = Math.round(t > 0 ? 18 + 212 * t : 18 + 40 * -t);
            b = Math.round(t < 0 ? 18 + 212 * -t : 18 + 40 * t);
            g = Math.round(22 + 30 * (1 - Math.abs(t)) + 60 * Math.abs(t) * 0.3);
          }
        } else {
          const v = frame.pixels[src];
          if (!Number.isFinite(v)) { r = 70; g = 20; b = 30; } else {
            const t = fn(Math.max(0, Math.min(1, (v - lo) / span)));
            r = Math.round(255 * Math.pow(t, 1.02)); g = Math.round(255 * Math.pow(t, 1.0)); b = Math.round(255 * Math.pow(t, 0.92));
          }
          if (this.opts.overlays.mask && frame.mask && frame.mask[src]) { r = 230; g = 90; b = 60; }
        }
        img.data[dst] = r; img.data[dst + 1] = g; img.data[dst + 2] = b; img.data[dst + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
    return off;
  }

  _geom(frame) {
    const cw = this.canvas.width, ch = this.canvas.height;
    const base = Math.min(cw / frame.width, ch / frame.height);
    const s = base * this.zoom;
    const ox = (cw - frame.width * s) / 2 + this.panX * devicePixelRatio;
    const oy = (ch - frame.height * s) / 2 + this.panY * devicePixelRatio;
    return { s, ox, oy, toCanvas: (x, y) => [ox + (x + 0.5) * s, oy + (frame.height - 1 - y + 0.5) * s] };
  }

  render() {
    const r = this.host.getBoundingClientRect();
    const dpr = devicePixelRatio || 1;
    this.canvas.width = Math.max(1, Math.round(r.width * dpr));
    this.canvas.height = Math.max(1, Math.round(r.height * dpr));
    const ctx = this.canvas.getContext("2d");
    ctx.fillStyle = "#070c16"; ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    const frames = this.opts.frames;
    if (!frames.length || !frames[0]) { this.caption.replaceChildren(); this.emptyEl.hidden = false; return; }
    this.emptyEl.hidden = true;
    const A = frames[0];
    const g = this._geom(A);
    ctx.imageSmoothingEnabled = false;
    const draw = (frame, scale, alpha = 1) => {
      ctx.globalAlpha = alpha;
      ctx.drawImage(this._imageFor(frame, scale), g.ox, g.oy, frame.width * g.s, frame.height * g.s);
      ctx.globalAlpha = 1;
    };
    const mode = this.opts.mode;
    let shown = 0;
    if (mode === "diff" && frames[1]) draw(A, [0, 1]);
    else if (mode === "fade" && frames[1]) { draw(A, this.scales[0]); draw(frames[1], this.scales[1], this.opts.fade); shown = this.opts.fade >= 0.5 ? 1 : 0; }
    else { shown = mode === "blink" && frames[1] ? this.opts.index % 2 : 0; draw(frames[shown], this.scales[shown]); }
    this.shown = shown;
    this._drawMarkers(ctx, g, mode === "single" ? [0] : mode === "blink" ? [shown] : [0, 1]);
    if (frames.some((f) => f && f.synthetic)) this._watermark(ctx);
    const cap = this.opts.captions[mode === "fade" || mode === "diff" ? 0 : shown] || this.opts.captions[0] || [];
    this.caption.replaceChildren(...cap.map((c) => el("span", {}, c)));
  }

  _drawMarkers(ctx, g, which) {
    const dpr = devicePixelRatio || 1;
    const styles = { predicted: ["#e6b450", [4, 3]], centroid: ["#6cc6a4", []], ref: ["#8fb3ff", []], "ref-rejected": ["#e48b5c", [2, 2]],
                     predictedB: ["#d97fb6", [4, 3]], centroidB: ["#d97fb6", []] };
    for (const i of which) {
      for (const m of (this.opts.markers[i] || [])) {
        const key = m.kind.startsWith("ref") ? "refs" : m.kind.startsWith("predicted") ? "predicted" : "centroid";
        if (!this.opts.overlays[key] || m.x == null) continue;
        const [cx, cy] = g.toCanvas(m.x, m.y);
        const [col, dash] = styles[m.kind] || ["#fff", []];
        ctx.strokeStyle = col; ctx.lineWidth = 1.5 * dpr; ctx.setLineDash(dash.map((d) => d * dpr));
        ctx.beginPath();
        const rad = (m.kind.startsWith("ref") ? 5 : m.kind.startsWith("predicted") ? 9 : 4) * dpr * Math.max(1, this.zoom * 0.6);
        if (m.kind.startsWith("centroid")) { ctx.moveTo(cx - rad * 2, cy); ctx.lineTo(cx - rad * 0.6, cy); ctx.moveTo(cx + rad * 0.6, cy); ctx.lineTo(cx + rad * 2, cy);
          ctx.moveTo(cx, cy - rad * 2); ctx.lineTo(cx, cy - rad * 0.6); ctx.moveTo(cx, cy + rad * 0.6); ctx.lineTo(cx, cy + rad * 2); }
        else ctx.arc(cx, cy, rad, 0, Math.PI * 2);
        ctx.stroke(); ctx.setLineDash([]);
      }
    }
  }

  _watermark(ctx) {
    const { width: w, height: h } = this.canvas;
    ctx.save();
    ctx.translate(w / 2, h / 2); ctx.rotate(-Math.PI / 7);
    ctx.font = `600 ${Math.round(Math.min(w, h) / 9)}px system-ui, sans-serif`;
    ctx.fillStyle = "rgba(217, 127, 182, 0.22)"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText("SYNTHETIC", 0, 0);
    ctx.font = `500 ${Math.round(Math.min(w, h) / 30)}px system-ui, sans-serif`;
    ctx.fillText("generated test image — not an observation", 0, Math.min(w, h) / 12);
    ctx.restore();
  }

  _bind() {
    const c = this.canvas;
    let drag = null;
    c.addEventListener("wheel", (e) => { e.preventDefault(); this.zoomBy(e.deltaY < 0 ? 1.2 : 1 / 1.2); }, { passive: false });
    c.addEventListener("pointerdown", (e) => { drag = { x: e.clientX, y: e.clientY, px: this.panX, py: this.panY }; c.setPointerCapture(e.pointerId); });
    c.addEventListener("pointerup", () => { drag = null; });
    c.addEventListener("pointermove", (e) => {
      if (drag) { this.panX = drag.px + e.clientX - drag.x; this.panY = drag.py + e.clientY - drag.y; this.render(); }
      this._hover(e);
    });
    c.addEventListener("pointerleave", () => { this.readout.textContent = ""; });
    c.addEventListener("keydown", (e) => {
      if (e.key === "+" || e.key === "=") this.zoomBy(1.25);
      else if (e.key === "-") this.zoomBy(0.8);
      else if (e.key === "0") this.resetView();
    });
  }

  zoomBy(f) { this.zoom = Math.max(1, Math.min(16, this.zoom * f)); this.render(); }
  resetView() { this.zoom = 1; this.panX = this.panY = 0; this.render(); }

  _hover(e) {
    const A = this.opts.frames[this.shown || 0] || this.opts.frames[0];
    if (!A) return;
    const rect = this.canvas.getBoundingClientRect();
    const dpr = devicePixelRatio || 1;
    const g = this._geom(A);
    const x = ((e.clientX - rect.left) * dpr - g.ox) / g.s - 0.5;
    const y = A.height - 1 - (((e.clientY - rect.top) * dpr - g.oy) / g.s - 0.5);
    const ix = Math.round(x), iy = Math.round(y);
    if (ix < 0 || iy < 0 || ix >= A.width || iy >= A.height) { this.readout.textContent = ""; return; }
    const v = this.opts.mode === "diff" ? this.diffData?.[iy * A.width + ix] : A.pixels[iy * A.width + ix];
    let sky = "";
    const W = this.opts.frames[0].linear_wcs;
    if (W) {
      const dx = x - W.center_xy[0], dy = y - W.center_xy[1];
      const dra = (W.cd_deg[0][0] * dx + W.cd_deg[0][1] * dy) / Math.cos(W.center_radec[1] * Math.PI / 180);
      const ddec = W.cd_deg[1][0] * dx + W.cd_deg[1][1] * dy;
      sky = `  RA ${fmt(W.center_radec[0] + dra, 5)}°  Dec ${fmt(W.center_radec[1] + ddec, 5)}° (approx.)`;
    }
    this.readout.textContent = `x ${ix}  y ${iy}  ${this.opts.mode === "diff" ? "Δ" : ""}${fmt(v, 3)} ${A.bunit || ""}${sky}`;
    if (this.onHover) this.onHover({ x, y, value: v });
  }
}
