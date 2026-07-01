#!/usr/bin/env python3
"""
Renfrew Calendar Manager — CONTROLLER ONLY
This file contains:
- CLI
- Command parsing
- High‑level dispatch

All business logic lives in:
    system_calendar_core.py
    system_posting_core.py
    system_EMR_core.py
"""

from system_calendar_core import (
    init_db,
    setup,
    add_days,
    build_from,
    delete_days,
    show_status,
    show_calendar_range,
    set_current_work_day,
    advance_current_work_day,
    get_current_work_day,
)

from system_posting_core import (
    show_items_for_workday,
    export_posting_to_csv,
)

from system_EMR_core import (
    rebuild_edi_matchresults_core,
)


def print_help():
    print("""
Renfrew Calendar Manager — Commands

CALENDAR / BUILD
  setup MM/DD/YYYY          - Reset calendar and anchor first bank day (OPEN)
  add N                     - Add N bank days after highest existing
  build-from MM/DD/YYYY N   - Setup from date and add N days
  delete-days FROM TO       - Delete calendar days between FROM and TO (bank_day)
  status                    - Show calendar status and current work day
  show-range FROM TO        - Show calendar range with EFT/Lockbox totals

WORK DAY / POSTING
  set-work MM/DD/YYYY       - Set current work day (paperwork_day)
  advance-work              - Advance to next open work day
  show-items MM/DD/YYYY     - Show posting screen for paperwork day
  export-posting MM/DD/YYYY - Export posting screen to CSV for paperwork day

EDI / UTIL
  rebuild-edi               - Rebuild EDI_MatchResults from EDI/Lockbox/EFT

GENERAL
  help                      - Show this help
  quit                      - Exit
""")


def main():
    init_db()

    # Auto-load posting screen if a work day is already set
    current = get_current_work_day()
    if current:
        try:
            rebuild_edi_matchresults_core()
            show_items_for_workday(current)
        except Exception as e:
            print("Error during startup posting screen:")
            print(e)

    while True:
        try:
            cmd = input("\nCalendar> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not cmd:
            continue

        parts = cmd.split()
        op = parts[0].lower()

        if op in ("quit", "exit", "q"):
            print("Goodbye.")
            break

        elif op == "help":
            print_help()

        elif op == "status":
            show_status()

        elif op == "setup" and len(parts) == 2:
            setup(parts[1])

        elif op == "add" and len(parts) == 2:
            try:
                n = int(parts[1])
                add_days(n)
            except ValueError:
                print("Invalid number of days.")

        elif op == "build-from" and len(parts) == 3:
            try:
                n = int(parts[2])
                build_from(parts[1], n)
            except ValueError:
                print("Invalid number of days.")

        elif op == "delete-days" and len(parts) == 3:
            delete_days(parts[1], parts[2])

        elif op == "show-range" and len(parts) == 3:
            show_calendar_range(parts[1], parts[2])

        elif op == "set-work" and len(parts) == 2:
            set_current_work_day(parts[1])

        elif op == "advance-work":
            advance_current_work_day()

        elif op == "show-items" and len(parts) == 2:
            show_items_for_workday(parts[1])

        elif op == "export-posting" and len(parts) == 2:
            export_posting_to_csv(parts[1])

        elif op == "rebuild-edi":
            rebuild_edi_matchresults_core()

        else:
            print("Unknown command. Type 'help' for options.")


if __name__ == "__main__":
    main()
