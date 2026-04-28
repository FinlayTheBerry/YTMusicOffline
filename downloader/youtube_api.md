# Setting Up Google Cloud
To get started go to https://console.cloud.google.com/ and sign in.
Next create a new project. IMPORTANT: Make sure you expand the hidden option and set the project id as this cannot be changed later.
Then search for YouTube Data API v3 and press enable.
Next return to https://console.cloud.google.com/ make sure your project is selected in the upper left and then press dashboard.
Expand the hamburger menu and press APIs & Services then select OAuth consent screen.
Select external and fill out the other info. Don't forget to add yourself as a test user when prompted.
Next on the left press Credentials and then Create Credentials then OAuth Client ID.
When creating your credentials make sure to set the application type to desktop app.
Next download the credentials and save them to extractor/client_secrets.json

# Testing APIs From Your Browser
Learn more about the YouTube API you can read the documentation at https://developers.google.com/youtube/v3/docs
The docs also innclude all possible values for inputs to APIs so these are super useful.
You can also use the API explorer.
It's very confusing to get to the API explorer since the main link is broken.
I got to it by going to Samples>Use cases and code samples and then pressing the </> next to an API endpoint.
Don't forget to make it fullscreen and then you can test apis and see what data they return.
https://developers.google.com/youtube/v3/code_samples/code_snippets

# YouTube Music Auto-Generated Descriptions
All songs on YouTube music are actually just videos.
You can convert from a song to a video by pressing share and then copying the video id.
This id will look something like https://music.youtube.com/watch?v=Ws2gU9A-vsw&si=gmhvuAIvuqS57o1o
where the part between ?v= and &si= is the video id. So in this case the id is "Ws2gU9A-vsw".
Note that the rules of URL variable encoding can be used to extract this information.
Once you have the video ID of a song simply go to https://www.youtube.com/watch?v=Ws2gU9A-vsw
but replace "Ws2gU9A-vsw" with your actual video id.
From here you can see how YouTube music works under the hood.
Each YouTube music artist is given a topic channel which will look like ArtistName - Topic.
It is easy enough to check if a song was uploaded by one of these auto generated artist topic channels
by simply removing the " - Topic" suffix if present.
To extract data from the description note that YouTube music auto generates a description with several
key peices of information about the given song.
These peices of information are split into sections and key value pairs.
Each section is separated with a double newline so "\n\n".
Note that all auto generated YouTube music descriptions use Unix line endings not Windows so prepare for \n not \r\n.
Next we have the sections. In order from first to last we have:

Section 0: Provided By Section
Example: "Provided to YouTube by The Orchard Enterprises"
Format: Starts with the text "Provided to YouTube by " then the name of the primary record label.
MultiLine: False
Optional: True

Section 1: Song And Artist Name Section
Example: "SLOW DANCING IN THE DARK · Joji · George Miller · Patrick Wimberly"
Format: An array of strings separated by the string " · ".
The array always contains at least 2 elements with element 0 being the song name and element 1 being the primary artist name.
Additional elements represent other secondary artists who worked on this song.
Empty strings are not premitted in this array.
MultiLine: False
Optional: False

Section 2: Album Name Section
Example: "BALLADS 1"
Format: Simply contains the album name in raw text.
MultiLine: False
Optional: False

Section 3: Publish Info Section
Example: "℗ 2011 M83 Recording Inc. under exclusive license to Mute for North America. All rights reserved.\n℗ 2011 Naive|M83 Recording Inc\n℗ M83 Recording Inc / naïve"
Format: Contains multiple lines which all begin with the string "℗ " then publishing information.
There is a reason to the madness but I don't really care about this info enough to parse it completely.
Suffice it to say it's usually in the form "℗ {PublishingNotes}{; or ,} ℗ {Year} {Publisher}".
MultiLine: True
Optional: True

Section 4: Released On Section
Example: "Released on: 2018-10-26"
Format: Starts with the string "Released on: " followed by a date in the form "yyyy-mm-dd".
MultiLine: False
Optional: True

Section 5: Name And Role Section
Example: "Producer: Joji\nProducer: Patrick Wimberly\nMastering Engineer: Chris Athens\nMusic  Publisher: George Miller - 88rising Publishing / Kobalt Songs Music Publishing (ASCAP)\nMusic  Publisher: Patrick Wimberly - Jonathan Patrick Wimberly Publishing(SESAC)/Kobalt Group Music Publishing (SESAC)"
Format: Split into lines separated by "\n" with no empty lines.
Each line is in the form "{Role}: {Name}".
Note that names can be the names of companies not just individuals.
Bro I'm high key pressed at YouTube music rn. What in the actual formatting fuck is this "Producer: Dirty Rush: Konrad Grela / Gregor Es: Grzegorz Surzyn".
MultiLine: True
Optional: True

Section 6: Auto-generated Tagline Section
Example: "Auto-generated by YouTube."
Format: Contains the exact text "Auto-generated by YouTube.".
This marks the video description as a YouTube music auto-generated description instead of a normal user inputted video description.
MultiLine: False
Optional: False

# Unavailible YTMusic videos
Some youtube music videos are unavailible when you try to download them.
We will call these videos indirect music videos since they can be downloaded
but must be accessed through another videoID.
Each of these types of videos has two videoIDs.
One of which is blocked in all countries and the other one functions normally.

You can identify if you have one of these videos by looking for the following characteristics:
video.contentDetails.regionRestriction.allowed == null;
video.contentDetails.regionRestriction.blocked.Contains(["AD","AE","AF","AG","AI","AL","AM","AO","AQ","AR","AS","AT","AU","AW","AX","AZ","BA","BB","BD","BE","BF","BG","BH","BI","BJ","BL","BM","BN","BO","BQ","BR","BS","BT","BV","BW","BY","BZ","CA","CC","CD","CF","CG","CH","CI","CK","CL","CM","CN","CO","CR","CU","CV","CW","CX","CY","CZ","DE","DJ","DK","DM","DO","DZ","EC","EE","EG","EH","ER","ES","ET","FI","FJ","FK","FM","FO","FR","GA","GB","GD","GE","GF","GG","GH","GI","GL","GM","GN","GP","GQ","GR","GS","GT","GU","GW","GY","HK","HM","HN","HR","HT","HU","ID","IE","IL","IM","IN","IO","IQ","IR","IS","IT","JE","JM","JO","JP","KE","KG","KH","KI","KM","KN","KP","KR","KW","KY","KZ","LA","LB","LC","LI","LK","LR","LS","LT","LU","LV","LY","MA","MC","MD","ME","MF","MG","MH","MK","ML","MM","MN","MO","MP","MQ","MR","MS","MT","MU","MV","MW","MX","MY","MZ","NA","NC","NE","NF","NG","NI","NL","NO","NP","NR","NU","NZ","OM","PA","PE","PF","PG","PH","PK","PL","PM","PN","PR","PS","PT","PW","PY","QA","RE","RO","RS","RU","RW","SA","SB","SC","SD","SE","SG","SH","SI","SJ","SK","SL","SM","SN","SO","SR","SS","ST","SV","SX","SY","SZ","TC","TD","TF","TG","TH","TJ","TK","TL","TM","TN","TO","TR","TT","TV","TW","TZ","UA","UG","UM","US","UY","UZ","VA","VC","VE","VG","VI","VN","VU","WF","WS","YE","YT","ZA","ZM","ZW"]);
video.contentDetails.licensedContent == false;
video.status.privacyStatus == "unlisted";
video.topicDetails == null;

But don't worry it is possible to get the other non-blocked videoID.
We can get this videoID manually by changing https://www.youtube.com/watch?v={VIDEOID}
to https://music.youtube.com/watch?v={VIDEOID}.
When the page loads it will instantly redirect to a new page where the video id is unblocked.

To do this automatically we can use the following:
First use the command below to download the html
curl -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36" https://music.youtube.com/watch?v={VIDEOIDHERE} > ytmusic.html
Then parse through the html for strings starting with "ytcfg.set(" and read until the matching end parenthese.
There may be multiple matches and we want them all.
These strings are json strings which must be parsed.
Once parsed we should look through the json objects we found searching for one with an INITIAL_ENDPOINT field.
The INITIAL_ENDPOINT field contains another json string which must be parsed into another json object.
From there we can extract the value of initialEndpoint.watchEndpoint.videoId to get the video id of the non-blocked video.

Additional notes: The initialEndpoint.watchEndpoint.videoId will simply store the current VideoID for YouTube music songs
which do not require redirection and for all normal non-music YouTube videos.

# Albums And Explicit Tags
So how does one get the album and exclicit tag status of a YouTube music song?
Short answer is that you don't it's really really hard.
Long answer is you send an http post request to:
https://music.youtube.com/youtubei/v1/next
with special cookies and request headers and pray to Alphabet Inc you don't get banned.
As for explicit tags those require another scary request to:
https://music.youtube.com/youtubei/v1/player
again with a bunch of cookies whose functions are currently unknown.
So yeah that's scary :|
Gonna investigate this more later but for now I got spooked.