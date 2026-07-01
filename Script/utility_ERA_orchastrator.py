#!/usr/bin/env python3

"""
utility_ERA_orchastrator.py

ERA Pipeline Utility

Runs the full ERA workflow in correct order:

1. PSC Core               (PostingScreenCapture)
2. PSC_EDI_only Core      (Filter PSC → PSC_EDI_only)
3. ERA Compiler           (PSC_EDI_only → proposed_edi)
4. ERA Renamer            (proposed_edi → rename ERA files)
"""

from system_PSC_core import run_psc_core
from system_PSC_EDI_only_core import run_psc_edi_core
from system_ERA_compile import run_era_compile
from system_ERA_rename import run_era_rename


def run_era_pipeline():
    print("\n==============================================")
    print("        ERA PIPELINE — BEGIN")
    print("==============================================\n")

    # 1️⃣ PSC CORE — builds full PSC
    print("\n🔵 STEP 1 — PSC CORE")
    run_psc_core()

    # 2️⃣ PSC_EDI_ONLY — filters PSC down to EDI rows
    print("\n🟣 STEP 2 — PSC_EDI_ONLY FILTER")
    run_psc_edi_core()

    # 3️⃣ ERA COMPILER — builds proposed_edi
    print("\n🟡 STEP 3 — ERA COMPILER")
    run_era_compile()

    # 4️⃣ ERA RENAMER — renames ERA files
    print("\n🟢 STEP 4 — ERA RENAMER")
    run_era_rename()

    print("\n==============================================")
    print("        ERA PIPELINE — COMPLETE ✔")
    print("==============================================\n")


if __name__ == "__main__":
    run_era_pipeline()
