"""Reading Windows registry files ("regf" format: the ones in
system32/config, such as "software", which is HKLM\\SOFTWARE).

  hive = Hive(path)
  hive.value("Classes\\Folder")            -> the key's (Default) value
  hive.value("Classes\\.doc", "Content Type")
  hive.subkeys("Classes")                  -> names of the subkeys

Read only, only what is needed: keys (nk), subkey lists (lf, lh, li, ri),
text values (vk) (REG_SZ / REG_EXPAND_SZ) and numbers (REG_DWORD).
"""
import struct

HBIN = 0x1000          # cell offsets count from here


class Hive:
    def __init__(self, path):
        with open(path, "rb") as f:
            self.d = f.read()
        if self.d[:4] != b"regf":
            raise ValueError(f"{path}: não é um ficheiro de registo")
        self.root = struct.unpack_from("<I", self.d, 0x24)[0]

    def _cell(self, off):
        return HBIN + off + 4            # (the cell size comes first)

    def _name(self, o, length, ascii_name):
        raw = self.d[o:o + length]
        return raw.decode("latin-1") if ascii_name else raw.decode("utf-16le")

    def _key(self, off):
        """(name, number of subkeys, subkey list, number of values, value list)."""
        o = self._cell(off)
        if self.d[o:o + 2] != b"nk":
            raise ValueError("chave inválida")
        flags, = struct.unpack_from("<H", self.d, o + 2)
        nsub, = struct.unpack_from("<I", self.d, o + 0x14)
        subs, = struct.unpack_from("<I", self.d, o + 0x1C)
        nval, valist = struct.unpack_from("<II", self.d, o + 0x24)
        nlen, = struct.unpack_from("<H", self.d, o + 0x48)
        return self._name(o + 0x4C, nlen, flags & 0x20), nsub, subs, nval, valist

    def _subkey_offsets(self, off):
        o = self._cell(off)
        sig = self.d[o:o + 2]
        n, = struct.unpack_from("<H", self.d, o + 2)
        if sig in (b"lf", b"lh"):
            return [struct.unpack_from("<I", self.d, o + 4 + i * 8)[0] for i in range(n)]
        if sig == b"li":
            return [struct.unpack_from("<I", self.d, o + 4 + i * 4)[0] for i in range(n)]
        if sig == b"ri":                  # list of lists
            out = []
            for i in range(n):
                out += self._subkey_offsets(struct.unpack_from("<I", self.d, o + 4 + i * 4)[0])
            return out
        raise ValueError(f"lista de subchaves desconhecida: {sig!r}")

    def _children(self, off):
        _name, nsub, subs, _nval, _valist = self._key(off)
        if not nsub:
            return {}
        return {self._key(k)[0].lower(): k for k in self._subkey_offsets(subs)}

    def _find(self, path):
        off = self.root
        for part in [p for p in path.split("\\") if p]:
            kids = self._children(off)
            if part.lower() not in kids:
                raise KeyError(path)
            off = kids[part.lower()]
        return off

    def subkeys(self, path):
        return [self._key(k)[0] for k in self._children(self._find(path)).values()]

    def value(self, path, name=""):
        """A value of a key ("" = the default value); None if there is none."""
        _n, _ns, _s, nval, valist = self._key(self._find(path))
        lo = self._cell(valist)
        for i in range(nval):
            vo = self._cell(struct.unpack_from("<I", self.d, lo + i * 4)[0])
            if self.d[vo:vo + 2] != b"vk":
                continue
            nlen, size, data_off, vtype, flags = struct.unpack_from("<HIIIH", self.d, vo + 2)
            vname = self._name(vo + 0x14, nlen, flags & 1)
            if vname.lower() != name.lower():
                continue
            if size & 0x80000000:         # data stored in the field itself
                size &= 0x7FFFFFFF
                data = struct.pack("<I", data_off)[:size]
            else:
                data = self.d[self._cell(data_off):self._cell(data_off) + size]
            if vtype in (1, 2):           # REG_SZ, REG_EXPAND_SZ
                return data.decode("utf-16le").split("\0")[0]
            if vtype == 4:                # REG_DWORD
                return struct.unpack("<I", data[:4])[0]
            return data
        return None
