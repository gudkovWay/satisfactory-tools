#!/usr/bin/env python3
"""
Satisfactory (save version 60 / U1.1) -- reorganise blueprint categories.

Rewrites the `mBlueprintCategoryRecords` property inside the BP_GameState
object of the save, so blueprints end up in real categories/sub-categories
instead of all sitting in "Undefined".

Container format
----------------
  [ file header, verbatim ]                     -- everything before the first chunk tag
  [ chunk ]*                                    -- each: 49-byte header + zlib stream
      int64  0x222222229E2A83C1   package tag
      int64  131072               max chunk size
      int8   3                    compressor (zlib)
      int64  compressedSize
      int64  uncompressedSize
      int64  compressedSize   (repeated)
      int64  uncompressedSize (repeated)

Body layout (only the parts we touch)
-------------------------------------
  @0                int64  bodySize          == len(body) - 8
  ...world grid, then per level:
      FString levelName
      int64  headerSectionSize
      int32  objectHeaderCount
      ...headers...
      int64  objectSectionSize   <-- encloses our edit
      int32  objectCount
      [ int32 saveVer(60) | int32 flag(0) | int32 size | data | int32 pad(0) ]*
      ...collectables...

Property format (UE5 / Satisfactory v41+)
-----------------------------------------
      FString name                      ("None" terminates a property list)
      FString type
      (int32 1, FString nestedType)*    type chain, terminated by int32 0
      int32   valueSize
      int8    flag                      (carries the value for BoolProperty)
      byte[valueSize] value
"""

import struct
import zlib

PKG_TAG = 0x222222229E2A83C1
MAX_CHUNK = 131072
SAVE_VER = 60


# --------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------

class Reader:
    def __init__(self, buf, pos=0):
        self.b = buf
        self.p = pos

    def i32(self):
        v = struct.unpack_from('<i', self.b, self.p)[0]
        self.p += 4
        return v

    def u8(self):
        v = self.b[self.p]
        self.p += 1
        return v

    def raw(self, n):
        v = self.b[self.p:self.p + n]
        self.p += n
        return v

    def fstring(self):
        n = self.i32()
        if n == 0:
            return ""
        if n < 0:                                   # UTF-16, n = -(chars incl. NUL)
            raw = self.raw(-n * 2)
            return raw[:-2].decode('utf-16-le')
        raw = self.raw(n)
        return raw[:-1].decode('utf-8')


def w_fstring(s):
    """Serialise like the game: ASCII-safe strings as UTF-8, others as UTF-16."""
    if s == "":
        return struct.pack('<i', 0)
    try:
        s.encode('ascii')
    except UnicodeEncodeError:
        raw = s.encode('utf-16-le') + b'\x00\x00'
        return struct.pack('<i', -(len(s) + 1)) + raw
    raw = s.encode('utf-8') + b'\x00'
    return struct.pack('<i', len(raw)) + raw


# --------------------------------------------------------------------------
# property tree
# --------------------------------------------------------------------------

class Prop:
    __slots__ = ('name', 'type', 'chain', 'flag', 'value', 'array', 'raw')

    def __init__(self, name, typ, chain, flag):
        self.name = name
        self.type = typ
        self.chain = chain          # nested type names, e.g. ["StructProperty", "X", "/Script/..."]
        self.flag = flag
        self.value = None           # raw bytes, for leaf properties we do not interpret
        self.array = None           # ("Struct"|"Str", [elements])
        self.raw = None


def read_props(r, stop_at=None):
    """Read a property list up to (and including) the 'None' terminator."""
    props = []
    while True:
        if stop_at is not None and r.p >= stop_at:
            return props, False
        save = r.p
        name = r.fstring()
        if name == "None":
            return props, True
        typ = r.fstring()
        chain = []
        while True:
            flag = r.i32()
            if flag == 0:
                break
            if flag != 1:
                raise ValueError(f"unexpected chain flag {flag} at {save}")
            chain.append(r.fstring())
        size = r.i32()
        pflag = r.u8()
        p = Prop(name, typ, chain, pflag)
        body = r.raw(size)
        if typ == "ArrayProperty":
            inner = chain[0]
            sub = Reader(body)
            count = sub.i32()
            if inner == "StructProperty":
                # count property-lists, each terminated by "None"
                elems = []
                for _ in range(count):
                    e, ok = read_props(sub)
                    if not ok:
                        raise ValueError("array struct element not terminated")
                    elems.append(e)
                if sub.p != len(body):
                    raise ValueError(f"struct array trailing bytes {len(body) - sub.p}")
                p.array = ("Struct", elems)
            elif inner == "StrProperty":
                elems = [sub.fstring() for _ in range(count)]
                if sub.p != len(body):
                    raise ValueError(f"str array trailing bytes {len(body) - sub.p}")
                p.array = ("Str", elems)
            else:
                p.value = body
        else:
            p.value = body
        props.append(p)


def write_props(props, terminate=True):
    out = bytearray()
    for p in props:
        out += w_fstring(p.name)
        out += w_fstring(p.type)
        for c in p.chain:
            out += struct.pack('<i', 1)
            out += w_fstring(c)
        out += struct.pack('<i', 0)
        if p.array is not None:
            kind, elems = p.array
            body = bytearray(struct.pack('<i', len(elems)))
            if kind == "Struct":
                for e in elems:
                    body += write_props(e)
            else:
                for s in elems:
                    body += w_fstring(s)
            body = bytes(body)
        else:
            body = p.value
        out += struct.pack('<i', len(body))
        out += bytes([p.flag])
        out += body
    if terminate:
        out += w_fstring("None")
    return bytes(out)


# --------------------------------------------------------------------------
# container
# --------------------------------------------------------------------------

def read_save(path):
    data = open(path, 'rb').read()
    tag = struct.pack('<Q', PKG_TAG)
    first = data.find(tag)
    if first < 0:
        raise ValueError("no chunk tag found -- unsupported save version")
    header = data[:first]
    body = bytearray()
    p = first
    while p < len(data):
        t, mx = struct.unpack_from('<QQ', data, p)
        if t != PKG_TAG:
            raise ValueError(f"bad chunk tag at {p}")
        algo = data[p + 16]
        csize, usize, csize2, usize2 = struct.unpack_from('<qqqq', data, p + 17)
        if (csize, usize) != (csize2, usize2):
            raise ValueError("chunk size fields disagree")
        if algo != 3:
            raise ValueError(f"unsupported compressor {algo}")
        start = p + 49
        raw = zlib.decompress(data[start:start + csize])
        if len(raw) != usize:
            raise ValueError("chunk size mismatch")
        body += raw
        p = start + csize
    return header, bytes(body), mx


def write_save(path, header, body, max_chunk=MAX_CHUNK):
    out = bytearray(header)
    for off in range(0, len(body), max_chunk):
        raw = body[off:off + max_chunk]
        comp = zlib.compress(raw, 6)
        out += struct.pack('<QQ', PKG_TAG, max_chunk)
        out += bytes([3])
        out += struct.pack('<qqqq', len(comp), len(raw), len(comp), len(raw))
        out += comp
    open(path, 'wb').write(out)
    return len(out)


# --------------------------------------------------------------------------
# locating the pieces inside the body
# --------------------------------------------------------------------------

class Located:
    pass


def locate(body):
    """Find the GameState object entry and every byte-length field enclosing it."""
    loc = Located()

    anchor = body.find(b'mBlueprintCategoryRecords')
    if anchor < 0 or body.find(b'mBlueprintCategoryRecords', anchor + 1) >= 0:
        raise ValueError("expected exactly one mBlueprintCategoryRecords")
    loc.prop_off = anchor - 4

    # object entry header: [i32 saveVer][i32 flag][i32 size] ... walk back to it
    hdr = None
    for cand in range(loc.prop_off - 4096, loc.prop_off):
        sv, fl, sz = struct.unpack_from('<iii', body, cand)
        if sv == SAVE_VER and fl == 0 and 0 < sz < 1 << 24:
            if cand + 12 < loc.prop_off < cand + 12 + sz:
                hdr = cand
                break
    if hdr is None:
        raise ValueError("could not locate GameState object entry")
    loc.entry_hdr = hdr
    loc.entry_size_off = hdr + 8
    loc.entry_size = struct.unpack_from('<i', body, loc.entry_size_off)[0]
    loc.entry_data = hdr + 12
    loc.entry_end = loc.entry_data + loc.entry_size

    # the object section this entry lives in: walk entries forward from our
    # entry to the section end, then find the int64 length field pointing there
    p = loc.entry_hdr
    while p + 12 <= len(body):
        sv, fl, sz = struct.unpack_from('<iii', body, p)
        if sv != SAVE_VER or fl != 0 or sz < 0 or p + 12 + sz + 4 > len(body):
            break
        p += 12 + sz + 4
    loc.section_end = p

    hits = [L for L in range(0, loc.entry_hdr)
            if 0 < struct.unpack_from('<q', body, L)[0] < len(body)
            and L + 8 + struct.unpack_from('<q', body, L)[0] == loc.section_end]
    if len(hits) != 1:
        raise ValueError(f"expected 1 object-section length field, found {len(hits)}")
    loc.section_size_off = hits[0]

    # sanity: header count == object count
    hdr_count = struct.unpack_from('<i', body, loc.section_size_off + 8)[0]
    if hdr_count <= 0:
        raise ValueError("implausible object count")
    loc.object_count = hdr_count

    loc.body_size_off = 0
    if struct.unpack_from('<q', body, 0)[0] != len(body) - 8:
        raise ValueError("body size field does not match body length")
    return loc


def read_categories(body, loc):
    r = Reader(body, loc.prop_off)
    props, _ = read_props(r, stop_at=loc.entry_end)
    if len(props) != 1 or props[0].name != "mBlueprintCategoryRecords":
        raise ValueError("unexpected property layout at anchor")
    prop = props[0]
    loc.prop_end = r.p
    # round-trip check: re-serialising must reproduce the exact original bytes
    original = body[loc.prop_off:loc.prop_end]
    if write_props([prop], terminate=True) != original:
        raise ValueError("round-trip mismatch -- refusing to touch the save")
    return prop


def splice(body, loc, new_bytes):
    """Replace the property and fix every enclosing length field."""
    old = loc.prop_end - loc.prop_off
    delta = len(new_bytes) - old
    out = bytearray(body[:loc.prop_off]) + new_bytes + bytearray(body[loc.prop_end:])

    def bump32(off):
        v = struct.unpack_from('<i', out, off)[0] + delta
        struct.pack_into('<i', out, off, v)

    def bump64(off):
        v = struct.unpack_from('<q', out, off)[0] + delta
        struct.pack_into('<q', out, off, v)

    bump32(loc.entry_size_off)
    bump64(loc.section_size_off)
    bump64(loc.body_size_off)
    return bytes(out), delta


def verify(body):
    """Re-parse from scratch and confirm every framing invariant still holds."""
    if struct.unpack_from('<q', body, 0)[0] != len(body) - 8:
        raise ValueError("verify: body size field wrong")
    loc = locate(body)
    count = struct.unpack_from('<i', body, loc.section_size_off + 8)[0]
    p = loc.section_size_off + 12
    for _ in range(count):
        sv, fl, sz = struct.unpack_from('<iii', body, p)
        if sv != SAVE_VER or fl != 0 or sz < 0:
            raise ValueError(f"verify: bad object entry at {p}")
        p += 12 + sz + 4
    if p != loc.section_end:
        raise ValueError(f"verify: object walk ended at {p}, section ends at {loc.section_end}")
    r = Reader(body, loc.prop_off)
    props, terminated = read_props(r, stop_at=loc.entry_end)
    if not terminated:
        raise ValueError("verify: property list not terminated by None")
    # read_props consumes the "None" terminator; the object data then ends
    # with a single int32 0
    tail = body[r.p:loc.entry_end]
    if tail != b'\x00\x00\x00\x00':
        raise ValueError(f"verify: unexpected object tail {tail!r}")
    return loc, props[0]
