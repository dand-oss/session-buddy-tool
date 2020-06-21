#!/usr/bin/python
#
# Session Buddy Chrome Extension tool
#
# TODO:
# * update existing item with new 1links collection
# * check if exists in GetPocket and insert if not?
# * find extension db path? what about cross-platform shit?

import sys
import traceback
import argparse
import cjson
import sqlite3
from pathlib import Path


#
# Helpers
#
def load_exclude_file(path):
    excluded = []
    if path.isfile():
        with open(path) as f:
            excluded = f.readlines()
    else:
        print("File with excluded urls can not be found!")
    return excluded


def extract_links(row, full):
    tabs = cjson.decode(row[1])
    row_id = None
    for key in tabs[0].keys():
        obj = tabs[0][key]
        if key == "id":
            row_id = obj
        elif key == "tabs":
            items = []
            for i in obj:
                if full:
                    items.append(i)
                else:
                    items.append({"title": i["title"], "url": i["url"]})
    return {"id": row_id, "items": items}


# TODO: maybe use sets to speed things up?
def remove_duplicates(items):
    seen = []
    unique = []
    for item in items:
        if not item["url"] in seen:
            seen.append(item["url"])
            unique.append(item)
    return unique


def filter_excluded(items, excluded_urls):
    filtered = []
    for item in items:
        found = 0
        for url in excluded_urls:
            if item["url"].startswith(url):
                found += 1
        if found == 0:
            filtered.append(item)
    return filtered


def build_tabs(id, top, width, heighttabs):
    tabs = 0
    height = 0
    return {
        "alwaysOnTop": False,
        "focused": True,
        "height": height,
        "id": id,
        "incognito": False,
        "left": 0,
        "state": "normal",
        "tabs": tabs,
        "top": top,
        "type": "normal",
        "width": width
    }


def get_saved_sessions(conn, table, full):
    sessions = []
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT id, windows FROM {table};")
        for row in cur.fetchall():
            item = extract_links(row, full)
            sessions += item["items"]

    except sqlite3.Error as e:
        print(f"Get sessions error: {e.args[0]}")
    return sessions


def insert_row(conn, table, row_id, items):
    try:
        cur = conn.cursor()
        cur.execute(f"INSERT INTO {table} VALUES();")
        return True
    except sqlite3.Error as e:
        print(f"Add merged sessions error: {e.args[0]}")
        return False


def delete_row(conn, table, row_id):
    try:
        cur = conn.cursor()
        cur.execute(f"DELETE * FROM {table} WHERE id={row_id};")
        return True
    except sqlite3.Error as e:
        print(f"Delete error: {e.args[0]}")
        return False


#
# Actions
#
def action_export(conn, tables, excluded_urls):
    items = []
    for table in tables:
        items += get_saved_sessions(conn, table, False)

    items = remove_duplicates(filter_excluded(items), excluded_urls)

    print(cjson.encode(items))


def action_merge(conn, tables, excluded_urls):
    items = []
    for table in tables:
        items += get_saved_sessions(conn, table, True)

    items = remove_duplicates(filter_excluded(items), excluded_urls)

    # TODO: merge records
    # TODO: clear existing sessions
    # TODO: add new session with merged data
    return None


def action_clean(conn, tables, excluded_urls):
    try:
        cur = conn.cursor()
        for table in tables:
            cur.execute(f"DELETE * FROM {table}")
    except sqlite3.Error as e:
        print(f"Cleanup error: {e.args[0]}")


def main(argv=None):
    if not argv:
        argv = sys.argv

    tables = ["SavedSessions", "PreviousSessions"]

    # handle commandline arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a",
        "--action",
        choices=['export', 'merge', 'clean'],
        help="Action: export, merge, clean", required=True)
    parser.add_argument(
        "-e",
        "--exclude",
        help="Path to file with excluded urls", required=False)
    parser.add_argument(
        "-p",
        "--profile",
        help="Path to Chrome profile", required=False)
    args = parser.parse_args()

    # apply parsed commandline arguments
    excluded_urls = []
    if args.exclude:
        excluded_urls = load_exclude_file(args.exclude)

    chrome_profile = Path.home() / ".config" / "google-chrome" / "Default"
    if args.profile:
        chrome_profile = Path(args.chrome_profile)

    extension = "chrome-extension_edacconmaakjimmfgnblocblbcdcpbko_0"
    db_path = f"{chrome_profile}/databases/{extension}/2"
    conn = sqlite3.connect(db_path)
    try:
        if args.action == "export":
            action_export(conn, tables, excluded_urls)
        elif args.action == "clean":
            action_clean(conn, tables, excluded_urls)
        elif args.action == "merge":
            action_merge(conn, tables, excluded_urls)
        else:
            parser.print_help()
            sys.exit(1)

        sys.exit(0)
    except Exception as e:
        print(f"Main error: {e}")
        print('-'*60)
        traceback.print_exc(file=sys.stdout)
        print('-'*60)
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    exit(main())
