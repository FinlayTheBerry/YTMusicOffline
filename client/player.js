"use strict";

(() => {
    const Player = {};

    Player.Database = [];
    Player.RuntimeData = [];
    Player.NowPlaying = null;
    Player.Selected = null;

    let AudioElement = null;
    let ElementRefrencesNull = true;

    const RegenRuntimeData = () => {
        const highlightStart = "<span class=\"element_highlight\">";
        const highlightEnd = "</span>";

        Player.RuntimeData = Player.Database.map(song => {
            let text = song.title;
            let textHtml = highlightStart + song.title + highlightEnd;
            if (song.album != undefined && song.album != null && song.album != "") {
                text += " from " + song.album;
                textHtml += " from " + highlightStart + song.album + highlightEnd;
            }
            switch (song.artists.length) {
                case 0:
                    text += " by unknown artist";
                    textHtml += " by unknown artist";
                    break;
                case 1:
                    text += " by " + song.artists[0];
                    textHtml += " by " + highlightStart + song.artists[0] + highlightEnd;
                    break;
                case 2:
                    text += " by " + song.artists[0];
                    text += ", and " + song.artists[1];
                    textHtml += " by " + highlightStart + song.artists[0] + highlightEnd;
                    textHtml += ", and " + highlightStart + song.artists[1] + highlightEnd;
                    break;
                case 3:
                    text += " by " + song.artists[0];
                    text += ", " + song.artists[1];
                    text += ", and " + song.artists[2];
                    textHtml += " by " + highlightStart + song.artists[0] + highlightEnd;
                    textHtml += ", " + highlightStart + song.artists[1] + highlightEnd;
                    textHtml += ", and " + highlightStart + song.artists[2] + highlightEnd;
                    break;
                default:
                    text += " by " + song.artists[0];
                    text += ", " + song.artists[1];
                    text += ", " + song.artists[2];
                    text += ", and others";
                    textHtml += " by " + highlightStart + song.artists[0] + highlightEnd;
                    textHtml += ", " + highlightStart + song.artists[1] + highlightEnd;
                    textHtml += ", " + highlightStart + song.artists[2] + highlightEnd;
                    textHtml += ", and others";
                    break;
            }
            // const releaseDateObj = new Date(song.releaseDate * 1000);
            // const releaseDay = ("0" + releaseDateObj.getUTCDate().toString()).slice(-2);
            // const releaseMonth = ("0" + (releaseDateObj.getUTCMonth() + 1).toString()).slice(-2);
            // const releaseYear = ("000" + releaseDateObj.getUTCFullYear().toString()).slice(-4);
            // const releaseDateStr = releaseMonth + "/" + releaseDay + "/" + releaseYear;
            // text += " released on " + releaseDateStr;
            // textHtml += " released on " + highlightStart + releaseDateStr + highlightEnd;
            return { text: text, textHtml: textHtml };
        });
    };

    const LoadDatabase = () => {
        fetch("/database/database.json").then((result) => {
            result.json().then((result) => {
                Player.Database = Object.values(result);

                VSLib.SetDataset(Player.Database);
                ThumbLib.SetDataset(Player.Database.map(song => song.thumbnail));

                RegenRuntimeData();

                console.timeEnd("PageLoad");
            });
        });
    };
    LoadDatabase();

    const SaveDatabase = () => {
        const jsonStr = JSON.stringify(Player.Database, null, 4);
        fetch("/api/save_database", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: jsonStr
        }).then(response => {
            if (!response.ok) {
                throw new Error(`ERROR: Http status code ${response.status} on post to /api/save_database.`);
            }
        }).catch(error => {
            throw new Error('Error saving database:', error);
        });
    };

    const SetElementRefrences = () => {
        AudioElement = document.querySelector(".player_audio");
        ElementRefrencesNull = false;
    };
    if (document.readyState == "loading") {
        document.addEventListener("DOMContentLoaded", SetElementRefrences);
    } else {
        SetElementRefrences();
    }

    const RandomRange = (min, max) => {
        const range = max - min;
        if (range <= 0) return min;

        let mask = 1;
        let bitCount = 1;
        for (let i = range - 1; i >>= 1; i > 0) {
            mask = (mask << 1) | 1;
            bitCount++;
        }

        const byteCount = Math.ceil(bitCount / 8);
        const array = new Uint8Array(byteCount);

        while (true) {
            window.crypto.getRandomValues(array);
            let result = 0;
            for (let i = 0; i < byteCount; i++) {
                result = (result << 8) | array[i];
            }
            result = result & mask;
            if (result < range) {
                return result + min;
            }
        }
    }

    Player.PlaySong = (index) => {
        AudioElement.pause();
        AudioElement.currentTime = 0;
        Player.NowPlaying = index;

        if (Player.NowPlaying == null) {
            AudioElement.src = "";
        } else {
            AudioElement.src = Player.Database[Player.NowPlaying].src;
            AudioElement.play();
        }
        Gui.RefreshPlayer();

        if ("mediaSession" in navigator) {
            if (Player.NowPlaying == null) {
                navigator.mediaSession.metadata = null;
            } else {
                navigator.mediaSession.metadata = new MediaMetadata({
                    title: Player.Database[Player.NowPlaying].title,
                    artist: Player.Database[Player.NowPlaying].artists[0],
                    album: Player.Database[Player.NowPlaying].album,
                    artwork: [{ src: Player.Database[Player.NowPlaying].thumbnail }]
                });
            }
        }
    };

    Player.Search = (query) => {
        query = query.toLowerCase();

        let searchStartIndex = 0;
        if (Player.SelectedSongIndex != null) {
            searchStartIndex = Player.SelectedSongIndex + 1;
        }
        for (let i = searchStartIndex; i < Player.Database.length; i++) {
            if (Player.RuntimeData[i].text.toLowerCase().includes(query)) {
                Player.SelectedSongIndex = i;
                VSLib.ScrollToElementByIndex(i);
                break;
            }
        }
    };
    Player.ClearSearch = () => {
        Player.SelectedSongIndex = null;
    }

    Player.Loop = false;
    Player.ToggleLoop = () => {
        Player.Loop = !Player.Loop;
        AudioElement.loop = Player.Loop;
        Gui.RefreshPlayer();
    };

    Player.PlayPause = () => {
        if (AudioElement.paused) {
            AudioElement.play();
        } else {
            AudioElement.pause();
        }
    };

    Player.Favorite = () => {
        if (Player.NowPlaying == null) {
            return;
        }

        const song = Player.Database.splice(Player.NowPlaying, 1)[0];
        Player.Database.unshift(song);
        const runtimeData = Player.RuntimeData.splice(Player.NowPlaying, 1)[0];
        Player.RuntimeData.unshift(runtimeData);
        Player.NowPlaying = 0;

        VSLib.SetDataset(Player.Database);
        ThumbLib.SetDataset(Player.Database.map(song => song.thumbnail));

        SaveDatabase();
    };

    Player.Next = () => {
        Player.PlaySong(RandomRange(0, Player.Database.length));
    };
    navigator.mediaSession.setActionHandler("nexttrack", () => {
        Player.Next();
    });

    globalThis.Player = Player;
})();
