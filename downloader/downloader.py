#!/bin/python3



# NOTE ON API COST:
# Total API cost is at maximum the following assuming only the Liked Music playlist is larger than 100 videos:
# ciel(NumOfPlaylists / 50) + ciel(NumOfVideos / 50) + (NumOfPlaylists * 2) + ciel(NumOfVideos / 50)
# That's about 322 querries for 79 playlists and 4005 videos.



# User Settings
# To get the latest user agent from your browser run the following in the developer console:
# console.log(navigator.userAgent);
UserAgent = "Mozilla/5.0 (X11; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0"
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
import sys
import os
import urllib.request
import urllib.parse
import time
from datetime import datetime, timezone
import random
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
def LoadSongDatabase():
    databaseDir = os.path.realpath("database")
    os.makedirs(databaseDir, exist_ok=True)
    databasePath = os.path.join(databaseDir, "database.json")
    if not os.path.exists(databasePath):
        return []
    else:
        return json.loads(ReadFile(databasePath))
def SaveSongDatabase(songDatabase):
    databaseDir = os.path.realpath("database")
    os.makedirs(databaseDir, exist_ok=True)
    databasePath = os.path.join(databaseDir, "database.json")
    WriteFile(databasePath, json.dumps(songDatabase, indent=4, ensure_ascii=False))
os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))



# Module 1 - Add New Songs To The Database
def AuthApi():
    userSecretsPath = os.path.realpath("downloader/user_secrets.json")
    clientSecretsPath = os.path.realpath("downloader/client_secrets.json")
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

    WriteFile(userSecretsPath, credentials.to_json())

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
def EnumMyVideos(youtubeApi, includeLikes=False, includeLikedMusic=False):
    myPlaylistIds = EnumMyPlaylists(youtubeApi, includeLikes, includeLikedMusic)

    myVideoIds = []
    progress = 0
    for myPlaylistId in myPlaylistIds:
        for myVideoId in EnumPlaylistContents(youtubeApi, myPlaylistId):
            if not myVideoId in myVideoIds:
                myVideoIds.append(myVideoId)
        progress += 1
        print(f"Progress: {progress} of {len(myPlaylistIds)}...")
    return myVideoIds
def GetVideoInfo(youtubeApi, infoNeededVideoIds, videoInfoDatabase):
    progress = 0
    while progress < len(infoNeededVideoIds):
        nextVideoIds = infoNeededVideoIds[progress:progress + 50]
        request = youtubeApi.videos().list(
            part="contentDetails,id,liveStreamingDetails,localizations,paidProductPlacementDetails,player,recordingDetails,snippet,statistics,status,topicDetails",
            id=",".join(nextVideoIds),
            maxResults=50
        )
        response = request.execute()
        for video in response["items"]:
            videoId = video["id"]
            videoInfoDatabase[videoId] = video
            nextVideoIds.remove(videoId)
        for videoId in nextVideoIds:
            PrintWarning(f"Unable to get video info for video Id {videoId}.")
        progress += 50
        if progress > len(infoNeededVideoIds):
            progress = len(infoNeededVideoIds)
        print(f"Progress: {progress} of {len(infoNeededVideoIds)}...")
    infoNeededVideoIds.clear()
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
    # headers = { "User-Agent": UserAgent }
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Connection': 'keep-alive',
    }
    cookies = {
        '__Secure-ROLLOUT_TOKEN': 'CLyzobDd2cKF8gEQoYj0vrSrkwMYy4uHhNGRlAM%3D',
        'VISITOR_INFO1_LIVE': 'WAN-HW2iRqQ',
        'VISITOR_PRIVACY_METADATA': 'CgJVUxIEGgAgbg%3D%3D',
        'PREF': 'f6=40000080&f7=100&tz=America.Los_Angeles&repeat=NONE&f5=30000&autoplay=true&volume=100',
        '__Secure-1PSIDTS': 'sidts-CjQBhkeRdyCRLwJh8ziN1TVsqh7Y8pUbkmuqHfj8CT2mbJiS4HzEug7S8BmZticMMxdfoN2BEAA',
        '__Secure-3PSIDTS': 'sidts-CjQBhkeRdyCRLwJh8ziN1TVsqh7Y8pUbkmuqHfj8CT2mbJiS4HzEug7S8BmZticMMxdfoN2BEAA',
        'HSID': 'A2JerDTJw0pbTqXqt',
        'SSID': 'AAXOuFk5rbBoiN_b5',
        'APISID': 'jDrlYCPlFK618jMk/AXbBHi_wxjhosAcp0',
        'SAPISID': 'WXRFw_v-rqDWwSb1/AGsRNSgph2SPLeFqW',
        '__Secure-1PAPISID': 'WXRFw_v-rqDWwSb1/AGsRNSgph2SPLeFqW',
        '__Secure-3PAPISID': 'WXRFw_v-rqDWwSb1/AGsRNSgph2SPLeFqW',
        'SID': 'g.a0009QhWV6IsoqLTB1r5me4EANH78VXsDrd4NGy1oRNq0pS8KkAGpTOL8BXaM1tya7OaI0xFRgACgYKAbYSARESFQHGX2MivN-1dB2Mvx5BJBtLWDZSDxoVAUF8yKroOUxKI4UpKrtFLtZWn1nk0076',
        '__Secure-1PSID': 'g.a0009QhWV6IsoqLTB1r5me4EANH78VXsDrd4NGy1oRNq0pS8KkAGcsZVthYcjYg9DInKdAgqcgACgYKAZkSARESFQHGX2MiXkBrEQskhsqkYOVYcWgSFhoVAUF8yKq2A_0Nbo5XaYwD9KHuHiyo0076',
        '__Secure-3PSID': 'g.a0009QhWV6IsoqLTB1r5me4EANH78VXsDrd4NGy1oRNq0pS8KkAGT_gec-DXUBoDfNtpdIvduwACgYKAVUSARESFQHGX2MiNg84LfTcrOiWqFpvvA4H-hoVAUF8yKrT2gnlnWMS22vuty1bCm8S0076',
        'LOGIN_INFO': 'AFmmF2swRQIgGL_bFCYzUQiG1ai13odpceoVhPXIzloekDCZgrYor6UCIQD5RAA5pZ1Gi87YKuPFG47Rkc8wpHXzoKzxjnQVWUxwUA:QUQ3MjNmenJWZlpZc2w2UW9DYndEZFpHWEIxanAtSnJNM2NJc3NsNmtnb0RTMDB5c3ZfUzY0UU9XNFZKbG9oZmFvSHVnbmk3M1MtdTlCT2gySkdnaTVWRE5icGIwOHhyckNzWFJHa1ZmSXk0dmk3QVBmM3NHTGlYdzFITW5PZndwR21ac0VmY0R4S2NzQ240Tk1VSVJRRF9ES0x0X1NTQktB',
        'SIDCC': 'AKEyXzVsY_SruDCM9KphqDj4wKIjS2lCAIk3aizcpWuIWNgAs0DbLYz7CpmE4wddGEaHDyms-g',
        '__Secure-1PSIDCC': 'AKEyXzU5huG8wdkQPOfOZcXWTXubnfFv5SrZC2zO_MB8_ubU0HoWeAp79VFdGje8_0F0v_L32N0',
        '__Secure-3PSIDCC': 'AKEyXzURaLs0hkiECHtVNnwZ9r6oA6lJqQKyNmCUifldWQqhq35KPKqZCDHP3eFjm4iYO8vhrbY',
        '__Secure-BUCKET': 'CMUH',
        '__Secure-YNID': '18.YT=iulC1nKg7GCMS4oxfzk_gxlYRObwTvdwIsuFsfG322DYwlmPIWjBRoawgq6XX5sNhn3sSdqelFLC3TQMvjsLFrCvlimUSqUSuY0joOgTD6egP8HQrK1AmJUh6fqwAJsjksjUx08DmPgrwUKSc915x_OVcPoQSTy30-5aruWUJtg8QD1rbt5Sg1OPN1tbsKHNQXasgAA3b47oW-LXTxgKoQBhf5XvioLsR5wMcb6xUgrVzd0tPm-GEk2Mh-rl1KaZdE5sb-x5dqSBRpaeBB-xu3ar_Z0UNNQxSmvOeJEAzReIuf9-r_OHPBG6koejKSJXBEf86TON7Xiomy0zQzvZlA',
        'YSC': 'wW9njxbeIVc',
        'wide': '0',
        'CONSISTENCY': 'AH5K9rZupymvuk-WQz2zWutEnQYP8oZw-a_jdXfCz2wGpeij6LGUDAhv8eqX0SGWpXh1U_TcmB_DwoK2ZuK-e5tp50L54YVsicMYZkEePqqLZpNoNXOM4_afRtZ9-scPb05q29QE2owEXvrCwlhxhka9BJAhf3piAR6U4NxSlTT1el6_B1IotEaszBUSNXhT-960sj1q0omJaKjWKB1mGO2oHSdU8A',
    }
    response = requests.get(musicUrl, headers=headers, cookies=cookies)
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
        initialEndpoint = json.loads(ytcfg["INITIAL_ENDPOINT"])
        if not DictionaryHas(initialEndpoint, "watchEndpoint.videoId"):
            continue
        tracedVideoId = initialEndpoint["watchEndpoint"]["videoId"]
        if tracedVideoId == videoId:
            return None
        return tracedVideoId
    return None
def TraceUnavailableVideos(infoNeededVideoIds, videoInfoDatabase):
    traceNeededVideoIds = set()
    for videoId in list(videoInfoDatabase.keys()):
        if IsVideoUnavailable(videoInfoDatabase[videoId]):
            traceNeededVideoIds.add(videoId)
            del videoInfoDatabase[videoId]

    progress = 0
    for videoId in traceNeededVideoIds:
        if progress != 0:
            RandomSleep(TraceMinDelay, TraceMaxDelay)
        tracedVideoId = TraceVideo(videoId)
        if tracedVideoId == None:
            PrintWarning(f"Unable to trace unavailable video with video Id {videoId}.")
        elif not tracedVideoId in videoInfoDatabase and not tracedVideoId in traceNeededVideoIds:
            infoNeededVideoIds.append(tracedVideoId)
        progress += 1
        print(f"Progress: {progress} of {len(traceNeededVideoIds)}...")
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
    ytVideoId = videoId

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

    return { "srcUrl": srcUrl, "src": src, "thumbnailUrl": thumbnailUrl, "thumbnail": thumbnail, "title": title, "album": album, "artists": artists, "releaseDate": releaseDate, "ytVideoId": ytVideoId }
def AddNewVideosToSongDatabase(videoInfoDatabase, songDatabase):
    ytVideoIdsAlreadyConverted = set()
    for song in songDatabase:
        ytVideoIdsAlreadyConverted.add(song["ytVideoId"])
    
    for ytVideoId in ytVideoIdsAlreadyConverted:
        if not ytVideoId in videoInfoDatabase:
            PrintWarning(f"Song exists in song database with Id {ytVideoId} but that song isn't in your likes or any playlist.")
    
    # New songs must be added in reverse order.
    for ytVideoId in videoInfoDatabase:
        if not ytVideoId in ytVideoIdsAlreadyConverted:
            songDatabase.insert(0, ConvertVideoToSong(ytVideoId, videoInfoDatabase[ytVideoId]))
def Module1():
    print("Authenticating with YouTube Api...")
    youtubeApi = AuthApi()

    print("Fetching playlist contents...")
    infoNeededVideoIds = EnumMyVideos(youtubeApi, includeLikes=False, includeLikedMusic=True)

    videoInfoDatabase = {}
    while len(infoNeededVideoIds) > 0:
        print("Fetching video info for all videos currently without info...")
        GetVideoInfo(youtubeApi, infoNeededVideoIds, videoInfoDatabase)

        print("Tracing unavailable videos to see if they were redirected...")
        TraceUnavailableVideos(infoNeededVideoIds, videoInfoDatabase)

    print("Loading database...")
    songDatabase = LoadSongDatabase()

    print("Extracting song info from video info...")
    AddNewVideosToSongDatabase(videoInfoDatabase, songDatabase)

    print("Saving database...")
    SaveSongDatabase(songDatabase)



# Module 2 - Download Each Song's Thumbnail
# Downloads the thumbnail for any song in the Database which does not already have a thumbnail in database/thumbnails.
# Regardless of weather a thumbnail is needed it updates song.thumbnail to reflect the client url of the thumbnail.
# Does not depend on previous steps and runs independently.
def DownloadThumbnail(song, thumbnailsDir):
    thumbnailUrl = song["thumbnailUrl"]
    thumbnailUrlPath = urllib.parse.urlparse(thumbnailUrl).path
    thumbnailFileExt = os.path.splitext(os.path.basename(thumbnailUrlPath))[1]
    thumbnailFilePath = os.path.join(thumbnailsDir, song["ytVideoId"] + thumbnailFileExt)
    request = urllib.request.Request(thumbnailUrl, headers={ "User-Agent": UserAgent })
    with urllib.request.urlopen(request) as responseFile: response = responseFile.read()
    with open(thumbnailFilePath, "wb") as thumbnailFile: thumbnailFile.write(response)
    song["thumbnail"] = PathToClientUrl(thumbnailFilePath)
def Module2():
    print("Loading database...")
    songDatabase = LoadSongDatabase()

    print("Downloading thumbnails for songs without a thumbnail...")
    thumbnailsDir = os.path.realpath("database/thumbnails")
    os.makedirs(thumbnailsDir, exist_ok=True)

    existingFiles = set()
    for fileName in os.listdir(thumbnailsDir):
        filePath = os.path.join(thumbnailsDir, fileName)
        existingFiles.add(PathToClientUrl(filePath))

    songsInNeedOfThumbnails = []
    for song in songDatabase:
        if song["thumbnail"] == None:
            songsInNeedOfThumbnails.append(song)
        elif not song["thumbnail"] in existingFiles:
            PrintWarning(f"Thumbnail for song {song["ytVideoId"]} is said to be at {song["thumbnail"]} but has been deleted.")
        else:
            existingFiles.remove(song["thumbnail"])

    for filePath in existingFiles:
        PrintWarning(f"Thumbnail exists at {filePath} but is claimed by no song.")
    
    progress = 0
    for song in songsInNeedOfThumbnails:
        DownloadThumbnail(song, thumbnailsDir)
        RandomSleep(ThumbnailDownloadMinDelay, ThumbnailDownloadMaxDelay)
        SaveSongDatabase(songDatabase)
        progress += 1
        print(f"Progress: {progress} of {len(songsInNeedOfThumbnails)}...")



# Module 3 - Download Each Song's Audio Stream
# Downloads the audio stream for any song in the Database which does not already have an audio stream in database/songs.
# Regardless of weather an audio stream is needed it updates song.src to reflect the client url of the audio stream.
# Does not depend on previous steps and runs independently.
# If an audio stream can't be downloaded normally tries again with cookies enabled.
def DownloadAudioStream(song, audioStreamsDir, tempDir):
    ytdlpOptions = {
        "format": "bestaudio",
        "outtmpl": os.path.join(tempDir, f"{song["ytVideoId"]}.%(ext)s"),
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
    
    retryWithCookies = False
    with yt_dlp.YoutubeDL(ytdlpOptions) as ytdlp:
        try:
            ytdlp.download(targetUrls)
        except Exception as ex:
            PrintError(repr(ex))
            retryWithCookies = True

    if retryWithCookies:
        PrintWarning(f"Downloading {song["srcUrl"]} failed. Retrying with cookies.")
        ytdlpOptions["cookiesfrombrowser"] = ("firefox",)
        with yt_dlp.YoutubeDL(ytdlpOptions) as ytdlp:
            ytdlp.download(targetUrls)

    fileNamesInTemp = os.listdir(tempDir)
    if len(fileNamesInTemp) != 1:
        raise Exception("Incorrect number of files in tempDir.")
    perminantPath = os.path.join(audioStreamsDir, fileNamesInTemp[0])
    os.rename(os.path.join(tempDir, fileNamesInTemp[0]), perminantPath)
    song["src"] = PathToClientUrl(perminantPath)
def Module3():
    print("Loading database...")
    songDatabase = LoadSongDatabase()

    print("Downloading audio stream for songs without an audio stream...")
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
        if song["src"] == None:
            songsInNeedOfAudioStreams.append(song)
        elif not song["src"] in existingFiles:
            PrintWarning(f"Audio stream for song {song["ytVideoId"]} is said to be at {song["src"]} but has been deleted.")
        else:
            existingFiles.remove(song["src"])

    for filePath in existingFiles:
        PrintWarning(f"Audio stream exists at {filePath} but is claimed by no song.")
    
    progress = 0
    for song in songsInNeedOfAudioStreams:
        DownloadAudioStream(song, audioStreamsDir, tempDir)
        RandomSleep(AudioStreamDownloadMinDelay, AudioStreamDownloadMaxDelay)
        SaveSongDatabase(songDatabase)
        progress += 1
        print(f"Progress: {progress} of {len(songsInNeedOfAudioStreams)}...")

    os.rmdir(tempDir)



def main():
    # Module1()
    Module2()
    Module3()
    print("All tasks completed successfully")
    sys.exit(0)
main()