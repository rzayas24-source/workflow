#!/usr/bin/env python3

"""
utility_Rename_ERA_compile.py

ERA Pipeline Utility

Runs the full ERA workflow in correct order:

1. PSC Core       (EMR → Posting Screen → PSC Capture)
2. ERA Compiler   (PSC_EDI_only → proposed_edi)
3. ERA Renamer    (proposed_edi → rename ERA files)
"""

from system_PSC_core import run_psc_core
from system_ERA_compile import run_era_compile
from system_ERA_rename import run_era_rename


def run_era_pipeline():
    print("\n==============================================")
    print("        ERA PIPELINE — BEGIN")
    print("==============================================\n")

    # 1️⃣ PSC CORE — MUST RUN FIRST
    print("\n🔵 STEP 1 — PSC CORE")
    run_psc_core()

    # 2️⃣ ERA COMPILER
    print("\n🟡 STEP 2 — ERA COMPILER")
    run_era_compile()

    # 3️⃣ ERA RENAMER
    print("\n🟢 STEP 3 — ERA RENAMER")
    run_era_rename()

    print("\n==============================================")
    print("        ERA PIPELINE — COMPLETE ✔")
    print("==============================================\n")


if __name__ == "__main__":
    run_era_pipeline()
