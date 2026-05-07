"use strict";

(() => {
    const Player = {};

    Player.Database = [];
    Player.ShowingQueue = false;
    Player.Queue = [];
    Player.DatabaseView = [];
    Player.NowPlaying = null;
    Player.Selected = null;

    const RandomRange = (min, max) => {
        const range = max - min;
        if (range <= 0) {
            throw Error(`Invalid range ${min} to ${max}`);
        }
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

    const LoadDatabase = () => {
        fetch("/database/database.json").then((result) => {
            result.json().then((result) => {
                Player.Database = Object.values(result);

                VSLib.SetDataset(Player.Database);
                ThumbLib.SetDataset(Player.Database.map(song => song.thumbnail));

                const highlightStart = "<span class=\"element_highlight\">";
                const highlightEnd = "</span>";

                for (let i = 0; i < Player.Database.length; i++) {
                    const song = Player.Database[i];
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
                    Player.Database[i].RuntimeData = { text: text, textHtml: textHtml };
                }

                Player.DatabaseView = [...Player.Database];

                console.timeEnd("PageLoad");
            });
        });
    };
    LoadDatabase();

    const SaveDatabase = () => {
        const jsonStr = JSON.stringify(Player.Database, (key, value) => {
            if (key == "RuntimeData") {
                return undefined;
            }
            return value;
        }, 4);
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

    const UpdateView = () => {
        if (Player.ShowingQueue) {
            VSLib.SetDataset(Player.Queue);
            ThumbLib.SetDataset(Player.Queue.map(song => song.thumbnail));
        } else {
            VSLib.SetDataset(Player.DatabaseView);
            ThumbLib.SetDataset(Player.DatabaseView.map(song => song.thumbnail));
        }
    };
    
    let AudioElement = null;
    let ElementRefrencesNull = true;
    const SetElementRefrences = () => {
        AudioElement = document.querySelector(".player_audio");
        ElementRefrencesNull = false;
    };
    if (document.readyState == "loading") {
        document.addEventListener("DOMContentLoaded", SetElementRefrences);
    } else {
        SetElementRefrences();
    }

    Player.PlaySong = (song) => {
        AudioElement.pause();
        AudioElement.currentTime = 0;
        Player.NowPlaying = song;
        if (Player.NowPlaying == null) {
            AudioElement.src = "";
        } else {
            AudioElement.src = Player.NowPlaying.src;
            AudioElement.play();
        }
        Gui.RefreshPlayer();
        if ("mediaSession" in navigator) {
            if (Player.NowPlaying == null) {
                navigator.mediaSession.metadata = null;
            } else {
                navigator.mediaSession.metadata = new MediaMetadata({
                    title: Player.NowPlaying.title,
                    artist: Player.NowPlaying.artists[0],
                    album: Player.NowPlaying.album,
                    artwork: [{ src: Player.NowPlaying.thumbnail }]
                });
            }
        }
    };

    Player.QueueAdd = (song, playIfStopped) => {
        const index = Player.Queue.indexOf(song);
        if (index != -1) {
            Player.Queue.splice(index, 1);
        }
        Player.Queue.push(song);
        UpdateView();
        if (Player.NowPlaying == null && playIfStopped) {
            Player.PlaySong(Player.Queue[0]);
        }
    };
    Player.QueueRemove = (song) => {
        const index = Player.Queue.indexOf(song);
        if (index == -1) {
            return;
        }
        if (Player.NowPlaying != null && Player.Queue[index] == Player.NowPlaying) {
            return;
        }
        Player.Queue.splice(index, 1);
        UpdateView();
    };

    Player.ToggleShowQueue = () => {
        Player.ShowingQueue = !Player.ShowingQueue;
        UpdateView();
        Gui.RefreshPlayer();
    };

    Player.GetLoop = () => {
        return AudioElement.loop;
    };
    Player.ToggleLoop = () => {
        AudioElement.loop = !AudioElement.loop;
        Gui.RefreshPlayer();
    };

    Player.PlayPause = () => {
        if (AudioElement.paused) {
            AudioElement.play();
        } else {
            AudioElement.pause();
        }
    };

    Player.Favorite = (song) => {
        const index = Player.Database.indexOf(song);
        Player.Database.splice(index, 1)[0];
        Player.Database.unshift(song);

        const index2 = Player.DatabaseView.indexOf(Player.NowPlaying);
        if (index2 != -1) {
            Player.DatabaseView.splice(index2, 1)[0];
            Player.DatabaseView.unshift(song);
        }

        UpdateView();
        SaveDatabase();
    };

    Player.Next = () => {
        let index = 0;
        if (Player.NowPlaying != null) {
            index = Player.Queue.indexOf(Player.NowPlaying) + 1;
        }
        if (index >= Player.Queue.length) {
            Player.QueueAdd(Player.Database[RandomRange(0, Player.Database.length)], false);
            UpdateView();
            index = Player.Queue.length - 1;
        }
        Player.PlaySong(Player.Queue[index]);
    };
    navigator.mediaSession.setActionHandler("nexttrack", () => {
        Player.Next();
    });

    Player.Previous = () => {
        let index = -1;
        if (Player.NowPlaying != null) {
            index = Player.Queue.indexOf(Player.NowPlaying) - 1;
        }
        if (index < 0) {
            return;
        }
        Player.PlaySong(Player.Queue[index]);
    };
    navigator.mediaSession.setActionHandler("previoustrack", () => {
        Player.Previous();
    });

    Player.Search = (query) => {
        query = query.toLowerCase();
        Player.DatabaseView = [];
        if (query == "") {
            Player.DatabaseView = [...Player.Database];
        } else {
            for (let i = 0; i < Player.Database.length; i++) {
                if (Player.Database[i].RuntimeData.text.toLowerCase().includes(query)) {
                    Player.DatabaseView.push(Player.Database[i]);
                }
            }
        }
        UpdateView();
    };

    globalThis.Player = Player;
})();
