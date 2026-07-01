#!/usr/bin/env python3

import win32com.client
import os
from datetime import datetime
from db import get_conn   # ⭐ dynamic DB connection

DOWNLOAD_DIR = r"C:\Renfrew\1.COPY - Copy\3._SITES"

# Normalize Outlook datetime (remove timezone)
def normalize_outlook_datetime(dt):
    try:
        return dt.replace(tzinfo=None)
    except:
        return dt

def insert_into_db(email_id, filename, saved_path, note):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO EmailAttachmentHistory
        (email_id, original_filename, moved_to, review_status, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (email_id, filename, saved_path, "Pending", note))

    conn.commit()
    conn.close()

def pick_folder(outlook, prompt_title):
    inbox = outlook.GetDefaultFolder(6)

    print(f"\n{prompt_title}")
    for i, f in enumerate(inbox.Folders):
        print(f"{i+1}. {f.Name}")

    choice = input("\nEnter folder number: ").strip()
    index = int(choice) - 1
    return inbox.Folders[index]

def move_messages(messages, dest_folder):
    moved = 0
    for msg in messages:
        try:
            msg.Move(dest_folder)
            moved += 1
        except:
            pass
    return moved

def download_emails():
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")

    # ---------------------------
    # PICK SOURCE FOLDER
    # ---------------------------
    folder = pick_folder(outlook, "Folders under Inbox:")

    # ---------------------------
    # DATE DISCOVERY MENU
    # ---------------------------
    messages = folder.Items
    messages.Sort("[ReceivedTime]", True)

    date_set = set()

    for msg in messages:
        try:
            received = normalize_outlook_datetime(msg.ReceivedTime)
            date_set.add(received.date())
        except:
            pass

    sorted_dates = sorted(list(date_set), reverse=True)

    print("\nAvailable Dates in This Folder:")
    for i, d in enumerate(sorted_dates):
        print(f"{i+1}. {d}")

    choice = input("\nChoose a date number (or press Enter for ALL dates): ").strip()

    date_filter = None
    if choice:
        index = int(choice) - 1
        date_filter = sorted_dates[index]

    # ---------------------------
    # PROCESS EMAILS
    # ---------------------------
    downloaded_files = []
    processed_messages = []

    for msg in messages:
        try:
            received = normalize_outlook_datetime(msg.ReceivedTime)
        except:
            continue

        if date_filter and received.date() != date_filter:
            continue

        processed_messages.append(msg)
        email_id = msg.EntryID

        # No attachments → save body text
        if msg.Attachments.Count == 0:
            body = msg.Body
            filename = f"{email_id}.txt"
            path = os.path.join(DOWNLOAD_DIR, filename)

            with open(path, "w", encoding="utf-8") as f:
                f.write(body)

            insert_into_db(email_id, filename, path, "No attachment — saved body text")
            downloaded_files.append(path)
            continue

        # Save all attachments
        for att in msg.Attachments:
            filename = att.FileName
            save_path = os.path.join(DOWNLOAD_DIR, filename)
            att.SaveAsFile(save_path)

            insert_into_db(email_id, filename, save_path, "")
            downloaded_files.append(save_path)

    print("\nDownloaded:", downloaded_files)

    # ---------------------------
    # ASK TO MOVE EMAILS (Y/N)
    # ---------------------------
    while True:
        confirm = input("\nMove these emails to another folder? (Y/N): ").strip()

        if confirm == "Y":
            dest_folder = pick_folder(outlook, "Select destination folder:")
            moved = move_messages(processed_messages, dest_folder)
            print(f"\nMoved {moved} emails to: {dest_folder.Name}")
            input("\nPress Enter to exit...")
            break

        elif confirm == "N":
            print("\nEmails were NOT moved.")
            input("\nPress Enter to exit...")
            break

        else:
            print("Invalid choice. Please type Y or N.")

    return downloaded_files

if __name__ == "__main__":
    files = download_emails()
