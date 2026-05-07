"use strict";

(() => {
    const Gui = {};

    VSLib.SetElementsPerScreen(12);

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
            PlayerLoopButtonTextElement.textContent = "🔁";
        } else {
            PlayerLoopButtonTextElement.textContent = "🔄";
        }

        if (Player.ShowingQueue) {
            PlayerShowQueueButtonTextElement.textContent = "Show All";
        } else {
            PlayerShowQueueButtonTextElement.textContent = "Show Queue";
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
    let PlayerLoopButtonTextElement = null;
    let PlayerShowQueueButtonTextElement = null;
    let SearchBarElement = null;
    let PlayerFavoriteButton = null;
    let PlayerFavoriteButtonText = null;
    let ElementRefrencesNull = true;
    const SetElementRefrences = () => {
        PlayerThumbnailElement = document.querySelector(".player_thumbnail");
        PlayerTextElement = document.querySelector(".player_text");
        PlayerLoopButtonTextElement = document.querySelector(".player_loop_button_text");
        PlayerShowQueueButtonTextElement = document.querySelector(".player_show_queue_button_text");
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
        PlayerFavoriteButton = document.querySelector(".player_favorite_button");
        PlayerFavoriteButtonText = document.querySelector(".player_favorite_button_text");
        ElementRefrencesNull = false;

        const PlayerFavoriteButtonOriginalText = PlayerFavoriteButtonText.textContent;
        const PlayerFavoriteButtonStartCharging = () => { PlayerFavoriteButton.classList.add("charging") };
        const PlayerFavoriteButtonStopCharging = () => { PlayerFavoriteButton.classList.remove("charging") };
        PlayerFavoriteButton.addEventListener("pointerdown", PlayerFavoriteButtonStartCharging);
        PlayerFavoriteButton.addEventListener("pointerup", PlayerFavoriteButtonStopCharging);
        PlayerFavoriteButton.addEventListener("pointerleave", PlayerFavoriteButtonStopCharging);
        PlayerFavoriteButton.addEventListener("pointercancel", PlayerFavoriteButtonStopCharging);
        PlayerFavoriteButton.addEventListener("transitionend", (e) => {
          const currentPlayerFavoriteButtonChargePercentage = getComputedStyle(PlayerFavoriteButton).getPropertyValue("--favorite_button_charge_percentage").trim();
          if (e.propertyName === "--favorite_button_charge_percentage" && currentPlayerFavoriteButtonChargePercentage === "100%") {
            if (Player.NowPlaying != null) {
                Player.Favorite(Player.NowPlaying);           
            }
            PlayerFavoriteButtonStopCharging();
            PlayerFavoriteButtonText.textContent = "Done!";
            if ("vibrate" in navigator) {
                navigator.vibrate(200);
            }
            setTimeout(() => { PlayerFavoriteButtonText.textContent = PlayerFavoriteButtonOriginalText; }, 1000);
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




















// Select all containers
const containers = document.querySelectorAll('.element_container');

containers.forEach(container => {
    // Each container needs its own local state
    let startX = 0;
    let currentX = 0;
    let totalOffset = 0;

    container.addEventListener('touchstart', (e) => {
        startX = e.touches[0].clientX;
        container.style.transition = 'none';
    }, { passive: true });

    container.addEventListener('touchmove', (e) => {
        const touchX = e.touches[0].clientX;
        const deltaX = touchX - startX;
        
        // Calculate position based on THIS element's previous offset
        currentX = totalOffset + deltaX;

        // Apply translation only to the element being touched
        container.style.transform = `translateX(${currentX}px)`;
    });

    container.addEventListener('touchend', () => {
        // Save the final position for THIS specific element
        totalOffset = currentX;
        container.style.transition = 'transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
    });
});