#!/usr/bin/env python3

"""
utility_HTML_orchestrator.py

HTML EOB Pipeline Utility

Runs the full HTML → EDI workflow in correct order:

1. PSC Core
2. PSC_EDI_only Core
3. HTML Compiler
4. HTML Renamer
"""

from system_PSC_core import run_psc_core
from system_PSC_EDI_only_core import run_psc_edi_core
from system_HTML_compile import run_era_compile
from system_HTML_rename import run_era_rename


def run_era_pipeline():
    print("\n==============================================")
    print("        HTML EOB PIPELINE — BEGIN")
    print("==============================================\n")

    print("\n🔵 STEP 1 — PSC CORE")
    run_psc_core()

    print("\n🟣 STEP 2 — PSC_EDI_ONLY FILTER")
    run_psc_edi_core()

    print("\n🟡 STEP 3 — HTML COMPILER")
    run_era_compile()

    print("\n🟢 STEP 4 — HTML RENAMER")
    run_era_rename()

    print("\n==============================================")
    print("        HTML EOB PIPELINE — COMPLETE ✔")
    print("==============================================\n")


if __name__ == "__main__":
    run_era_pipeline()
