#!/usr/bin/env python3
"""
PipelineMk3Plus (v1.0.0, собран под Satisfactory CL 383729) не грузится на
CL 502094: единственный неразрешённый импорт из Core —

    old  ?GetBlocks@FNameDebugVisualizer@@SAPEAPEAEXZ    (static)
    new  ?GetBlocks@FNameDebugVisualizer@@QEAAPEAPEAEXZ  (нестатический метод)

Тело новой функции: `lea rax,[rip+X]; ret` — this (RCX) игнорируется,
поэтому вызов по старому соглашению безопасен.

Имя длиннее на 2 байта, поэтому IMAGE_IMPORT_BY_NAME переносится в
нулевой хвост .rdata, а записи OFT и IAT перенаправляются на него.

Использование:  pmk3-fiximport.py [--check|--revert]
"""
import struct, sys, os, shutil

OLD = b'?GetBlocks@FNameDebugVisualizer@@SAPEAPEAEXZ'
NEW = b'?GetBlocks@FNameDebugVisualizer@@QEAAPEAPEAEXZ'

MODDIR = '/home/q/games/SteamLibrary/steamapps/common/Satisfactory/FactoryGame/Mods/PipelineMk3Plus/Binaries/Win64'
TARGETS = ['FactoryGameSteam-PipelineMk3Plus-Win64-Shipping.dll',
           'FactoryGameEGS-PipelineMk3Plus-Win64-Shipping.dll']

def sections(d):
    pe = struct.unpack_from('<I', d, 0x3c)[0]
    nsec = struct.unpack_from('<H', d, pe + 6)[0]
    optsz = struct.unpack_from('<H', d, pe + 20)[0]
    opt = pe + 24
    secs = []
    for i in range(nsec):
        o = opt + optsz + i * 40
        vsz, va, rawsz, raw = struct.unpack_from('<IIII', d, o + 8)
        secs.append((d[o:o+8].rstrip(b'\0').decode(), va, vsz, raw, rawsz))
    return pe, opt, secs

def r2o(secs, r):
    for n, va, vsz, raw, rawsz in secs:
        if va <= r < va + max(vsz, rawsz):
            return raw + (r - va)
    return None

def find_thunks(d, secs, opt):
    """вернуть [(file_off_of_thunk_entry, name_rva)] для OFT и IAT, где имя == OLD"""
    imp_rva = struct.unpack_from('<I', d, opt + 112 + 8)[0]
    o = r2o(secs, imp_rva)
    hits = []
    while True:
        oft, ts, fc, nrva, ft = struct.unpack_from('<IIIII', d, o)
        if oft == 0 and nrva == 0:
            break
        dllname = bytes(d[r2o(secs, nrva):r2o(secs, nrva) + 100]).split(b'\0')[0]
        for arr_rva in (oft, ft):
            if not arr_rva:
                continue
            t = r2o(secs, arr_rva)
            i = 0
            while True:
                v = struct.unpack_from('<Q', d, t + i * 8)[0]
                if v == 0:
                    break
                if not (v >> 63):
                    ho = r2o(secs, v)
                    nm = bytes(d[ho + 2:ho + 200]).split(b'\0')[0]
                    if nm == OLD:
                        hits.append((t + i * 8, v, dllname.decode()))
                i += 1
        o += 20
    return hits

def find_free(d, secs, need):
    """нулевой хвост внутри VirtualSize секции .rdata"""
    for n, va, vsz, raw, rawsz in secs:
        if n != '.rdata':
            continue
        end_off = raw + vsz
        run = 0
        for off in range(raw, end_off):
            if d[off] == 0:
                run += 1
                if run >= need + 8:          # запас
                    start = off - run + 1
                    start = (start + 1) & ~1  # выравнивание на 2
                    return start, va + (start - raw)
            else:
                run = 0
    return None, None

def process(path, mode):
    d = bytearray(open(path, 'rb').read())
    pe, opt, secs = sections(d)
    cur = bytes(d).count(NEW)
    hits = find_thunks(d, secs, opt)

    if mode == 'check':
        print(f'  {os.path.basename(path)}: старых записей={len(hits)}, новое имя в файле={"есть" if cur else "нет"}'
              f' -> {"ПРОПАТЧЕН" if cur and not hits else ("ОРИГИНАЛ" if hits else "неизвестно")}')
        return

    if mode == 'revert':
        bak = path + '.orig'
        if os.path.exists(bak):
            shutil.copy2(bak, path)
            print(f'  {os.path.basename(path)}: восстановлен из .orig')
        else:
            print(f'  {os.path.basename(path)}: .orig не найден')
        return

    if not hits:
        print(f'  {os.path.basename(path)}: старых записей нет — уже пропатчен, пропускаю')
        return

    bak = path + '.orig'
    if not os.path.exists(bak):
        shutil.copy2(path, bak)

    start, new_rva = find_free(d, secs, 2 + len(NEW) + 1)
    if start is None:
        print(f'  {os.path.basename(path)}: НЕ НАШЁЛ свободного места в .rdata')
        return
    d[start:start + 2] = b'\x00\x00'                    # Hint = 0
    d[start + 2:start + 2 + len(NEW)] = NEW
    d[start + 2 + len(NEW)] = 0
    for thunk_off, old_rva, dllname in hits:
        struct.pack_into('<Q', d, thunk_off, new_rva)
    open(path, 'wb').write(d)
    print(f'  {os.path.basename(path)}: перенёс имя в .rdata @RVA {hex(new_rva)}, '
          f'обновил {len(hits)} записи (OFT+IAT), импорт из {hits[0][2]}')

def main():
    mode = 'patch'
    if len(sys.argv) > 1:
        a = sys.argv[1]
        if a == '--check': mode = 'check'
        elif a == '--revert': mode = 'revert'
        else:
            print(__doc__); return 1
    print({'patch': 'ПАТЧ', 'check': 'ПРОВЕРКА', 'revert': 'ОТКАТ'}[mode] + ':')
    for t in TARGETS:
        p = os.path.join(MODDIR, t)
        if os.path.exists(p):
            process(p, mode)
    return 0

sys.exit(main())
