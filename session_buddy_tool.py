#!/usr/bin/python
#
# Session Buddy Chrome Extension tool
#
# TODO:
# * update existing item with new 1links collection
# * check if exists in GetPocket and insert if not?
# * find extension db path? what about cross-platform shit?

# download the crx and unpack as zip
# background.bundle.js
# https://robwu.nl/crxviewer/?crx=https%3A%2F%2Fchrome.google.com%2Fwebstore%2Fdetail%2Fsession-buddy%2Fedacconmaakjimmfgnblocblbcdcpbko%3Fhl%3Den

import sys
import argparse
import ujson
import yaml
import sqlite3
from pathlib import Path
from dataclasses import dataclass


@dataclass
class TabInfo:
    title: str
    url: str


@dataclass
class LinkInfo:
    id: int
    item_list: list = None


#
# Helpers
#
def extract_links(row, full):
    tabs = ujson.decode(row[1])

    row_id = None
    for key in tabs[0].keys():

        obj = tabs[0][key]

        if key == "id":
            row_id = obj

        elif key == "tabs":
            item_list = []

            for i in obj:
                if full:
                    item_list.append(i)
                else:
                    item_list.append(TabInfo(i["title"], i["url"]))

    return LinkInfo(row_id, item_list)


# TODO: maybe use sets to speed things up?
def remove_duplicates(item_list):
    seen_list = []
    unique_list = []
    for item in item_list:
        if item.url not in seen_list:
            seen_list.append(item.url)
            unique_list.append(item)
    return unique_list


def filter_excluded(item_list, excluded_url_list):
    sus_ext = "chrome-extension://klbibkeccnjlkjkiokjodocebajanakg"
    filtered = []
    for item in item_list:
        url = item.url
        if url.startswith(sus_ext):
            try:
                uri_loc = url.rindex("uri=")
                item.url = url[uri_loc + 4:]
            except Exception:
                pass
        found = False
        for url in excluded_url_list:
            if item.url.startswith(url):
                found = True
                break

        if not found:
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


def get_saved_sessions(conn, tname, full):
    sessions = []
    cur = conn.cursor()
    cur.execute(f"SELECT id, windows FROM {tname};")
    for row in cur.fetchall():
        link_info = extract_links(row, full)
        sessions += link_info.item_list
    return sessions


def insert_row(conn, tname, row_id, item_list):
    cur = conn.cursor()
    cur.execute(f"INSERT INTO {tname} VALUES();")


def delete_row(conn, tname, row_id):
    cur = conn.cursor()
    cur.execute(f"DELETE * FROM {tname} WHERE id={row_id};")


#
# Actions
#
def action_export(conn, table_list, excluded_url_list):
    item_list = []
    for tname in table_list:
        item_list += get_saved_sessions(conn, tname, full=False)

    item_list = remove_duplicates(
        filter_excluded(
            item_list,
            excluded_url_list))

    print(yaml.dump(item_list))
    # print(ujson.encode(item_list))


def action_merge(conn, table_list, excluded_url_list):
    item_list = []
    for tname in table_list:
        item_list += get_saved_sessions(conn, tname, full=True)

    item_list = remove_duplicates(
        filter_excluded(
            item_list,
            excluded_url_list))

    # TODO: merge records
    # TODO: clear existing sessions
    # TODO: add new session with merged data


def action_clean(conn, table_list, excluded_url_list):
    cur = conn.cursor()
    for tname in table_list:
        cur.execute(f"DELETE * FROM {tname}")


def main(argv=None):
    if not argv:
        argv = sys.argv

    table_list = ["SavedSessions", "PreviousSessions"]

    # handle commandline arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a",
        "--action",
        choices=['export', 'merge', 'clean'],
        help="Action: export, merge, clean",
        required=True)
    parser.add_argument(
        "-e",
        "--exclude",
        help="Path to file with excluded url_list",
        required=False)
    parser.add_argument(
        "-p",
        "--profile",
        help="Path to Chrome profile",
        required=False)

    args = parser.parse_args()

    # apply parsed commandline arguments
    excluded_url_list = []
    if args.exclude:
        with open(args.exclude) as f:
            excluded_url_list = f.readlines()

    chrome_profile = Path.home() / ".config" / "google-chrome" / "Default"
    if args.profile:
        chrome_profile = Path(args.chrome_profile)

    ext_id = "chrome-extension_edacconmaakjimmfgnblocblbcdcpbko_0"
    ext_ver = "3"
    db_path = chrome_profile / "databases" / ext_id / ext_ver

    rc = 0  # assume success
    print(f"{db_path=}")
    with sqlite3.connect(db_path) as conn:
        if args.action == "export":
            action_export(conn, table_list, excluded_url_list)
        elif args.action == "clean":
            action_clean(conn, table_list, excluded_url_list)
        elif args.action == "merge":
            action_merge(conn, table_list, excluded_url_list)
        else:
            parser.print_help()
            rc = -1
    return rc


if __name__ == "__main__":
    exit(main())
