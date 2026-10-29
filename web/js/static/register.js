// Static preview only: display registration of image B onto image A's pixel grid, done in the browser.
// Mirrors the server's /pair-image: with Gaia-referenced plate solutions for both exposures (DIFFAST-1) the
// mapping is exact for the affine plates; otherwise it falls back to each image's local linear WCS and says so.
// Display only: no measurement uses resampled pixels.

export function b64ToFloat32(b64) {
  const bin = atob(b64), u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  return new Float32Array(u8.buffer);
}

const affine = (c) => ({ t: [c[0], c[3]], M: [[c[1], c[2]], [c[4], c[5]]] });
const inv2 = (M) => { const d = M[0][0] * M[1][1] - M[0][1] * M[1][0]; return [[M[1][1] / d, -M[0][1] / d], [-M[1][0] / d, M[0][0] / d]]; };
const mul = (M, v) => [M[0][0] * v[0] + M[0][1] * v[1], M[1][0] * v[0] + M[1][1] * v[1]];

function linear(p) {   // local linear WCS from the payload: pixel <-> (ra, dec)
  const W = p.linear_wcs, [cx, cy] = W.center_xy, [ra0, dec0] = W.center_radec, cosd = Math.cos((dec0 * Math.PI) / 180);
  const CD = W.cd_deg, iCD = inv2(CD);
  return {
    toSky: (x, y) => { const d = mul(CD, [x - cx, y - cy]); return [ra0 + d[0] / cosd, dec0 + d[1]]; },
    toPix: (ra, dec) => { const d = mul(iCD, [(ra - ra0) * cosd, dec - dec0]); return [cx + d[0], cy + d[1]]; },
  };
}

function bilinear(img, nx, ny, x, y) {
  if (!(x >= 0 && y >= 0 && x <= nx - 1 && y <= ny - 1)) return NaN;
  const x0 = Math.min(Math.floor(x), nx - 2), y0 = Math.min(Math.floor(y), ny - 2), fx = x - x0, fy = y - y0;
  const i = y0 * nx + x0;
  return img[i] * (1 - fx) * (1 - fy) + img[i + 1] * fx * (1 - fy) + img[i + nx] * (1 - fx) * fy + img[i + nx + 1] * fx * fy;
}

/** pa, pb: image payloads; ma, mb: logged measurements (may be null). Returns the /pair-image response shape. */
export function registerPair(pa, pb, ma, mb, comparison) {
  const nx = pa.width, ny = pa.height, src = b64ToFloat32(pb.data), out = new Float32Array(nx * ny);
  const plates = ma?.plate?.coeffs_deg && mb?.plate?.coeffs_deg;
  let mapBtoA = null, method;
  if (plates) {
    const A = affine(ma.plate.coeffs_deg), B = affine(mb.plate.coeffs_deg), iB = inv2(B.M), iA = inv2(A.M);
    for (let y = 0; y < ny; y++) for (let x = 0; x < nx; x++) {
      const s = mul(A.M, [x, y]); const xe = [A.t[0] + s[0] - B.t[0], A.t[1] + s[1] - B.t[1]];
      const [bx, by] = mul(iB, xe);
      out[y * nx + x] = bilinear(src, pb.width, pb.height, bx, by);
    }
    mapBtoA = (x, y) => { const s = mul(B.M, [x, y]); return mul(iA, [B.t[0] + s[0] - A.t[0], B.t[1] + s[1] - A.t[1]]); };
    method = "per-exposure Gaia-referenced plate solutions (affine, DIFFAST-1), resampled in the browser";
  } else {
    const LA = linear(pa), LB = linear(pb);
    for (let y = 0; y < ny; y++) for (let x = 0; x < nx; x++) {
      const [ra, dec] = LA.toSky(x, y); const [bx, by] = LB.toPix(ra, dec);
      out[y * nx + x] = bilinear(src, pb.width, pb.height, bx, by);
    }
    method = "approximate: each image's local linear WCS (static preview, no plate solution for one of the images; the server uses the full TAN-SIP WCS)";
  }
  const LA = linear(pa);
  const b = { ...pb, data: null, pixels: out, resampled_onto: pa.key,
              predicted_target_xy: pb.predicted_target_radec ? LA.toPix(...pb.predicted_target_radec) : null, centroid_in_a: null };
  const cb = mb?.centroid;
  if (mapBtoA && cb?.converged) b.centroid_in_a = mapBtoA(cb.x, cb.y);
  return { a: pa, b, registration: method, comparison,
           note: "B is resampled onto A's pixel grid by bilinear interpolation for display only; all measurements use the original pixels." };
}
