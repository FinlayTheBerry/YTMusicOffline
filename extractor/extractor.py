#!/bin/python3

# User Settings
# To update user agent run the following in the chrome developer console
# console.log(navigator.userAgent);
UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
TraceMinDelay = 0
TraceMaxDelay = 1
ThumbnailDownloadMinDelay = 0
ThumbnailDownloadMaxDelay = 1
AudioStreamDownloadMinDelay = 0
AudioStreamDownloadMaxDelay = 5
SongDownloadRateLimit = 1_000_000
SegmentDownloadMinDelay = 0
SegmentDownloadMaxDelay = 5



# NOTE ON API COST:
# Total API cost is at maximum the following assuming only the Liked Music playlist is larger than 100 videos:
# ciel(NumOfPlaylists / 50) + ciel(NumOfVideos / 50) + (NumOfPlaylists * 2) + ciel(NumOfVideos / 50)
# That's about 322 querries for 79 playlists and 4005 videos.



# Import builtins (part of python)
import json
import sys
import os
import subprocess
import urllib.request
import urllib.parse
import time
from datetime import datetime, timezone
import random
import importlib
# Import pip dependencies
def PromptPipInstall(importName, pipName):
    pipCommand = f"python -m pip install -U {pipName}"
    print(f"ERROR: Dependency {pipName} not found. Would you like to install it now? (y/n)")
    choice = input().lower()
    if choice in [ "y", "yes" ]:
        print()
        print(f"> {pipCommand}")
        errorCode = subprocess.run(pipCommand, shell=True, env=os.environ.copy()).returncode
        print()
        if errorCode != 0:
           print(f"ERROR: {pipCommand} failed with error code {errorCode}.")
           sys.exit(1)
        globals()[importName] = importlib.import_module(importName)
    else:
        print(f"Execution cannot continue without required dependency {pipName}.")
        sys.exit(1)
try:
    import googleapiclient
except ImportError:
    PromptPipInstall("googleapiclient", "google-api-python-client")
try:
    import google_auth_oauthlib
except ImportError:
    PromptPipInstall("google_auth_oauthlib", "google-auth-oauthlib")
try:
    import google_auth_httplib2
except ImportError:
    PromptPipInstall("google_auth_httplib2", "google-auth-httplib2")
try:
    import yt_dlp
except ImportError:
    PromptPipInstall("yt_dlp", "yt-dlp")
# Import submodules of pip packages not previously imported
import google_auth_oauthlib.flow
import googleapiclient.discovery
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request



# Helper functions
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
def ChangeDir():
    extractorDir = os.path.dirname(os.path.abspath(sys.argv[0]))
    ytMusicOfflineDir = os.path.dirname(extractorDir)
    os.chdir(ytMusicOfflineDir)
def PathToClientUrl(filePath):
    ChangeDir()
    filePath = os.path.abspath(filePath)
    databaseDir = os.path.abspath("database")
    clientDir = os.path.abspath("client")
    if not "..\\" in os.path.relpath(filePath, databaseDir):
        return "/database/" + os.path.relpath(filePath, databaseDir).replace("\\", "/")
    if not "..\\" in os.path.relpath(filePath, clientDir):
        return "/" + os.path.relpath(filePath, clientDir).replace("\\", "/")
    raise Exception(f"{filePath} is not within the client or database folders and therefore is innaccesable to the client.")
def LoadSongDatabase():
    ChangeDir()
    databaseDir = os.path.abspath("database")
    os.makedirs(databaseDir, exist_ok=True)
    databasePath = os.path.abspath("database/database.json")
    databaseBackupPath = os.path.join(databaseDir, "database_backup.json")
    if os.path.exists(databaseBackupPath):
        raise Exception("A previous failed save exists of the database. Bailing out for manual audit.")
    if not os.path.exists(databasePath):
        return {}
    with open(databasePath, "r", encoding="utf-8") as databaseFile:
        return json.load(databaseFile)
def SaveSongDatabase(songDatabase):
    ChangeDir()
    databaseDir = os.path.abspath("database")
    os.makedirs(databaseDir, exist_ok=True)
    databasePath = os.path.abspath("database/database.json")
    databaseBackupPath = os.path.join(databaseDir, "database_backup.json")
    if os.path.exists(databaseBackupPath):
        raise Exception("A previous failed save exists of the database. Bailing out for manual audit.")
    if os.path.exists(databasePath):
        os.rename(databasePath, databaseBackupPath)
    with open(databasePath, "w", encoding="utf-8") as databaseFile:
        json.dump(songDatabase, databaseFile, indent=4, ensure_ascii=True)
    if os.path.exists(databaseBackupPath):
        os.remove(databaseBackupPath)



# Module 1 - Add New Songs To The Database - APPROVED
# This module is complex and documentation will come later.
def AuthApi():
    ChangeDir()
    userSecretsPath = os.path.abspath("extractor/user_secrets.json")
    clientSecretsPath = os.path.abspath("extractor/client_secrets.json")
    credentials = None

    if os.path.exists(userSecretsPath):
        credentials = Credentials.from_authorized_user_file(userSecretsPath, [ "https://www.googleapis.com/auth/youtube.readonly" ])
        if credentials.expired:
            credentials.refresh(Request())
        if not credentials.valid:
            credentials = None

    if credentials == None:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(clientSecretsPath, [ "https://www.googleapis.com/auth/youtube.readonly" ])
        credentials = flow.run_local_server(port=0)

    with open(userSecretsPath, "w") as userSecretsFile: userSecretsFile.write(credentials.to_json())

    return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)
def EnumMyPlaylists(youtubeApi, includeLikes=False, includeLikedMusic=False):
    output = []
    if includeLikes:
        output.append("LL")
    if includeLikedMusic:
        output.append("LM")

    request = youtubeApi.playlists().list(
        part="id",
        mine=True,
        maxResults=50
    )
    response = request.execute()
    for item in response["items"]:
        output.append(item["id"])
    if DictionaryHas(response, "nextPageToken"):
        nextPageToken = response["nextPageToken"]
    else:
        nextPageToken = None

    while nextPageToken != None:
        request = youtubeApi.playlists().list(
            part="id",
            mine=True,
            maxResults=50,
            pageToken=nextPageToken
        )
        response = request.execute()
        for item in response["items"]:
            output.append(item["id"])
        if DictionaryHas(response, "nextPageToken"):
            nextPageToken = response["nextPageToken"]
        else:
            nextPageToken = None
    return output
def EnumPlaylistContents(youtubeApi, playlistId):
    output = []
    request = youtubeApi.playlistItems().list(
        part="snippet", # Snippet used instead of id because id returns the playlistItemId not the videoId
        playlistId=playlistId,
        maxResults=50
    )
    response = request.execute()
    for item in response["items"]:
        output.append(item["snippet"]["resourceId"]["videoId"])
    if DictionaryHas(response, "nextPageToken"):
        nextPageToken = response["nextPageToken"]
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
        for item in response["items"]:
            output.append(item["snippet"]["resourceId"]["videoId"])
        if DictionaryHas(response, "nextPageToken"):
            nextPageToken = response["nextPageToken"]
        else:
            nextPageToken = None
    return output
def EnumMyVideos(youtubeApi):
    myPlaylistIds = EnumMyPlaylists(youtubeApi, includeLikedMusic=True)

    myVideoIds = []
    i = 0
    for myPlaylistId in myPlaylistIds:
        print(f"Progress {i} of {len(myPlaylistIds)}...")
        i += 1
        for myVideoId in EnumPlaylistContents(youtubeApi, myPlaylistId):
            if not myVideoId in myVideoIds:
                myVideoIds.append(myVideoId)
    return myVideoIds
def GetVideoInfo(youtubeApi, videoIds):
    output = {}
    i = 0
    while i < len(videoIds):
        nextVideoIds = videoIds[i:i + 50]
        print(f"Progress {i} of {len(videoIds)}...")
        i += len(nextVideoIds)
        request = youtubeApi.videos().list(
            part="contentDetails,id,liveStreamingDetails,localizations,paidProductPlacementDetails,player,recordingDetails,snippet,statistics,status,topicDetails",
            id=",".join(nextVideoIds),
            maxResults=50
        )
        response = request.execute()
        for video in response["items"]:
            videoId = video["id"]
            output[videoId] = video
            nextVideoIds.remove(videoId)
        for videoId in nextVideoIds:
            print(f"Warning: Unable to get video info for video Id {videoId}.")
    return output
def IsVideoUnavailable(video):
    if DictionaryHas(video, "status.privacyStatus"):
        privacyStatus = video["status"]["privacyStatus"]
        if privacyStatus != "public" and privacyStatus != "unlisted":
            return True
    if DictionaryHas(video, "contentDetails.regionRestriction.allowed"):
        allowedCountries = video["contentDetails"]["regionRestriction"]["allowed"]
        if allowedCountries != None and not "US" in allowedCountries:
            return True
    if DictionaryHas(video, "contentDetails.regionRestriction.blocked"):
        blockedCountries = video["contentDetails"]["regionRestriction"]["blocked"]
        if blockedCountries != None and "US" in blockedCountries:
            return True
    return False
def TraceVideo(videoId):
    musicUrl = f"https://music.youtube.com/watch?v={videoId}"
    marker = "ytcfg.set("
    request = urllib.request.Request(musicUrl, headers={ "User-Agent": UserAgent })
    with urllib.request.urlopen(request) as responseFile: response = responseFile.read().decode("utf-8")
    startIndex = 0
    markerIndex = response.find(marker, startIndex)
    startIndex = markerIndex + len(marker)
    while markerIndex != -1:
        parenthesisDepth = 1
        ytcfgJson = None
        for i in range(markerIndex + len(marker), len(response)):
            if response[i] == "(":
                parenthesisDepth += 1
            elif response[i] == ")":
                parenthesisDepth -= 1
            if parenthesisDepth == 0:
                ytcfgJson = response[markerIndex + len(marker):i]
                startIndex = i + 1
                break
        if ytcfgJson == None:
            continue
        ytcfg = json.loads(ytcfgJson)
        if not DictionaryHas(ytcfg, "INITIAL_ENDPOINT"):
            continue
        initialEndpoint = json.loads(ytcfg["INITIAL_ENDPOINT"])
        if not DictionaryHas(initialEndpoint, "watchEndpoint.videoId"):
            continue
        tracedVideoId = initialEndpoint["watchEndpoint"]["videoId"]
        if tracedVideoId == videoId:
            return None
        return tracedVideoId
    return None
def TraceAndRemoveUnavailableVideos(videoInfoDatabase):
    traceNeededVideoIds = set()
    for videoId in list(videoInfoDatabase.keys()):
        if IsVideoUnavailable(videoInfoDatabase[videoId]):
            traceNeededVideoIds.add(videoId)
            del videoInfoDatabase[videoId]

    output = []
    i = 0
    for videoId in traceNeededVideoIds:
        print(f"Progress {i} of {len(traceNeededVideoIds)}...")
        i += 1
        tracedVideoId = TraceVideo(videoId)
        if (tracedVideoId != None
            and not tracedVideoId in videoInfoDatabase
            and not tracedVideoId in traceNeededVideoIds):
            output.append(tracedVideoId)
        RandomSleep(TraceMinDelay, TraceMaxDelay)
    return output
def GetBestThumbnail(video):
    bestThumbnailSize = 0
    bestThumbnailUrl = None
    for thumbnail in video["snippet"]["thumbnails"].values():
        if thumbnail == None:
            continue
        if thumbnail["width"] * thumbnail["height"] > bestThumbnailSize:
            bestThumbnailSize = thumbnail["width"] * thumbnail["height"]
            bestThumbnailUrl = thumbnail["url"]
    return bestThumbnailUrl
def ConvertVideoToSong(videoId, videoInfo):
    srcUrl = f"https://www.youtube.com/watch?v={videoId}"
    src = None
    thumbnailUrl = GetBestThumbnail(videoInfo)
    thumbnail = None
    title = None
    album = None
    artists = None
    releaseDate = None

    description = videoInfo["snippet"]["description"]
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
        title = videoInfo["snippet"]["title"]
    if album == None:
        album = ""
    if artists == None:
        artistRaw = videoInfo["snippet"]["channelTitle"]
        artists = [ artistRaw[0:-len(" - Topic")] if artistRaw.endswith(" - Topic") else artistRaw ]
    if releaseDate == None:
        rawReleaseDate = videoInfo["snippet"]["publishedAt"]
        releaseDate = int(datetime.strptime(rawReleaseDate, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())

    return { "srcUrl": srcUrl, "src": src, "thumbnailUrl": thumbnailUrl, "thumbnail": thumbnail, "title": title, "album": album, "artists": artists, "releaseDate": releaseDate }
def AddNewVideosToSongDatabase(videoInfoDatabase, songDatabase):
    for songId in songDatabase:
        if not songId in videoInfoDatabase:
            print(f"Warning: Song exists in song database with Id {songId} but that song isn't in your likes or any playlist.")
    
    # New songs must be added in reverse order so that when the database is reversed it goes back to normal.
    for videoId in reversed(list(videoInfoDatabase.keys())):
        if not videoId in songDatabase:
            songDatabase[videoId] = ConvertVideoToSong(videoId, videoInfoDatabase[videoId])
def Module1():
    print("Authenticating with YouTube Api...")
    youtubeApi = AuthApi()

    print("Fetching playlists including music likes...")
    infoNeededVideoIds = EnumMyVideos(youtubeApi)

    videoInfoDatabase = {}
    while len(infoNeededVideoIds) > 0:
        print("Fetching video info for all videos currently without info...")
        videoInfoDatabase.update(GetVideoInfo(youtubeApi, infoNeededVideoIds))

        print("Tracing unavailable videos to see if they were redirected...")
        infoNeededVideoIds = TraceAndRemoveUnavailableVideos(videoInfoDatabase)

    print("Loading database...")
    songDatabase = LoadSongDatabase()

    # Database must be reversed before calls to AddNewVideosToSongDatabase.
    # This makes insertions to the end go to the beginning of the database.
    print("Extracting song info from video info...")
    songDatabase = dict(reversed(list(songDatabase.items())))
    AddNewVideosToSongDatabase(videoInfoDatabase, songDatabase)
    songDatabase = dict(reversed(list(songDatabase.items())))

    print("Saving database...")
    SaveSongDatabase(songDatabase)



# Module 2 - Download Each Song's Thumbnail - APPROVED
# Downloads the thumbnail for any song in the Database which does not already have a thumbnail in database/thumbnails.
# Regardless of weather a thumbnail is needed it updates song.thumbnail to reflect the client url of the thumbnail.
# Does not depend on previous steps and runs independently.
def DownloadThumbnail(songId, song, thumbnailsDir):
    thumbnailUrl = song["thumbnailUrl"]
    thumbnailUrlPath = urllib.parse.urlparse(thumbnailUrl).path
    thumbnailFileExt = os.path.splitext(os.path.basename(thumbnailUrlPath))[1]
    thumbnailFilePath = os.path.join(thumbnailsDir, songId + thumbnailFileExt)
    request = urllib.request.Request(thumbnailUrl, headers={ "User-Agent": UserAgent })
    with urllib.request.urlopen(request) as responseFile: response = responseFile.read()
    with open(thumbnailFilePath, "wb") as thumbnailFile: thumbnailFile.write(response)
    song["thumbnail"] = PathToClientUrl(thumbnailFilePath)
def Module2():
    print("Loading database...")
    songDatabase = LoadSongDatabase()

    print("Downloading thumbnails for songs without a thumbnail...")
    ChangeDir()
    thumbnailsDir = os.path.abspath("database/thumbnails")
    os.makedirs(thumbnailsDir, exist_ok=True)

    existingFiles = {}
    for fileName in os.listdir(thumbnailsDir):
        filePath = os.path.join(thumbnailsDir, fileName)
        songId = os.path.splitext(fileName)[0]
        if not songId in songDatabase:
            print(f"Warning: Thumbnail exists for song {songId} at {filePath} but that song isn't in the database.")
        existingFiles[songId] = filePath

    thumbnailNeededSongIds = set()
    for songId in songDatabase:
        if songId in existingFiles:
            songDatabase[songId]["thumbnail"] = PathToClientUrl(existingFiles[songId])
            continue
        thumbnailNeededSongIds.add(songId)

    i = 0
    for songId in thumbnailNeededSongIds:
        print(f"Downloading thumbnail for song {i} of {len(thumbnailNeededSongIds)}...")
        i += 1
        DownloadThumbnail(songId, songDatabase[songId], thumbnailsDir)
        RandomSleep(ThumbnailDownloadMinDelay, ThumbnailDownloadMaxDelay)
    
    print("Saving database...")
    SaveSongDatabase(songDatabase)



# Module 3 - Download Each Song's Audio Stream - APPROVED
# Downloads the audio stream for any song in the Database which does not already have an audio stream in database/songs.
# Regardless of weather an audio stream is needed it updates song.src to reflect the client url of the audio stream.
# Does not depend on previous steps and runs independently.
# If an audio stream can't be downloaded normally tries again with cookies enabled.
def DownloadAudioStream(songId, song, audioStreamsDir):
    global SongDownloadRateLimit, SegmentDownloadMinDelay, SegmentDownloadMaxDelay
    ytdlpOptions = {
        "format": "bestaudio",
        "outtmpl": os.path.join(audioStreamsDir, f"{songId}.%(ext)s"),
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
    }
    targetUrls = [ song["srcUrl"] ]
    downloadFailed = False
    with yt_dlp.YoutubeDL(ytdlpOptions) as ytdlp:
        try:
            ytdlp.download(targetUrls)
        except:
            downloadFailed = True
    if downloadFailed:
        ytdlpOptions["cookiesfrombrowser"] = ("firefox",)
        with yt_dlp.YoutubeDL(ytdlpOptions) as ytdlp:
            ytdlp.download(targetUrls)
    for fileName in os.listdir(audioStreamsDir):
        filePath = os.path.abspath(os.path.join(audioStreamsDir, fileName))
        fileNameNoExt = os.path.splitext(fileName)[0]
        if fileNameNoExt == songId:
            song["src"] = PathToClientUrl(filePath)
            return
    raise Exception(f"Downloaded audio stream for song {songId} but the output file from ytdlp could not be located.")
def Module3():
    print("Loading database...")
    songDatabase = LoadSongDatabase()
    
    print("Downloading audio stream for songs without an audio stream...")
    ChangeDir()
    audioStreamsDir = os.path.abspath("database/songs")
    os.makedirs(audioStreamsDir, exist_ok=True)

    existingFiles = {}
    for fileName in os.listdir(audioStreamsDir):
        filePath = os.path.join(audioStreamsDir, fileName)
        songId = os.path.splitext(fileName)[0]
        if not songId in songDatabase:
            print(f"Warning: Audio stream exists for song {songId} at {filePath} but that song isn't in the database.")
        existingFiles[songId] = filePath

    audioStreamNeededSongIds = set()
    for songId in songDatabase:
        if songId in existingFiles:
            songDatabase[songId]["src"] = PathToClientUrl(existingFiles[songId])
            continue
        audioStreamNeededSongIds.add(songId)

    i = 0
    for songId in audioStreamNeededSongIds:
        print(f"Downloading audio stream for song {i} of {len(audioStreamNeededSongIds)}...")
        i += 1
        DownloadAudioStream(songId, songDatabase[songId], audioStreamsDir)
        RandomSleep(AudioStreamDownloadMinDelay, AudioStreamDownloadMaxDelay)

    print("Saving database...")
    SaveSongDatabase(songDatabase)



def main():
    Module1()
    Module2()
    Module3()
    print("All tasks completed successfully")
    sys.exit(0)
main()