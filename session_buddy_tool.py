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
            item_list = [TabInfo(i["title"], i["url"]) for i in obj]

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

        # fix the url
        if url.startswith(sus_ext):
            # expand uri from Great Suspender extension
            try:
                uri_loc = url.rindex("uri=")
                item.url = url[uri_loc + 4:]
            except Exception:
                pass

        is_excluded = False
        for url in excluded_url_list:
            if item.url.startswith(url):
                is_excluded = True
                break

        if not is_excluded:
            filtered.append(item)

    return filtered


"""
tab_json
{
   "tabs": [
      {
         "active": false,
         "audible": false,
         "autoDiscardable": true,
         "discarded": false,
         "favIconUrl": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAABKElEQVRYR+2XIQ4CMRBFXxVIJA4cV0EiccsN9ggEiSOcABwSiSQcAYdb3EqCAlVStiULCWHbQoYQmtT9mfn9/Z2dVQgvJVyfP4HvVEBDHWgCDbuNVdqefsks/gCYnSs4Pea4U0AXRbtAy7NYVfgeWCnIXcCNgC0+AGpVswXizsDMkSgT6AOdwKS+YTsFCxNUJjD0zRKDVzC6EdCF2dKYhAGxY2PKqwK6cHhSOUmvB8tlZfgT4FxBFkZAa9hsIEkgc6/Nm08kAVPveITJBIZB9nkDAXfo7RbSFNZrHxneSMCVnU4LNQ6m8b1cv0RA7ApETSj6DD/QiGRbsW3HQd3k5WN7Arj7GFkC4p9jMw3JDSRWBbmRrHxVYkNpqKFi4r7zvyDmRL6xfwUuMUl+IYSS65sAAAAASUVORK5CYII=",
         "height": 595,
         "highlighted": false,
         "id": 1868,
         "incognito": false,
         "index": 0,
         "mutedInfo": {
            "muted": false
         },
         "pinned": false,
         "selected": false,
         "status": "complete",
         "title": "Building Realtime Serverless APIs with GraphQL and Azure - YouTube",
         "url": "chrome-extension://klbibkeccnjlkjkiokjodocebajanakg/suspended.html#ttl=Building%20Realtime%20Serverless%20APIs%20with%20GraphQL%20and%20Azure%20-%20YouTube&pos=0&uri=https://www.youtube.com/watch?v=0YOaYUYd2-s&t=0s",
         "width": 1362,
         "windowId": 1867
      },
"""


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


def get_db_path(args):

    chrome_profile = Path.home() / ".config" / "google-chrome" / "Default" \
        if not args.profile \
        else Path(args.chrome_profile)

    sb_ext_id = "chrome-extension_edacconmaakjimmfgnblocblbcdcpbko_0"
    sb_ext_ver = "3"
    return chrome_profile / "databases" / sb_ext_id / sb_ext_ver


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

    db_path = get_db_path(args)

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
