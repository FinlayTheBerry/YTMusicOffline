#!/usr/bin/env python3



# NOTE ON API COST:
# Total API cost is at maximum the following assuming only the Liked Music playlist is larger than 100 videos:
# ciel(NumOfPlaylists / 50) + ciel(NumOfVideos / 50) + (NumOfPlaylists * 2) + ciel(NumOfVideos / 50)
# That's about 322 querries for 79 playlists and 4005 videos.



# User Settings
# To get the latest user agent from your browser run the following in the developer console:
# console.log(navigator.userAgent);
UserAgent = "Mozilla/5.0 (X11; Linux x86_64; rv:159.0) Gecko/20100101 Firefox/159.0"
TraceMinDelay = 0.5
TraceMaxDelay = 1.0
ThumbnailDownloadMinDelay = 0.0
ThumbnailDownloadMaxDelay = 0.5
AudioStreamDownloadMinDelay = 0.0
AudioStreamDownloadMaxDelay = 5.0
SongDownloadRateLimit = 1_000_000
SegmentDownloadMinDelay = 0.0
SegmentDownloadMaxDelay = 5.0



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



def AuthApi():
    clientSecretsPath = os.path.realpath("./client_secrets.json")
    if not os.path.exists(clientSecretsPath):
        raise Exception("./client_secrets.json does not exist next to ytmusic-dl.py. See README.md for Google Cloud Platform setup.")

    credentials = None

    userSecretsPath = os.path.realpath("./user_secrets.json")
    if os.path.exists(userSecretsPath):
        credentials = Credentials.from_authorized_user_file(userSecretsPath, [ "https://www.googleapis.com/auth/youtube.readonly" ])
        if credentials.expired:
            credentials.refresh(Request())
        if not credentials.valid:
            credentials = None

    if credentials == None:
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(clientSecretsPath, [ "https://www.googleapis.com/auth/youtube.readonly" ])
        credentials = flow.run_local_server(port=0)

    WriteFile(userSecretsPath, credentials.to_json())

    return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)
def EnumMyPlaylists(youtubeApi, includeLikes=False, includeLikedMusic=False, includeWatchLater=False):
    output = []
    if includeLikes:
        output.append({ "id": "LL", "title": "Liked videos" })
    if includeLikedMusic:
        output.append({ "id": "LM", "title": "Liked Music" })
    if includeWatchLater:
        output.append({ "id": "WL", "title": "Watch later" })

    nextPageToken = None
    while True:
        request = youtubeApi.playlists().list(
            part="id,snippet",
            mine=True,
            maxResults=50,
            pageToken=nextPageToken
        )
        response = request.execute()
        for item in response['items']:
            output.append({ "id": item['id'], "title": item['snippet']['title'] } )
        if DictionaryHas(response, "nextPageToken"):
            nextPageToken = response['nextPageToken']
        else:
            break
    return output
def SelectPlaylists(allPlaylists, playlistSelection):
    for i in range(len(allPlaylists)):
        if not allPlaylists[i]['id'] in playlistSelection['state']:
            playlistSelection['state'][allPlaylists[i]['id']] = playlistSelection['default']
    
    while True:
        playlistsFormatted = []
        for i in range(len(allPlaylists)):
            if playlistSelection['state'][allPlaylists[i]['id']]:
                playlistsFormatted.append(f"\033[32m{i}) {allPlaylists[i]['title']}\033[0m")
            else:
                playlistsFormatted.append(f"{i}) {allPlaylists[i]['title']}")
        PrintGrid(playlistsFormatted, padding=1)

        choice = input("playlist number = toggle, all = select all, none = select none, done = download selected: ")
        
        if choice == "done":
            playlistSelection['selected'] = []
            for i in range(len(allPlaylists)):
                if playlistSelection['state'][allPlaylists[i]['id']]:
                    playlistSelection['selected'].append(allPlaylists[i]['id'])
            return
        elif choice == "all":
            for i in range(len(allPlaylists)):
                playlistSelection['state'][allPlaylists[i]['id']] = True
            playlistSelection['default'] = True
        elif choice == "none":
            for i in range(len(allPlaylists)):
                playlistSelection['state'][allPlaylists[i]['id']] = False
            playlistSelection['default'] = False
        else:
            try:
                playlistSelection['state'][allPlaylists[int(choice)]['id']] = not playlistSelection['state'][allPlaylists[int(choice)]['id']]
            except:
                print("Invalid choice")
def EnumPlaylistContents(youtubeApi, playlistId):
    output = []
    request = youtubeApi.playlistItems().list(
        part="snippet", # Snippet used instead of id because id returns the playlistItemId not the videoId
        playlistId=playlistId,
        maxResults=50
    )
    response = request.execute()
    for item in response['items']:
        output.append(item['snippet']['resourceId']['videoId'])
    if DictionaryHas(response, "nextPageToken"):
        nextPageToken = response['nextPageToken']
    else:
        nextPageToken = None

    while nextPageToken != None:
        request = youtubeApi.playlistItems().list(
            part="snippet",
            playlistId=playlistId,
            maxResults=50,
            pageToken=nextPageToken
        )
        response = request.execute()
        for item in response['items']:
            output.append(item['snippet']['resourceId']['videoId'])
        if DictionaryHas(response, "nextPageToken"):
            nextPageToken = response['nextPageToken']
        else:
            nextPageToken = None
    return output
def EnumPlaylistsContents(youtubeApi, playlistIds):
    videoIds = []
    progress = 0
    for playlistId in playlistIds:
        for videoId in EnumPlaylistContents(youtubeApi, playlistId):
            if not videoId in videoIds:
                videoIds.append(videoId)
        progress += 1
        print(f"Progress: {progress} of {len(playlistIds)}...")
    return videoIds
def GetVideoInfo(youtubeApi, infoNeededVideoIds, videoInfoDB):
    progress = 0
    while progress < len(infoNeededVideoIds):
        nextVideoIds = infoNeededVideoIds[progress:progress + 50]
        request = youtubeApi.videos().list(
            part="contentDetails,id,liveStreamingDetails,localizations,paidProductPlacementDetails,player,recordingDetails,snippet,statistics,status,topicDetails",
            id=",".join(nextVideoIds),
            maxResults=50
        )
        response = request.execute()
        for video in response['items']:
            videoId = video['id']
            videoInfoDB[videoId] = video
            nextVideoIds.remove(videoId)
        for videoId in nextVideoIds:
            PrintWarning(f"Unable to get video info for video Id {videoId} (it's a ghost).")
            videoInfoDB[videoId] = None
        progress += 50
        if progress > len(infoNeededVideoIds):
            progress = len(infoNeededVideoIds)
        print(f"Progress: {progress} of {len(infoNeededVideoIds)}...")
def IsVideoUnavailable(videoInfo):
    if DictionaryHas(videoInfo, "status.privacyStatus"):
        privacyStatus = videoInfo['status']['privacyStatus']
        if privacyStatus != "public" and privacyStatus != "unlisted":
            return True
    if DictionaryHas(videoInfo, "contentDetails.regionRestriction.allowed"):
        allowedCountries = videoInfo['contentDetails']['regionRestriction']['allowed']
        if allowedCountries != None and not "US" in allowedCountries:
            return True
    if DictionaryHas(videoInfo, "contentDetails.regionRestriction.blocked"):
        blockedCountries = videoInfo['contentDetails']['regionRestriction']['blocked']
        if blockedCountries != None and "US" in blockedCountries:
            return True
    return False
def TraceVideo(videoId):
    musicUrl = f"https://music.youtube.com/watch?v={videoId}"
    marker = "ytcfg.set("
    headers = { "User-Agent": UserAgent }
    response = requests.get(musicUrl, headers=headers)
    response.raise_for_status()
    response_text = response.text
    startIndex = 0
    markerIndex = response_text.find(marker, startIndex)
    startIndex = markerIndex + len(marker)
    while markerIndex != -1:
        parenthesisDepth = 1
        ytcfgJson = None
        for i in range(markerIndex + len(marker), len(response_text)):
            if response_text[i] == "(":
                parenthesisDepth += 1
            elif response_text[i] == ")":
                parenthesisDepth -= 1
            if parenthesisDepth == 0:
                ytcfgJson = response_text[markerIndex + len(marker):i]
                startIndex = i + 1
                break
        if ytcfgJson == None:
            continue
        ytcfg = json.loads(ytcfgJson)
        if not DictionaryHas(ytcfg, "INITIAL_ENDPOINT"):
            continue
        initialEndpoint = json.loads(ytcfg['INITIAL_ENDPOINT'])
        if not DictionaryHas(initialEndpoint, "watchEndpoint.videoId"):
            continue
        tracedVideoId = initialEndpoint['watchEndpoint']['videoId']
        if tracedVideoId == videoId:
            return None
        return tracedVideoId
    return None
def TraceUnavailableVideos(traceNeededVideoIds, relocationDB):
    progress = 0
    for videoId in traceNeededVideoIds:
        if progress != 0:
            RandomSleep(TraceMinDelay, TraceMaxDelay)
        tracedVideoId = TraceVideo(videoId)
        if tracedVideoId == None:
            PrintWarning(f"Unable to trace unavailable video with video Id {videoId}.")
            relocationDB[videoId] = None
        else:
            relocationDB[videoId] = tracedVideoId
        progress += 1
        print(f"Progress: {progress} of {len(traceNeededVideoIds)}...")
def GetBestThumbnailUrl(videoInfo):
    bestThumbnailSize = 0
    bestThumbnailUrl = None
    for thumbnail in videoInfo['snippet']['thumbnails'].values():
        if thumbnail == None:
            continue
        if thumbnail['width'] * thumbnail['height'] > bestThumbnailSize:
            bestThumbnailSize = thumbnail['width'] * thumbnail['height']
            bestThumbnailUrl = thumbnail['url']
    return bestThumbnailUrl
def ConvertVideoToSong(videoId, videoInfo):
    srcUrl = f"https://www.youtube.com/watch?v={videoId}"
    og_src = None
    src = None
    thumbnailUrl = GetBestThumbnailUrl(videoInfo)
    thumbnail = None
    title = None
    album = None
    artists = None
    releaseDate = None
    songId = "yt." + videoId

    description = videoInfo['snippet']['description']
    descriptionLines = [line.strip() for line in description.replace("\r\n", "\n").split("\n") if len(line) > 0]
    if len(descriptionLines) > 0 and descriptionLines[-1] == "Auto-generated by YouTube.":
        if descriptionLines[0].startswith("Provided to YouTube by "):
            descriptionLines = descriptionLines[1:]
        if len(descriptionLines) >= 1:
            titleArtistsSplit = descriptionLines[0].split(" · ")
            if len(titleArtistsSplit) >= 2:
                title = titleArtistsSplit[0]
                artists = titleArtistsSplit[1:]
        if len(descriptionLines) >= 2:
            album = descriptionLines[1]
        for line in descriptionLines[2:]:
            if line.startswith("Released on: "):
                line = line[len("Released on: "):]
                releaseDate = int(datetime.strptime(line, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
                break

    if title == None:
        title = videoInfo['snippet']['title']
    if album == None:
        album = ""
    if artists == None:
        artistRaw = videoInfo['snippet']['channelTitle']
        artists = [ artistRaw[0:-len(" - Topic")] if artistRaw.endswith(" - Topic") else artistRaw ]
    if releaseDate == None:
        rawReleaseDate = videoInfo['snippet']['publishedAt']
        releaseDate = int(datetime.strptime(rawReleaseDate, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())

    return { "srcUrl": srcUrl, "og_src": og_src, "src": src, "thumbnailUrl": thumbnailUrl, "thumbnail": thumbnail, "title": title, "album": album, "artists": artists, "releaseDate": releaseDate, "songId": songId }
def AddNewVideosToSongDatabase(videoInfoDB, relocationDB, songDatabase):
    ytVideoIdsAlreadyConverted = set()
    for song in songDatabase:
        if song['songId'].startswith("yt."):
            ytVideoIdsAlreadyConverted.add(song['songId'][3:])

    # New songs must be added in reverse order.
    for ytVideoId in videoInfoDB:
        if ytVideoId not in ytVideoIdsAlreadyConverted and ytVideoId not in relocationDB and videoInfoDB[ytVideoId] is not None:
            songDatabase.insert(0, ConvertVideoToSong(ytVideoId, videoInfoDB[ytVideoId]))
def DownloadThumbnail(song, tempDir, thumbnailsDir):
    thumbnailUrl = song['thumbnailUrl']
    thumbnailUrlPath = urllib.parse.urlparse(thumbnailUrl).path
    thumbnailFileExt = os.path.splitext(os.path.basename(thumbnailUrlPath))[1]
    thumbnailTempPath = os.path.join(tempDir, song['songId'] + ".thumb.temp" + thumbnailFileExt)
    thumbnailFilePath = os.path.join(thumbnailsDir, song['songId'] + thumbnailFileExt)
    request = urllib.request.Request(thumbnailUrl)
    try:
        with urllib.request.urlopen(request) as responseStream:
            with open(thumbnailTempPath, "wb") as thumbnailFile:
                thumbnailFile.write(responseStream.read())
    except urllib.error.HTTPError as ex:
        if ex.code == 404:
            PrintError(f"404 Failed to download thumbnail: {thumbnailUrl}")
            return
        else:
            raise
    os.rename(thumbnailTempPath, thumbnailFilePath)
    song['thumbnail'] = PathToClientUrl(thumbnailFilePath)
def DownloadOgAudioStream(song, tempDir, ogAudioStreamsDir):
    NeverUseCookies = False
    AlwaysUseCookies = False

    streamPathNoExt = os.path.join(ogAudioStreamsDir, f"{song['songId']}")
    streamTempPathNoExt = os.path.join(tempDir, f"{song['songId']}.stream.temp")

    ytdlpOptions = {
        "format": "bestaudio",
        "outtmpl": os.path.join(tempDir, f"{streamTempPathNoExt}.%(ext)s"),
        "nooverwrites": True,
        "force_overwrites": False,
        "continuedl": False,
        "abort_on_error": True,
        "ignoreerrors": False,
        "abort_on_unavailable_fragments": True,
        "noplaylist": True,
        "retries": 0,
        "fragment_retries": 0,
        "skip_unavailable_fragments": False,
        "sleep_interval": SegmentDownloadMinDelay,
        "max_sleep_interval": SegmentDownloadMaxDelay,
        "ratelimit": SongDownloadRateLimit,
        "remote_components": [ "ejs:github" ],
    }
    targetUrls = [ song['srcUrl'] ]
    
    retryWithCookies = False
    if AlwaysUseCookies:
        retryWithCookies = True
    else:
        with yt_dlp.YoutubeDL(ytdlpOptions) as ytdlp:
            try:
                ytdlp.download(targetUrls)
            except Exception as ex:
                PrintError(repr(ex))
                if NeverUseCookies:
                    return
                else:
                    PrintWarning(f"Downloading {song['srcUrl']} failed. Retrying with cookies.")
                    retryWithCookies = True

    if retryWithCookies:
        ytdlpOptions['cookiesfrombrowser'] = ("firefox",)
        with yt_dlp.YoutubeDL(ytdlpOptions) as ytdlp:
            try:
                ytdlp.download(targetUrls)
            except Exception as ex:
                PrintError(repr(ex))
                PrintError(f"FATAL Could not download video {song['srcUrl']}")
                return

    tempFiles = [ os.path.join(tempDir, tempFileName) for tempFileName in os.listdir(tempDir) ]
    streamTempPath = None
    for tempFile in tempFiles:
        if os.path.splitext(tempFile)[0] == os.path.join(tempDir, f"{song['songId']}.stream.temp"):
            if streamTempPath == None:
                streamTempPath = tempFile
            else:
                raise Exception("Multiple matching temp files found.")
    if streamTempPath == None:
        raise Exception("No matching temp file found.")
    streamPath = streamPathNoExt + os.path.splitext(tempFile)[1]
    os.rename(streamTempPath, streamPath)
    song['og_src'] = PathToClientUrl(streamPath)
def ConvertAudioStream(song, tempDir, ogAudioStreamsDir, audioStreamsDir):
    ogStreamPath = os.path.join(ogAudioStreamsDir, os.path.basename(song['og_src']))
    streamTempPath = os.path.join(tempDir, song['songId'] + ".convert.temp.m4a")
    streamPath = os.path.join(audioStreamsDir, song['songId'] + ".m4a")
    if not os.path.exists(ogStreamPath):
        PrintError(f"FATAL OG stream does not exist at {ogStreamPath}")
        return
    RunCommand(f"ffmpeg -i \"{ogStreamPath}\" -c:a aac -ac 2 -y -nostdin \"{streamTempPath}\"", echo=True)
    os.rename(streamTempPath, streamPath)
    song['src'] = PathToClientUrl(streamPath)

def Main():
    if not os.path.exists("./database"):
        os.mkdir("./database")
    defaultSongDatabase = []
    songDatabase = DeserializeJson(ReadFile("./database/database.json", defaultContents=SerializeJson(defaultSongDatabase, compact=True)))

    if True: # Add new songs to database from YouTube API or leave untouched
        youtubeApi = AuthApi()

        defaultPlaylistSelection = { "state": {}, "default": True, "selected": [] }
        playlistSelection = DeserializeJson(ReadFile("./playlist_selection.json", defaultContents=SerializeJson(defaultPlaylistSelection, compact=True)))
        if True: # Get latest playlists and customize selection or use previous list
            SelectPlaylists(EnumMyPlaylists(youtubeApi, False, True, False), playlistSelection)
            WriteFile("./playlist_selection.json", SerializeJson(playlistSelection, compact=True))

        defaultRequestedVideos = []
        requestedVideos = DeserializeJson(ReadFile("./requested_videos.json", defaultContents=SerializeJson(defaultRequestedVideos, compact=True)))
        if True: # Fetch playlist contents or use previous list of needed videos
            print("Fetching playlist contents...")
            requestedVideos = list(set(requestedVideos + EnumPlaylistsContents(youtubeApi, playlistSelection['selected'])))
            WriteFile("./requested_videos.json", SerializeJson(requestedVideos, compact=True))

        defaultVideoInfoDB = {}
        videoInfoDB = DeserializeJson(ReadFile("./video_info_db.json", defaultContents=SerializeJson(defaultVideoInfoDB, compact=True)))
        defaultRelocationDB = {}
        relocationDB = DeserializeJson(ReadFile("./relocation_db.json", defaultContents=SerializeJson(defaultRelocationDB, compact=True)))
        while True: # Get video info and trace relocations
            didSomething = False

            # Filter out video Ids which already have info
            infoNeededVideoIds = [ videoId for videoId in requestedVideos if videoId not in videoInfoDB ]
            infoNeededVideoIds.extend([ videoId for videoId in relocationDB.values() if videoId is not None and videoId not in videoInfoDB and videoId not in infoNeededVideoIds ])

            # Fetch video info for needed video Ids
            print("Fetching video info for all videos currently without info...")
            if len(infoNeededVideoIds) > 0:
                GetVideoInfo(youtubeApi, infoNeededVideoIds, videoInfoDB)
                WriteFile("./video_info_db.json", SerializeJson(videoInfoDB, compact=True))
                didSomething = True

            # Build list of videos which need to be traced
            traceNeededVideoIds = [ videoId for videoId in list(videoInfoDB.keys()) if IsVideoUnavailable(videoInfoDB[videoId]) and videoId not in relocationDB ]

            # Trace unavailible video Ids
            print("Tracing unavailable videos to see if they were redirected...")
            if len(traceNeededVideoIds) > 0:
                TraceUnavailableVideos(traceNeededVideoIds, relocationDB)
                WriteFile("./relocation_db.json", SerializeJson(relocationDB, compact=True))
                didSomething = True

            # If we didn't do anything this round then exit loop
            if not didSomething:
                break

        print("Extracting song info from video info...")
        AddNewVideosToSongDatabase(videoInfoDB, relocationDB, songDatabase)
        WriteFile("./database/database.json", SerializeJson(songDatabase, compact=True))

    if True: # Download thumbnails for songs without one
        print("Downloading thumbnails for songs without a thumbnail...")
        thumbnailsDir = os.path.realpath("database/thumbnails")
        os.makedirs(thumbnailsDir, exist_ok=True)
        tempDir = os.path.realpath("database/temp")
        os.makedirs(tempDir, exist_ok=True)

        existingFiles = set()
        for fileName in os.listdir(thumbnailsDir):
            filePath = os.path.join(thumbnailsDir, fileName)
            existingFiles.add(PathToClientUrl(filePath))

        songsInNeedOfThumbnails = []
        for song in songDatabase:
            if song['thumbnail'] == None:
                songsInNeedOfThumbnails.append(song)
            elif not song['thumbnail'] in existingFiles:
                PrintWarning(f"Thumbnail for song {song['songId']} is said to be at {song['thumbnail']} but has been deleted.")
            else:
                existingFiles.remove(song['thumbnail'])

        for filePath in existingFiles:
            PrintWarning(f"Thumbnail exists at {filePath} but is claimed by no song.")

        progress = 0
        for song in songsInNeedOfThumbnails:
            DownloadThumbnail(song, tempDir, thumbnailsDir)
            WriteFile("./database/database.json", SerializeJson(songDatabase, compact=True))
            progress += 1
            print(f"Progress: {progress} of {len(songsInNeedOfThumbnails)}...")
            RandomSleep(ThumbnailDownloadMinDelay, ThumbnailDownloadMaxDelay)

        os.rmdir(tempDir)

    if True: # Download original audio streams for songs without one
        print("Downloading audio stream for songs without an audio stream...")
        ogAudioStreamsDir = os.path.realpath("database/og_songs")
        os.makedirs(ogAudioStreamsDir, exist_ok=True)
        tempDir = os.path.realpath("database/temp")
        os.makedirs(tempDir, exist_ok=True)

        existingFiles = set()
        for fileName in os.listdir(ogAudioStreamsDir):
            filePath = os.path.join(ogAudioStreamsDir, fileName)
            existingFiles.add(PathToClientUrl(filePath))

        songsInNeedOfOgAudioStreams = []
        for song in songDatabase:
            if song['og_src'] == None:
                songsInNeedOfOgAudioStreams.append(song)
            elif not song['og_src'] in existingFiles:
                PrintWarning(f"OG audio stream for song {song['songId']} is said to be at {song['og_src']} but has been deleted.")
                songsInNeedOfOgAudioStreams.append(song)
            else:
                existingFiles.remove(song['og_src'])

        for filePath in existingFiles:
            PrintWarning(f"OG audio stream exists at {filePath} but is claimed by no song.")

        progress = 0
        for song in songsInNeedOfOgAudioStreams:
            DownloadOgAudioStream(song, tempDir, ogAudioStreamsDir)
            WriteFile("./database/database.json", SerializeJson(songDatabase, compact=True))
            progress += 1
            print(f"Progress: {progress} of {len(songsInNeedOfOgAudioStreams)}...")
            RandomSleep(AudioStreamDownloadMinDelay, AudioStreamDownloadMaxDelay)

        os.rmdir(tempDir)

    if True: # Convert original audio streams to universal codec
        print("Encoding audio streams into univerisal codec...")
        ogAudioStreamsDir = os.path.realpath("database/og_songs")
        os.makedirs(ogAudioStreamsDir, exist_ok=True)
        audioStreamsDir = os.path.realpath("database/songs")
        os.makedirs(audioStreamsDir, exist_ok=True)
        tempDir = os.path.realpath("database/temp")
        os.makedirs(tempDir, exist_ok=True)

        existingFiles = set()
        for fileName in os.listdir(audioStreamsDir):
            filePath = os.path.join(audioStreamsDir, fileName)
            existingFiles.add(PathToClientUrl(filePath))

        songsInNeedOfAudioStreams = []
        for song in songDatabase:
            if song['src'] == None:
                songsInNeedOfAudioStreams.append(song)
            elif not song['src'] in existingFiles:
                PrintWarning(f"Audio stream for song {song['songId']} is said to be at {song['src']} but has been deleted.")
                songsInNeedOfAudioStreams.append(song)
            else:
                existingFiles.remove(song['src'])

        for filePath in existingFiles:
            PrintWarning(f"Audio stream exists at {filePath} but is claimed by no song.")

        progress = 0
        for song in songsInNeedOfAudioStreams:
            ConvertAudioStream(song, tempDir, ogAudioStreamsDir, audioStreamsDir)
            WriteFile("./database/database.json", SerializeJson(songDatabase, compact=True))
            progress += 1
            print(f"Progress: {progress} of {len(songsInNeedOfAudioStreams)}...")

        os.rmdir(tempDir)

    print("All tasks completed successfully")
    sys.exit(0)
Main()
