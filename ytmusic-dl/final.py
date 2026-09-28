#!/usr/bin/env python3



# Import builtins (part of python)
import json
import subprocess
import sys
import os
import urllib.request
import urllib.parse
import time
from datetime import datetime, timezone
import random
import shutil
import math
import re
# Import pip dependencies
import googleapiclient
import googleapiclient.discovery
import google_auth_oauthlib
import google_auth_oauthlib.flow
import requests
import yt_dlp
# Import submodules of pip packages not previously imported
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request



# Helper functions
def PrintWarning(message):
	print(f"\033[93mWarning: {message}\033[0m")
def PrintError(message):
	print(f"\033[91mERROR: {message}\033[0m")
def WriteFile(filePath, contents, binary=False):
    filePath = os.path.realpath(os.path.expanduser(filePath))
    os.makedirs(os.path.dirname(filePath), exist_ok=True)
    with open(filePath, "wb" if binary else "w", encoding=(None if binary else "UTF-8")) as file:
        file.write(contents)
def ReadFile(filePath, defaultContents=None, binary=False):
    filePath = os.path.realpath(os.path.expanduser(filePath))
    if not os.path.exists(filePath):
        if defaultContents != None:
            return defaultContents
    with open(filePath, "rb" if binary else "r", encoding=(None if binary else "UTF-8")) as file:
        return file.read()
def DictionaryHas(dictionary, path):
    if dictionary == None:
        return False
    keys = path.split(".")
    for key in keys:
        if not key in dictionary:
            return False
        if dictionary[key] == None:
            return False
        dictionary = dictionary[key]
    return True
def RandomSleep(minSeconds, maxSeconds):
    if minSeconds > maxSeconds:
        minSeconds, maxSeconds = maxSeconds, minSeconds
    duration = random.uniform(minSeconds, maxSeconds)
    time.sleep(duration)
def PathToClientUrl(filePath):
    filePath = os.path.realpath(filePath)
    databaseDir = os.path.realpath("database")
    clientDir = os.path.realpath("client")
    if not "..\\" in os.path.relpath(filePath, databaseDir):
        return "/database/" + os.path.relpath(filePath, databaseDir).replace("\\", "/")
    if not "..\\" in os.path.relpath(filePath, clientDir):
        return "/" + os.path.relpath(filePath, clientDir).replace("\\", "/")
    raise Exception(f"{filePath} is not within the client or database folders and therefore is innaccesable to the client.")
def DeserializeJson(jsonStr):
    return json.loads(jsonStr)
def SerializeJson(jsonObj, compact=False):
    return json.dumps(jsonObj, indent=(0 if compact else 4), ensure_ascii=False)
def VisibleLength(value):
    ansi_regex = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    printable_value = ansi_regex.sub("", value)
    return len(printable_value)  
def PrintGrid(values, padding=1):
    term_width = shutil.get_terminal_size().columns
    item_length = max([ VisibleLength(value) for value in values ]) + padding
    columns = math.floor(term_width / item_length)
    num_in_row = 0
    line_count = 0
    for i in range(len(values)):
        print(values[i], end="")
        num_in_row += 1
        if i < len(values) - 1 and num_in_row < columns:
            print(" " * (item_length - VisibleLength(values[i])), end="")
        else:
            print()
            line_count += 1
            num_in_row = 0
def RunCommand(command, echo=False, capture=False, input=None, check=True, env=None):
    if echo and capture:
        raise Exception("Command cannot be run with both echo and capture.")
    result = subprocess.run(command, stdout=(None if echo else subprocess.PIPE), stderr=(None if echo else subprocess.STDOUT), input=input, env=env, check=False, shell=True, text=True)
    if check and result.returncode != 0:
        print(result.stdout)
        raise Exception(f"Sub-process returned non-zero exit code.\nExitCode: {result.returncode}\nCmdLine: {command}")
    if capture and not check:
        return result.stdout.strip(), result.returncode
    elif capture:
        return result.stdout.strip()
    elif not check:
        return result.returncode
    else:
        return
os.chdir(os.path.dirname(os.path.realpath(__file__)))



def Module():
    print("Loading database...")
    songDatabase = DeserializeJson(ReadFile("./database/database.json"))

    i = 0
    for song in songDatabase:
        try:
            out_path = os.path.join("./database/songsplusmeta/", os.path.splitext(os.path.basename(song["src"]))[0] + ".m4a")
            i += 1
            if os.path.exists(out_path):
                continue
            else:
                c = f"ffmpeg -i \"{'.' + song['src']}\" -i \"{'.' + song['thumbnail']}\" -map 0:a -map 1:v -c:a aac -c:v copy -disposition:v attached_pic -metadata title=\"{song['title'].replace('\"', '\\\"')}\" -metadata artist=\"{song["artists"][0].replace('\"', '\\\"')}\" -metadata album=\"{song['album'].replace('\"', '\\\"')}\" \"{out_path}\""
                RunCommand(c)
                print(f"{i} of {len(songDatabase)}")
        except Exception as ex:
            PrintError(repr(ex))



def main():
    Module()
    print("All tasks completed successfully")
    sys.exit(0)
main()
