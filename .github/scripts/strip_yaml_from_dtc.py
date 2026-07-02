#!/usr/bin/env python3
"""
strip_yaml_from_dtc.py

Menghapus seluruh blok Makefile conditional (ifeq/ifneq ... [else] ... endif)
yang berhubungan dengan YAML support di scripts/dtc/Makefile.

Kenapa gak pakai sed baris-per-baris:
Kalau cuma menghapus baris yang match kata "yaml" (misal baris ifneq-nya),
tapi baris `else`/`endif` pasangannya gak ikut kehapus, struktur Makefile
jadi rusak -> error "extraneous 'else'". Script ini melacak kedalaman
blok if/else/endif secara benar, dan cuma menghapus blok yang utuh dan
memang terkait yaml (dan baris `yamltree.o` yang ada di luar blok if,
kalau ada).
"""

import re
import sys
from pathlib import Path

IF_RE = re.compile(r"^\s*(ifeq|ifneq|ifdef|ifndef)\b")
ELSE_RE = re.compile(r"^\s*else\b")
ENDIF_RE = re.compile(r"^\s*endif\b")


def strip_yaml_blocks(lines):
    """
    Pass 1: hapus blok if/else/endif yang KONDISI-nya (baris ifeq/ifneq)
    menyinggung 'yaml'.
    """
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if IF_RE.match(line) and "yaml" in line.lower():
            # cari endif yang cocok, dengan tracking nested if
            depth = 1
            j = i + 1
            while j < n and depth > 0:
                if IF_RE.match(lines[j]):
                    depth += 1
                elif ENDIF_RE.match(lines[j]):
                    depth -= 1
                j += 1
            # skip seluruh blok dari i sampai j-1 (termasuk endif-nya)
            i = j
            continue
        out.append(line)
        i += 1
    return out


def strip_standalone_yaml_lines(lines):
    """
    Pass 2: hapus baris standalone (di luar blok if) yang assign yamltree.o
    atau -lyaml langsung, tanpa merusak struktur if/else/endif lain.
    """
    out = []
    for line in lines:
        low = line.lower()
        if "yamltree.o" in low or ("lyaml" in low and "yaml-0.1" not in low):
            continue
        out.append(line)
    return out


def main():
    if len(sys.argv) != 2:
        print("Usage: strip_yaml_from_dtc.py <path-to-scripts/dtc/Makefile>")
        sys.exit(1)

    mk_path = Path(sys.argv[1])
    if not mk_path.exists():
        print(f"PERINGATAN: {mk_path} tidak ditemukan, skip patch.")
        sys.exit(0)

    original = mk_path.read_text().splitlines(keepends=True)

    step1 = strip_yaml_blocks(original)
    step2 = strip_standalone_yaml_lines(step1)

    mk_path.write_text("".join(step2))

    removed = len(original) - len(step2)
    print(f"Selesai. {removed} baris terkait yaml dihapus dari {mk_path}")

    remaining = [l for l in step2 if "yaml" in l.lower()]
    if remaining:
        print("PERINGATAN: masih ada sisa baris menyinggung yaml:")
        for l in remaining:
            print("  " + l.rstrip())
    else:
        print("Bersih, tidak ada referensi yaml lagi di file ini.")


if __name__ == "__main__":
    main()
