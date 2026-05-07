"use strict";

(() => {
    const SwipeLib = {};

    SwipeLib.OnSwipe = (element, onSwipe, onClick) => {
        let state = 0; // 0 waiting for touch 1 unsure 2 swiping
        let startY = 0;
        let startX = 0;
        const deadzone = 15;
        const threshold_max = 225;

        const start = (e) => {
            e.stopPropagation();
            element.setPointerCapture(e.pointerId);
            state = 1;
            startX = e.clientX;
            startY = e.clientY;
            element.style.cursor = 'grabbing';
        };

        const move = (e) => {
            if (state == 0 || state == 3) {
                return;
            }
            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;
            if (state == 1) {
                if (deltaY > deadzone || deltaY < -deadzone || deltaX < -deadzone) {
                    cancel(e);
                } else if (deltaX > deadzone) {
                    state = 2;
                }
            }
            if (state == 2) {
                if (deltaX > threshold_max) {
                    element.style.transform = `translate(${threshold_max}px, 0px)`;
                    if ("vibrate" in navigator) {
                        navigator.vibrate(150);
                    }
                    onSwipe();
                    cancel(e);
                } else {
                    const clamped = Math.min(Math.max(deltaX, 0), threshold_max);
                    element.style.transform = `translate(${clamped}px, 0px)`;
                }
            }
        };

        const end = (e) => {
            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;
            if (state == 1) {
                onClick();
            }
            cancel(e);
        };

        const cancel = (e) => {
            element.releasePointerCapture(e.pointerId);
            element.style.cursor = 'grab';
            element.style.transform = `translate(0px, 0px)`;
            state = 0;
        };

        element.addEventListener('pointerdown', start);
        element.addEventListener('pointermove', move);
        element.addEventListener('pointerup', end);
        element.addEventListener('pointercancel', cancel);
    };

    globalThis.SwipeLib = SwipeLib;
})();