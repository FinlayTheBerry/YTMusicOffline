"use strict";

(() => {
    const SwipeLib = {};

    SwipeLib.OnSwipe = (element, onSwipeRight, onSwipeLeft, onClick) => {
        let isDragging = false;
        let startX = 0;
        let currentX = 0;
        const threshold_min = 10;
        const threshold_max = 300;

        const getX = (e) => e.clientX; // Pointer events use clientX directly

        const start = (e) => {
            // Stop parent handlers (like onclick) from interfering
            e.stopPropagation();
            
            // Lock the pointer to this element so dragging doesn't break if mouse leaves bounds
            element.setPointerCapture(e.pointerId);

            isDragging = true;
            startX = getX(e);
            element.style.transition = 'none';
            element.style.cursor = 'grabbing';
        };

        const move = (e) => {
            if (!isDragging) return;

            const deltaX = getX(e) - startX;
            currentX = deltaX; // We use deltaX directly for a "fresh" drag feel
            
            if (currentX >= threshold_min) {
                element.style.transform = `translate(${currentX}px, 0px)`;
            }
        };

        const end = (e) => {
            if (!isDragging) return;
            isDragging = false;
            element.releasePointerCapture(e.pointerId);

            element.style.cursor = 'grab';
            // Enable the "Spring" animation
            element.style.transition = 'transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)';

            if (Math.abs(currentX) < threshold_min) {
                if (onClick) onClick();
            } 
            else if (currentX > threshold_max) {
                if (onSwipeRight) onSwipeRight();
            } 
            else if (currentX < -threshold_max) {
                if (onSwipeLeft) onSwipeLeft();
            } 
            element.style.transform = `translate(0px, 0px)`;
            currentX = 0;
        };

        // Pointer Events handle both Touch and Mouse seamlessly
        element.addEventListener('pointerdown', start);
        element.addEventListener('pointermove', move);
        element.addEventListener('pointerup', end);
        element.addEventListener('pointercancel', end); // Handle interrupted gestures (e.g. system alerts)
    };

    globalThis.SwipeLib = SwipeLib;
})();