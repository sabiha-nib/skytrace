"""Minimal FITS reader/writer (NumPy only), following the FITS Standard 4.0.

Supports what SPHEREx Level-2 products use: primary/IMAGE extensions with
BITPIX 8/16/32/64/-32/-64 (BSCALE/BZERO applied), and BINTABLE extensions with
numeric columns including multi-dimensional cells (TDIMn). Compressed images,
variable-length arrays and ASCII tables are refused explicitly.

astropy is preferred when installed (archive.products chooses); this reader
exists so the application can run where astropy cannot be installed, and it is
cross-checked against astropy in tests whenever astropy is present.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

BLOCK = 2880
_BITPIX = {8: ">u1", 16: ">i2", 32: ">i4", 64: ">i8", -32: ">f4", -64: ">f8"}
_TFORM = {"L": ("?", 1), "B": (">u1", 1), "I": (">i2", 2), "J": (">i4", 4), "K": (">i8", 8),
          "E": (">f4", 4), "D": (">f8", 8), "A": ("S1", 1)}


class FITSError(ValueError):
    pass


class Header(dict):
    """Ordered keyword -> value mapping; comments kept separately."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.comments: dict[str, str] = {}


@dataclass
class HDU:
    name: str
    header: Header
    data: object = None          # ndarray for images, dict[str, ndarray] for tables
    kind: str = "image"          # "image" | "table"
    columns: list[str] = field(default_factory=list)


def _parse_value(raw: str):
    s = raw.strip()
    if not s:
        return None, ""
    if s.startswith("'"):
        out, i = [], 1
        while i < len(s):
            if s[i] == "'":
                if i + 1 < len(s) and s[i + 1] == "'":
                    out.append("'")
                    i += 2
                    continue
                break
            out.append(s[i])
            i += 1
        rest = s[i + 1:]
        comment = rest.split("/", 1)[1].strip() if "/" in rest else ""
        return "".join(out).rstrip(), comment
    val, _, comment = s.partition("/")
    val = val.strip()
    if val == "T":
        return True, comment.strip()
    if val == "F":
        return False, comment.strip()
    try:
        return int(val), comment.strip()
    except ValueError:
        pass
    try:
        return float(val.replace("D", "E")), comment.strip()
    except ValueError:
        return val, comment.strip()


def _read_header(buf: io.BufferedIOBase) -> Header | None:
    h = Header()
    while True:
        block = buf.read(BLOCK)
        if not block:
            return None if not h else h
        if len(block) != BLOCK:
            raise FITSError("truncated header block")
        for i in range(0, BLOCK, 80):
            card = block[i:i + 80].decode("ascii", "replace")
            key = card[:8].strip()
            if key == "END":
                return h
            if key in ("", "COMMENT", "HISTORY"):
                continue
            if key == "HIERARCH" and "=" in card:
                k, _, v = card[9:].partition("=")
                h[k.strip()], c = _parse_value(v)
                h.comments[k.strip()] = c
                continue
            if card[8:10] == "= ":
                v, c = _parse_value(card[10:])
                h[key] = v
                h.comments[key] = c


def _data_bytes(h: Header) -> int:
    naxis = int(h.get("NAXIS", 0))
    if naxis == 0:
        return 0
    n = 1
    for i in range(1, naxis + 1):
        n *= int(h[f"NAXIS{i}"])
    n *= abs(int(h["BITPIX"])) // 8
    return int(h.get("GCOUNT", 1)) * (int(h.get("PCOUNT", 0)) + n)


def _image(h: Header, raw: bytes) -> np.ndarray | None:
    naxis = int(h.get("NAXIS", 0))
    if naxis == 0:
        return None
    if h.get("ZIMAGE"):
        raise FITSError("tile-compressed images are not supported by the native reader; install astropy")
    shape = tuple(int(h[f"NAXIS{i}"]) for i in range(naxis, 0, -1))
    arr = np.frombuffer(raw[: int(np.prod(shape)) * abs(int(h["BITPIX"])) // 8],
                        dtype=_BITPIX[int(h["BITPIX"])]).reshape(shape)
    bscale, bzero = h.get("BSCALE", 1), h.get("BZERO", 0)
    if bscale != 1 or bzero != 0:
        if int(h["BITPIX"]) == 16 and bscale == 1 and bzero == 32768:
            return (arr.astype(np.int32) + 32768).astype(np.uint16)
        if int(h["BITPIX"]) == 32 and bscale == 1 and bzero == 2147483648:
            return (arr.astype(np.int64) + 2147483648).astype(np.uint32)
        arr = arr.astype(np.float64) * bscale + bzero
    return arr.astype(arr.dtype.newbyteorder("="))


def _table(h: Header, raw: bytes) -> tuple[dict, list[str]]:
    if int(h.get("PCOUNT", 0)) != 0:
        raise FITSError("variable-length table columns are not supported by the native reader")
    nrow, width, ncol = int(h["NAXIS2"]), int(h["NAXIS1"]), int(h["TFIELDS"])
    fields, names = [], []
    for i in range(1, ncol + 1):
        m = re.fullmatch(r"\s*(\d*)([LBIJKEDA])\s*", str(h[f"TFORM{i}"]))
        if not m:
            raise FITSError(f"unsupported TFORM{i} = {h[f'TFORM{i}']!r}")
        rep = int(m.group(1) or 1)
        dt, _ = _TFORM[m.group(2)]
        name = str(h.get(f"TTYPE{i}", f"COL{i}")).strip()
        names.append(name)
        if m.group(2) == "A":
            fields.append((name, f"S{rep}"))
            continue
        tdim = h.get(f"TDIM{i}")
        shape = tuple(int(x) for x in reversed(re.findall(r"\d+", tdim))) if tdim else ((rep,) if rep > 1 else ())
        fields.append((name, dt, shape) if shape else (name, dt))
    rec = np.frombuffer(raw[: nrow * width], dtype=np.dtype(fields)) if nrow else np.zeros(0, np.dtype(fields))
    if rec.dtype.itemsize != width:
        raise FITSError(f"row width mismatch: header {width}, columns {rec.dtype.itemsize}")
    out = {}
    for n in names:
        col = rec[n]
        if col.dtype.kind == "S":
            out[n] = np.char.rstrip(col.astype(str))
        else:
            v = col.astype(col.dtype.newbyteorder("="))
            for i in range(1, ncol + 1):
                if str(h.get(f"TTYPE{i}", "")).strip() == n and (h.get(f"TSCAL{i}", 1) != 1 or h.get(f"TZERO{i}", 0) != 0):
                    v = v * h.get(f"TSCAL{i}", 1) + h.get(f"TZERO{i}", 0)
            out[n] = v
    return out, names


def read(source: bytes | str | Path) -> list[HDU]:
    buf = io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else open(source, "rb")
    hdus: list[HDU] = []
    try:
        while True:
            h = _read_header(buf)
            if h is None:
                break
            if not hdus and "SIMPLE" not in h:
                raise FITSError("not a FITS file (no SIMPLE keyword)")
            nbytes = _data_bytes(h)
            raw = buf.read(nbytes)
            if len(raw) < nbytes:
                raise FITSError(f"truncated data in HDU {len(hdus)} ({len(raw)} of {nbytes} bytes)")
            pad = (-nbytes) % BLOCK
            buf.read(pad)
            xt = str(h.get("XTENSION", "")).strip()
            name = str(h.get("EXTNAME", "PRIMARY" if not hdus else f"HDU{len(hdus)}")).strip().upper()
            if xt == "BINTABLE":
                data, cols = _table(h, raw)
                hdus.append(HDU(name, h, data, "table", cols))
            elif xt in ("", "IMAGE"):
                hdus.append(HDU(name, h, _image(h, raw), "image"))
            else:
                hdus.append(HDU(name, h, None, f"unsupported:{xt}"))
    finally:
        if not isinstance(source, (bytes, bytearray)):
            buf.close()
    if not hdus:
        raise FITSError("empty file")
    return hdus


# ------------------------------------------------------------------ writer
def _fmt(v) -> str:
    if isinstance(v, bool):
        return f"{'T' if v else 'F':>20}"
    if isinstance(v, (int, np.integer)):
        return f"{int(v):>20d}"
    if isinstance(v, (float, np.floating)):
        s = f"{float(v):.16G}"
        if "." not in s and "E" not in s and "N" not in s and "I" not in s:
            s += "."
        return f"{s:>20}"
    s = str(v).replace("'", "''")
    return f"'{s:<8}'"


def _card(k: str, v, c: str = "") -> bytes:
    if len(k) > 8:
        body = f"HIERARCH {k} = {_fmt(v).strip()}"
    else:
        body = f"{k:<8}= {_fmt(v)}"
    if c:
        body += f" / {c}"
    if len(body) > 80:
        raise FITSError(f"card too long for {k}")
    return body.ljust(80).encode("ascii")


def _header_bytes(cards: list[tuple]) -> bytes:
    out = b"".join(_card(*c) for c in cards) + b"END".ljust(80)
    return out + b" " * ((-len(out)) % BLOCK)


def _pad(data: bytes) -> bytes:
    return data + b"\0" * ((-len(data)) % BLOCK)


_NP2BITPIX = {np.dtype("uint8"): 8, np.dtype("int16"): 16, np.dtype("int32"): 32, np.dtype("int64"): 64,
              np.dtype("float32"): -32, np.dtype("float64"): -64}


def write(path: str | Path, hdus: list[HDU]) -> None:
    """Write image and numeric BINTABLE HDUs. The first HDU must be an image (may be empty)."""
    chunks = []
    for i, h in enumerate(hdus):
        extra = [(k, v, h.header.comments.get(k, "")) for k, v in h.header.items()
                 if k not in ("SIMPLE", "XTENSION", "BITPIX", "NAXIS", "EXTEND", "PCOUNT", "GCOUNT", "EXTNAME", "TFIELDS")
                 and not re.fullmatch(r"(NAXIS\d+|TTYPE\d+|TFORM\d+|TDIM\d+)", k)]
        if h.kind == "image":
            arr = None if h.data is None else np.ascontiguousarray(h.data)
            bitpix = 8 if arr is None else _NP2BITPIX[arr.dtype]
            cards = [("SIMPLE", True)] if i == 0 else [("XTENSION", "IMAGE")]
            cards += [("BITPIX", bitpix), ("NAXIS", 0 if arr is None else arr.ndim)]
            if arr is not None:
                cards += [(f"NAXIS{j + 1}", n) for j, n in enumerate(reversed(arr.shape))]
            cards += [("EXTEND", True)] if i == 0 else [("PCOUNT", 0), ("GCOUNT", 1)]
            if i > 0 or h.name != "PRIMARY":
                cards.append(("EXTNAME", h.name))
            chunks.append(_header_bytes(cards + extra))
            if arr is not None:
                chunks.append(_pad(arr.astype(arr.dtype.newbyteorder(">")).tobytes()))
        elif h.kind == "table":
            if i == 0:
                raise FITSError("the first HDU must be an image")
            cols = h.columns or list(h.data)
            nrow = len(next(iter(h.data.values())))
            fields, cards_cols = [], []
            for j, n in enumerate(cols, 1):
                a = np.asarray(h.data[n])
                code = {np.dtype("float64"): "D", np.dtype("float32"): "E", np.dtype("int32"): "J",
                        np.dtype("int64"): "K", np.dtype("int16"): "I", np.dtype("uint8"): "B"}[a.dtype]
                cell = a.shape[1:]
                rep = int(np.prod(cell)) if cell else 1
                cards_cols += [(f"TTYPE{j}", n), (f"TFORM{j}", f"{rep}{code}")]
                if len(cell) > 1:
                    cards_cols.append((f"TDIM{j}", "(" + ",".join(str(x) for x in reversed(cell)) + ")"))
                fields.append((n, a.dtype.newbyteorder(">"), cell) if cell else (n, a.dtype.newbyteorder(">")))
            rec = np.zeros(nrow, dtype=np.dtype(fields))
            for n in cols:
                rec[n] = h.data[n]
            cards = [("XTENSION", "BINTABLE"), ("BITPIX", 8), ("NAXIS", 2), ("NAXIS1", rec.dtype.itemsize),
                     ("NAXIS2", nrow), ("PCOUNT", 0), ("GCOUNT", 1), ("TFIELDS", len(cols))] + cards_cols
            cards.append(("EXTNAME", h.name))
            chunks.append(_header_bytes(cards + extra))
            chunks.append(_pad(rec.tobytes()))
    Path(path).write_bytes(b"".join(chunks))
