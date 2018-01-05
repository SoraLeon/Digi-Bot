import os
import sqlite3

# Databases filenames
import shutil

USERDB = "users.db"

userDatabase = sqlite3.connect(USERDB)

DB_LASTVERSION = 1

# Dictionaries of welcome messages per server
welcome_messages = {}

# Dictionaries of announce channels per server
announce_channels = {}


def init_database():
    """Initializes and/or updates the database to the current version"""

    # Database file is automatically created with connect, now we have to check if it has tables
    print("Checking database version...")
    try:
        c = userDatabase.cursor()
        c.execute("SELECT COUNT(*) as count FROM sqlite_master WHERE type = 'table'")
        result = c.fetchone()
        # Database is empty
        if result is None or result["count"] == 0:
            # 'users'
            c.execute("""CREATE TABLE users (
                      id INTEGER NOT NULL,
                      weight INTEGER DEFAULT 5,
                      name TEXT,                      
                      PRIMARY KEY(id)
                      )""")
            # 'events' table
            c.execute("""CREATE TABLE events (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      creator INTEGER,
                      name TEXT,
                      start INTEGER,
                      duration INTEGER,
                      description TEXT,
                      server INTEGER,
                      active INTEGER DEFAULT 1
                      )""")
            # 'user_servers'          
            c.execute("""CREATE TABLE user_servers (
                      id INTEGER,
                      server INTEGER,
                      name TEXT,
                      last_message DATETIME,
                      PRIMARY KEY(id,server)
                      );""")
            # 'server_properties' table
            c.execute("""CREATE TABLE server_properties (
                      server_id TEXT,
                      name TEXT,
                      value TEXT
                      );""")          
        # DB Info
        c.execute("SELECT tbl_name FROM sqlite_master WHERE type = 'table' AND name LIKE 'db_info'")
        result = c.fetchone()
        # If there's no version value, version 1 is assumed
        if result is None:
            c.execute("""CREATE TABLE db_info (
                      key TEXT,
                      value TEXT
                      )""")
            c.execute("INSERT INTO db_info(key,value) VALUES('version','1')")
            db_version = 1
            print("No version found, version 1 assumed")
        else:
            c.execute("SELECT value FROM db_info WHERE key LIKE 'version'")
            db_version = int(c.fetchone()["value"])
            print("Version {0}".format(db_version))
        if db_version == DB_LASTVERSION:
            print("Database is up to date.")
            return

    finally:
        userDatabase.commit()


def dict_factory(cursor, row):
    """Makes values returned by cursor fetch functions return a dictionary instead of a tuple.

    To implement this, the connection's row_factory method must be replaced by this one."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

userDatabase.row_factory = dict_factory


def reload_welcome_messages():
    c = userDatabase.cursor()
    welcome_messages_temp = {}
    try:
        c.execute("SELECT server_id, value FROM server_properties WHERE name = 'welcome'")
        result = c.fetchall()
        if len(result) > 0:
            for row in result:
                welcome_messages_temp[row["server_id"]] = row["value"]
        welcome_messages.clear()
        welcome_messages.update(welcome_messages_temp)
    finally:
        c.close()


def reload_announce_channels():
    c = userDatabase.cursor()
    announce_channels_temp = {}
    try:
        c.execute("SELECT server_id, value FROM server_properties WHERE name = 'announce_channel'")
        result = c.fetchall()
        if len(result) > 0:
            for row in result:
                announce_channels_temp[row["server_id"]] = row["value"]
        announce_channels.clear()
        announce_channels.update(announce_channels_temp)
    finally:
        c.close()
