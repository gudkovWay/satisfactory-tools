#!/usr/bin/env python3
"""Жёстко выключает "Half Pipeline Flow Capacity" в моде HeavyFluids 1.4.5.

SML не применяет значение этой галки из сейва (откатывает к дефолту мода true),
поэтому чинится патчем самого мода: функция-хелпер, читающая настройку,
всегда возвращает false -> деление потока не выполняется ни в одном из мест.

Игра должна быть закрыта.

  python3 hf-unhalve.py           # применить патч (делает .orig бэкап)
  python3 hf-unhalve.py --revert  # вернуть оригинальный мод
  python3 hf-unhalve.py --check   # только показать текущее состояние
"""
import os
import shutil
import sys

MODDIR = os.path.expanduser(
    "~/games/SteamLibrary/steamapps/common/Satisfactory/FactoryGame/"
    "Mods/GameFeatures/HeavyFluids/Binaries/Win64")

DLLS = ["FactoryGameSteam-HeavyFluids-Win64-Shipping.dll",
        "FactoryGameEGS-HeavyFluids-Win64-Shipping.dll"]

# (смещение в файле, оригинальные байты, пропатченные байты, описание)
# .text: VMA 0x180001000 -> file offset 0x400
PATCHES = [
    (0xabb0, "4883ec38", "31c0c3",
     "хелпер IsHalfFlowEnabled -> xor eax,eax; ret (всегда false)"),
    (0xc3eb, "ffd3", "31c0",
     "SetPipeline: call GetBoolOptionValue -> xor eax,eax (делитель = 1)"),
]


def state(data):
    """'orig' | 'patched' | 'unknown' для набора патчей."""
    orig = patched = 0
    for off, o, p, _ in PATCHES:
        cur = data[off:off + len(bytes.fromhex(o))]
        if cur == bytes.fromhex(o):
            orig += 1
        elif cur[:len(bytes.fromhex(p))] == bytes.fromhex(p):
            patched += 1
    if orig == len(PATCHES):
        return "orig"
    if patched == len(PATCHES):
        return "patched"
    return "unknown"


def main():
    mode = "apply"
    if "--revert" in sys.argv:
        mode = "revert"
    elif "--check" in sys.argv:
        mode = "check"

    for name in DLLS:
        path = os.path.join(MODDIR, name)
        if not os.path.exists(path):
            continue
        data = open(path, "rb").read()
        st = state(data)
        print(f"\n{name}: {st}")

        if mode == "check":
            for off, o, p, desc in PATCHES:
                cur = data[off:off + 4].hex(" ")
                print(f"  0x{off:05x}: {cur}   [{desc}]")
            continue

        if mode == "revert":
            bak = path + ".orig"
            if os.path.exists(bak):
                shutil.copy2(bak, path)
                print("  восстановлен из .orig")
            else:
                print("  бэкапа .orig нет — нечего восстанавливать")
            continue

        if st == "patched":
            print("  уже пропатчен, пропуск")
            continue
        if st != "orig":
            print("  БАЙТЫ НЕ СОВПАДАЮТ с ожидаемыми — версия мода другая, пропуск")
            continue

        if not os.path.exists(path + ".orig"):
            shutil.copy2(path, path + ".orig")
            print("  бэкап -> " + name + ".orig")

        buf = bytearray(data)
        for off, o, p, desc in PATCHES:
            new = bytes.fromhex(p)
            buf[off:off + len(new)] = new
            print(f"  0x{off:05x}: {o} -> {p}   [{desc}]")
        open(path, "wb").write(bytes(buf))
        print("  записан")

    print("\nГотово." if mode != "check" else "")


main()
