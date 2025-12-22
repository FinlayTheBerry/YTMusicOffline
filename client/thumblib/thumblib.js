// Approved 03/20/2025
"use strict";

(() => {
    const ThumbLib = {};

    let InTransaction = false;
    ThumbLib.StartTransaction = () => {
        if (InTransaction) {
            throw new Error("Already in a transaction. Please call EndTransaction.");
        }
        InTransaction = true;
    };
    ThumbLib.EndTransaction = () => {
        if (!InTransaction) {
            throw new Error("Not in a transaction. Please call StartTransaction.");
        }
        InTransaction = false;
        Update();
    };

    let ConcurrencyLimit = 5;
    ThumbLib.SetConcurrencyLimit = (concurrencyLimit) => {
        if (!Number.isInteger(concurrencyLimit) || concurrencyLimit <= 0) {
            throw new Error("concurrencyLimit must an integer greater than 0.");
        }
        ConcurrencyLimit = concurrencyLimit;
        Update();
    };

    let PreloadLimit = 10; // 0 = unlimitted
    ThumbLib.SetPreloadLimit = (value) => {
        if (!Number.isInteger(value) || value < 0) {
            throw new Error("PreloadLimit must be a positive integer great than 0 or -1.");
        }
        PreloadLimit = value;
        if (!InTransaction) {
            Update();
        }
    };

    let Elements = [];
    ThumbLib.SetElements = (elements) => {
        if (!Array.isArray(elements)) {
            throw new Error("Elements must be a valid array.");
        }
        for (let element of elements) {
            if (!(element instanceof HTMLImageElement)) {
                throw new Error("Elements must contain only HTMLImageElements.");
            }
        }
        Elements = elements.slice();
        Update();
    };

    let Dataset = [];
    ThumbLib.SetDataset = (dataset) => {
        if (!Array.isArray(dataset)) {
            throw new Error("Dataset must be a valid array.");
        }
        for (let imageUrl of dataset) {
            if (typeof imageUrl != "string") {
                throw new Error("Dataset must contain only string urls.");
            }
        }
        Dataset = dataset.slice();
        Update();
    };

    let StartIndex = 0;
    ThumbLib.SetStartIndex = (startIndex) => {
        if (!Number.isInteger(startIndex) || startIndex < 0) {
            throw new Error("StartIndex must a positive integer or 0.");
        }
        StartIndex = startIndex;
        Update();
    };

    //ThumbLib.BlankImageSrc = "data:image/gif;base64,R0lGODlhAQABAPAAAAAAAP///yH5BAUAAAAALAAAAAABAAEAAAICRAEAOw==";

    let ImageCache = new Map();
    let InProgressRequests = new Set();
    const HelperOnFetchComplete = (url) => {
        InProgressRequests.delete(url);
        if (!InTransaction) {
            Update();
        }
    };
    const HelperFetch = (url) => {
        if (url == undefined) {
            return;
        }
        if (ImageCache.has(url)) {
            return;
        }
        if (InProgressRequests.has(url)) {
            return;
        }
        if (InProgressRequests.size >= ConcurrencyLimit) {
            return;
        }

        InProgressRequests.add(url);
        fetch(url, {
            method: "GET",
            headers: { Priority: "normal" }
        }).then((response) => {
            response.blob().then((image) => {
                ImageCache.set(url, URL.createObjectURL(image));
                HelperOnFetchComplete(url);
            }).catch((error) => {
                console.error(error);
                HelperOnFetchComplete(url);
            });
        }).catch((error) => {
            console.error(error);
            HelperOnFetchComplete(url);
        });
    };
    const Update = () => {
        if (InTransaction) {
            return;
        }

        for (let i = 0; i < Elements.length; i++) {
            const element = Elements[i];
            const url = Dataset[StartIndex + i];

            if (ImageCache.has(url)) {
                const src = ImageCache.get(url);
                if (element.src != src) {
                    element.src = src;
                }
                if (element.style.visibility != '' && element.style.visibility != undefined) {
                    element.style.removeProperty("visibility");
                }
            } else {
                if (element.style.visibility != "hidden") {
                    element.style.visibility = "hidden";
                }
            }

            HelperFetch(url);
        }

        for (let i = 0; i < PreloadLimit || PreloadLimit == -1; i++) {
            const urlBelow = Dataset[StartIndex + Elements.length + i];
            HelperFetch(urlBelow);

            const urlAbove = Dataset[StartIndex - i];
            HelperFetch(urlAbove);

            if (InProgressRequests.size >= ConcurrencyLimit || (urlBelow == undefined && urlAbove == undefined)) {
                break;
            }
        }
    };

    globalThis.ThumbLib = ThumbLib;
})();