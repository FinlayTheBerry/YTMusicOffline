"use strict";

(() => {
    const Gui = {};

    VSLib.SetElementsPerScreen(10);

    let Userdata = new Map();
    VSLib.SetRebindCallback((element, index, value, userdata) => {
        if (userdata == null) {
            userdata = {
                index: -1,
                value: null,
                containerElement: element.querySelector(".element_container"),
                thumbnailElement: element.querySelector(".element_thumbnail"),
                textElement: element.querySelector(".element_text"),
            };
            Userdata.set(element, userdata);
        }
        userdata.index = index;
        userdata.value = value;
        if (value == null) {
            userdata.containerElement.style.visibility = "hidden";
        } else {
            userdata.containerElement.style.visibility = "visible";
            userdata.textElement.innerHTML = Player.RuntimeData[index].textHtml;
        }

        return userdata;
    });

    VSLib.SetUpdateCallback((elements, startIndex, dataset) => {
        const imgElements = [];
        for (let element of elements) {
            imgElements.push(Userdata.get(element).thumbnailElement);
        }
        ThumbLib.StartTransaction();
        ThumbLib.SetElements(imgElements);
        ThumbLib.SetStartIndex(startIndex);
        ThumbLib.EndTransaction();
    });

    Gui.OnElementClicked = (element) => {
        Player.PlaySong(Userdata.get(element.parentElement).index);
    };

    let PortraitMode = undefined;
    const OnWindowResize = () => {
        if (window.innerHeight > window.innerWidth) {
            if (PortraitMode !== true) {
                document.documentElement.style.setProperty("--search-container-height", "75px");
                document.documentElement.style.setProperty("--player-container-height", "250px");
                PortraitMode = true;
            }
        } else {
            if (PortraitMode !== false) {
                document.documentElement.style.setProperty("--search-container-height", "50px");
                document.documentElement.style.setProperty("--player-container-height", "150px");
                PortraitMode = false;
            }
        }
    };
    window.addEventListener("resize", OnWindowResize);
    OnWindowResize();

    Gui.OnSearchButtonClicked = () => {
        Player.Search(SearchBarElement.value);
    };

    Gui.RefreshPlayer = () => {
        if (Player.NowPlaying == null) {
            PlayerTextElement.innerHTML = "Nothing is playing...";
            PlayerThumbnailElement.style.visibility = "hidden";
        } else {
            PlayerTextElement.innerHTML = Player.RuntimeData[Player.NowPlaying].textHtml;
            PlayerThumbnailElement.src = Player.Database[Player.NowPlaying].thumbnail;
            PlayerThumbnailElement.style.visibility = "visible";
        }

        if (Player.Loop) {
            PlayerLoopElement.textContent = "Loop✅";
        } else {
            PlayerLoopElement.textContent = "Loop❌";
        }
    };

    document.addEventListener("keydown", (event) => {
        if ((event.key == "f" || event.key == "F") && (event.ctrlKey || event.metaKey)) {
            event.preventDefault(); 
            SearchBarElement.focus();
        }
    });

    let PlayerThumbnailElement = null;
    let PlayerTextElement = null;
    let PlayerWatchOriginalElement = null;
    let PlayerLoopElement = null;
    let SearchBarElement = null;
    let FavoriteButton = null;
    let ElementRefrencesNull = true;
    const SetElementRefrences = () => {
        PlayerThumbnailElement = document.querySelector(".player_thumbnail");
        PlayerTextElement = document.querySelector(".player_text");
        PlayerWatchOriginalElement = document.querySelector(".player_watch_original");
        PlayerWatchOriginalElement.addEventListener("click", (event) => {
            event.preventDefault();
            if (Player.NowPlaying != null) {
                window.open(Player.Database[Player.NowPlaying].srcUrl, "_blank");
            }
        });
        PlayerLoopElement = document.querySelector(".player_loop");
        SearchBarElement = document.querySelector(".search_bar");
        SearchBarElement.addEventListener("keydown", (event) => {
            if (event.key == "Enter") {
                Gui.OnSearchButtonClicked();
                SearchBarElement.blur();
            } else if (event.key == "Escape") {
                SearchBarElement.blur();
            }
        });
        SearchBarElement.addEventListener("focus", () => {
            SearchBarElement.select();
        });
        FavoriteButton = document.querySelector(".player_favorite");
        ElementRefrencesNull = false;

        const FavoriteButtonStartCharging = () => { FavoriteButton.classList.add("charging") };
        const FavoriteButtonStopCharging = () => { FavoriteButton.classList.remove("charging") };

        FavoriteButton.addEventListener("mousedown", FavoriteButtonStartCharging);
        FavoriteButton.addEventListener("mouseup", FavoriteButtonStopCharging);
        FavoriteButton.addEventListener("mouseleave", FavoriteButtonStopCharging);
        FavoriteButton.addEventListener("transitionend", (e) => {
          const currentFavoriteButtonChargePercentage = getComputedStyle(FavoriteButton).getPropertyValue("--favorite_button_charge_percentage").trim();
          if (e.propertyName === "--favorite_button_charge_percentage" && currentFavoriteButtonChargePercentage === "100%") {
            Player.Favorite();
            FavoriteButtonStopCharging();
          }
        });

        Gui.RefreshPlayer();
    };
    if (document.readyState == "loading") {
        document.addEventListener("DOMContentLoaded", SetElementRefrences);
    } else {
        SetElementRefrences();
    }

    globalThis.Gui = Gui;
})();