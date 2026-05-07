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
            userdata.textElement.innerHTML = value.RuntimeData.textHtml;
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
        if (Player.ShowingQueue) {
            Player.PlaySong(Userdata.get(element.parentElement).value);
        } else {
            Player.QueueAdd(Userdata.get(element.parentElement).value, true);
        }
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

    Gui.OnSearchClearButton = () => {
        SearchBarElement.value = "";
        Player.Search("");
    };
    Gui.OnSearchSubmitButton = () => {
        Player.Search(SearchBarElement.value);
    };

    Gui.RefreshPlayer = () => {
        if (Player.NowPlaying == null) {
            PlayerTextElement.innerHTML = "Nothing is playing...";
            PlayerThumbnailElement.style.visibility = "hidden";
        } else {
            PlayerTextElement.innerHTML = Player.NowPlaying.RuntimeData.textHtml;
            PlayerThumbnailElement.src = Player.NowPlaying.thumbnail;
            PlayerThumbnailElement.style.visibility = "visible";
        }

        if (Player.GetLoop()) {
            PlayerLoopElement.textContent = "🔁";
        } else {
            PlayerLoopElement.textContent = "🔄";
        }

        if (Player.ShowingQueue) {
            PlayerShowQueueElement.textContent = "Show All";
        } else {
            PlayerShowQueueElement.textContent = "Show Queue";
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
    let PlayerLoopElement = null;
    let PlayerShowQueueElement = null;
    let SearchBarElement = null;
    let FavoriteButton = null;
    let FavoriteButtonText = null;
    let ElementRefrencesNull = true;
    const SetElementRefrences = () => {
        PlayerThumbnailElement = document.querySelector(".player_thumbnail");
        PlayerTextElement = document.querySelector(".player_text");
        PlayerLoopElement = document.querySelector(".player_loop");
        PlayerShowQueueElement = document.querySelector(".player_show_queue");
        SearchBarElement = document.querySelector(".search_bar");
        SearchBarElement.addEventListener("keydown", (event) => {
            if (event.key == "Enter") {
                Gui.OnSearchSubmitButton();
                SearchBarElement.blur();
            } else if (event.key == "Escape") {
                SearchBarElement.blur();
            }
        });
        SearchBarElement.addEventListener("focus", () => {
            SearchBarElement.select();
        });
        FavoriteButton = document.querySelector(".player_favorite");
        FavoriteButtonText = document.querySelector(".player_favorite_text");
        ElementRefrencesNull = false;

        const FavoriteButtonOriginalText = FavoriteButtonText.textContent;
        const FavoriteButtonStartCharging = () => { FavoriteButton.classList.add("charging") };
        const FavoriteButtonStopCharging = () => { FavoriteButton.classList.remove("charging") };
        FavoriteButton.addEventListener("pointerdown", FavoriteButtonStartCharging);
        FavoriteButton.addEventListener("pointerup", FavoriteButtonStopCharging);
        FavoriteButton.addEventListener("pointerleave", FavoriteButtonStopCharging);
        FavoriteButton.addEventListener("pointercancel", FavoriteButtonStopCharging);
        FavoriteButton.addEventListener("transitionend", (e) => {
          const currentFavoriteButtonChargePercentage = getComputedStyle(FavoriteButton).getPropertyValue("--favorite_button_charge_percentage").trim();
          if (e.propertyName === "--favorite_button_charge_percentage" && currentFavoriteButtonChargePercentage === "100%") {
            if (Player.NowPlaying != null) {
                Player.Favorite(Player.NowPlaying);           
            }
            FavoriteButtonStopCharging();
            FavoriteButtonText.textContent = "Done";
            setTimeout(() => { FavoriteButtonText.textContent = FavoriteButtonOriginalText; }, 1000);
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
