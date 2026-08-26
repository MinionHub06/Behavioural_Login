/**
 * Behavioural Keystroke Dynamics Capture Module
 * 
 * PRIVACY BY DESIGN:
 * This script measures ONLY typing timing dynamics (dwell times, flight times,
 * typing speed, and speed variance).
 * It NEVER records, logs, stores, or transmits passwords, key values (e.g. event.key),
 * key codes (e.g. event.code), or character identities.
 */

(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', () => {
        const passwordInput = document.getElementById('password');
        const loginForm = document.getElementById('login-form');
        const statusBadge = document.getElementById('keystroke-status-badge');

        if (!passwordInput || !loginForm) {
            return;
        }

        // Keystroke state storage (Timestamps ONLY - NO key values or codes)
        let activeKeypresses = []; // Array of active keydown timestamps: [{ id, downTime }]
        let keypressCounter = 0;
        let dwellTimes = [];       // Array of float durations in ms
        let flightTimes = [];      // Array of float durations in ms
        let lastKeyUpTime = null;
        let firstKeyDownTime = null;
        let lastKeyUpOrDownTime = null;

        /**
         * Reset internal timing state completely.
         */
        function resetState() {
            activeKeypresses = [];
            keypressCounter = 0;
            dwellTimes = [];
            flightTimes = [];
            lastKeyUpTime = null;
            firstKeyDownTime = null;
            lastKeyUpOrDownTime = null;
        }

        // 1. Keydown Event Handler
        passwordInput.addEventListener('keydown', (e) => {
            // Ignore auto-repeat keydown events
            if (e.repeat) return;

            const now = performance.now();

            if (firstKeyDownTime === null) {
                firstKeyDownTime = now;
            }

            // Calculate flight time from previous keyup if available
            if (lastKeyUpTime !== null) {
                const flight = now - lastKeyUpTime;
                // Keep flight time if within realistic range (e.g., < 10 seconds)
                if (flight >= 0 && flight <= 10000) {
                    flightTimes.push(flight);
                }
            }

            keypressCounter++;
            activeKeypresses.push({
                id: keypressCounter,
                downTime: now
            });

            lastKeyUpOrDownTime = now;
        });

        // 2. Keyup Event Handler
        passwordInput.addEventListener('keyup', (e) => {
            const now = performance.now();
            lastKeyUpTime = now;
            lastKeyUpOrDownTime = now;

            // Match with oldest unresolved keydown (FIFO order)
            if (activeKeypresses.length > 0) {
                const kp = activeKeypresses.shift();
                const dwell = now - kp.downTime;
                if (dwell >= 0 && dwell <= 10000) {
                    dwellTimes.push(dwell);
                }
            }
        });

        // Clear timing state if input is emptied (e.g. user selects all and deletes)
        passwordInput.addEventListener('input', () => {
            if (passwordInput.value.length === 0) {
                resetState();
            }
        });

        /**
         * Computes arithmetic mean of a number array.
         */
        function calcMean(arr) {
            if (arr.length === 0) return 0.0;
            const sum = arr.reduce((acc, val) => acc + val, 0);
            return sum / arr.length;
        }

        /**
         * Computes population standard deviation of a number array.
         */
        function calcStd(arr, mean) {
            if (arr.length <= 1) return 0.0;
            const variance = arr.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / arr.length;
            return Math.sqrt(variance);
        }

        /**
         * Computes variance of inter-keystroke intervals (typing speed variance).
         * Divides interval sequence into sub-intervals and measures variance across segments.
         */
        function calcSpeedVariance(dwells, flights) {
            const combined = [...dwells, ...flights];
            if (combined.length <= 1) return 0.0;
            const mean = calcMean(combined);
            return combined.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / combined.length;
        }

        /**
         * Extracts aggregate non-sensitive feature payload.
         */
        function extractFeatures() {
            if (dwellTimes.length === 0) {
                return null;
            }

            const avgDwell = calcMean(dwellTimes);
            const stdDwell = calcStd(dwellTimes, avgDwell);
            const minDwell = Math.min(...dwellTimes);
            const maxDwell = Math.max(...dwellTimes);

            const avgFlight = flightTimes.length > 0 ? calcMean(flightTimes) : 0.0;
            const stdFlight = flightTimes.length > 0 ? calcStd(flightTimes, avgFlight) : 0.0;
            const minFlight = flightTimes.length > 0 ? Math.min(...flightTimes) : 0.0;
            const maxFlight = flightTimes.length > 0 ? Math.max(...flightTimes) : 0.0;

            const totalDuration = lastKeyUpTime && firstKeyDownTime ? (lastKeyUpTime - firstKeyDownTime) : 0.0;
            const typingSpeed = totalDuration > 0 ? (dwellTimes.length / (totalDuration / 1000.0)) : 0.0; // keys per sec
            const speedVariance = calcSpeedVariance(dwellTimes, flightTimes);

            return {
                avg_dwell_time: Number(avgDwell.toFixed(2)),
                std_dwell_time: Number(stdDwell.toFixed(2)),
                min_dwell_time: Number(minDwell.toFixed(2)),
                max_dwell_time: Number(maxDwell.toFixed(2)),
                avg_flight_time: Number(avgFlight.toFixed(2)),
                std_flight_time: Number(stdFlight.toFixed(2)),
                min_flight_time: Number(minFlight.toFixed(2)),
                max_flight_time: Number(maxFlight.toFixed(2)),
                total_typing_duration: Number(totalDuration.toFixed(2)),
                typing_speed: Number(typingSpeed.toFixed(2)),
                typing_speed_variance: Number(speedVariance.toFixed(2)),
                sample_count: dwellTimes.length
            };
        }

        // Attach feature extraction to form submission
        loginForm.addEventListener('submit', () => {
            const features = extractFeatures();

            if (features) {
                // Attach hidden form input with JSON feature string
                let hiddenInput = document.getElementById('keystroke_data');
                if (!hiddenInput) {
                    hiddenInput = document.createElement('input');
                    hiddenInput.type = 'hidden';
                    hiddenInput.id = 'keystroke_data';
                    hiddenInput.name = 'keystroke_data';
                    loginForm.appendChild(hiddenInput);
                }
                hiddenInput.value = JSON.stringify(features);
            }

            // Immediately clear raw local timing buffers
            resetState();
        });

        // Activate status badge UI indicator
        if (statusBadge) {
            statusBadge.style.display = 'inline-flex';
        }
    });
})();
