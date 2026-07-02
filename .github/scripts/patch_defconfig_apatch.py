#!/usr/bin/env python3
"""
patch_defconfig_apatch.py

Patch defconfig kernel cepheus (4.14 non-GKI) supaya siap dipakai APatch.
Dipanggil dari workflow build-apatch.yml.

Kenapa config ini penting:
- CONFIG_KALLSYMS_ALL=y  -> APatch butuh resolve SEMUA symbol kernel
                             (bukan cuma exported symbols) buat cari
                             fungsi target patch-nya secara runtime.
                             Ini yang paling sering jadi biang bootloop
                             kalau stock config cuma set CONFIG_KALLSYMS=y
                             tanpa _ALL.
- CONFIG_KALLSYMS=y      -> prasyarat dasar, biasanya sudah aktif di
                             stock config, tapi tetap dipaksa di sini.
- CONFIG_MODULES=y       -> diperlukan kalau nanti mau pakai KPM
                             (Kernel Patch Module) di APatch.
- CONFIG_MODULE_UNLOAD=y -> opsional, memudahkan unload KPM saat testing.
- CONFIG_KSU=y           -> WAJIB dinyalain, BUKAN buat dipakai bareng
                             APatch. Source kernel Spark-Devices ini
                             sudah punya hook KernelSU tertanam permanen
                             di fs/read_write.c, fs/stat.c, fs/exec.c,
                             drivers/input/input.c (pemanggilan
                             ksu_handle_vfs_read dkk TIDAK dibungkus
                             #ifdef CONFIG_KSU, cuma dibungkus variable
                             runtime). Kalau CONFIG_KSU dimatikan, driver
                             di drivers/staging/kernelsu/ gak ke-compile,
                             padahal hook-nya tetap manggil fungsi dari
                             situ -> undefined reference pas linking.
                             Driver ini TETAP PASIF selama tidak ada
                             app KernelSU Manager yang aktif komunikasi
                             ke kernel, jadi aman berdampingan dengan
                             APatch (APatch kerja independen lewat
                             patch boot.img, bukan lewat hook ini).
- CONFIG_OVERLAY_FS=y    -> dependency wajib buat CONFIG_KSU (lihat
                             drivers/staging/kernelsu/Kconfig).
"""

import re
import sys
from pathlib import Path

FORCE_ENABLE = [
    "CONFIG_KALLSYMS",
    "CONFIG_KALLSYMS_ALL",
    "CONFIG_MODULES",
    "CONFIG_MODULE_UNLOAD",
    "CONFIG_KSU",
    "CONFIG_OVERLAY_FS",
]

FORCE_DISABLE = [
    "CONFIG_KSU_DEBUG",
]


def set_enabled(lines, name):
    pattern_set = re.compile(rf"^{name}=.*$")
    pattern_unset = re.compile(rf"^# {name} is not set$")
    found = False
    for i, line in enumerate(lines):
        if pattern_set.match(line):
            lines[i] = f"{name}=y"
            found = True
        elif pattern_unset.match(line):
            lines[i] = f"{name}=y"
            found = True
    if not found:
        lines.append(f"{name}=y")
    return lines


def set_disabled(lines, name):
    pattern_set = re.compile(rf"^{name}=.*$")
    pattern_unset = re.compile(rf"^# {name} is not set$")
    found = False
    for i, line in enumerate(lines):
        if pattern_set.match(line):
            lines[i] = f"# {name} is not set"
            found = True
        elif pattern_unset.match(line):
            found = True
    if not found:
        lines.append(f"# {name} is not set")
    return lines


def main():
    if len(sys.argv) != 2:
        print("Usage: patch_defconfig_apatch.py <path-to-defconfig>")
        sys.exit(1)

    cfg_path = Path(sys.argv[1])
    if not cfg_path.exists():
        print(f"GAGAL: defconfig tidak ditemukan di {cfg_path}")
        sys.exit(1)

    lines = cfg_path.read_text().splitlines()

    for name in FORCE_ENABLE:
        lines = set_enabled(lines, name)
        print(f"[+] {name}=y")

    for name in FORCE_DISABLE:
        lines = set_disabled(lines, name)
        print(f"[-] {name} disabled")

    cfg_path.write_text("\n".join(lines) + "\n")
    print(f"\nSelesai patch: {cfg_path}")


if __name__ == "__main__":
    main()
