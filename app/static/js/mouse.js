/**
 * Behavioural Mouse Movement Dynamics Capture Module
 * 
 * PRIVACY BY DESIGN:
 * This script measures ONLY mouse movement kinetics (velocity, acceleration,
 * path curvature, jitter, and pause patterns).
 * Raw trajectory coordinates (x, y, t) are kept TEMPORARILY in browser memory
 * only during feature extraction and are NEVER sent or persisted in raw form.
 */

(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', () => {
        const loginForm = document.getElementById('login-form');
        if (!loginForm) {
            return;
        }

        // In-memory trajectory buffer (TEMPORARY - cleared on submit)
        let trajectoryPoints = []; // Array of { x, y, t }
        const MAX_POINTS = 1000;
        const MIN_TIME_DELTA_MS = 4; // Ignore sub-4ms duplicate triggers
        const PAUSE_DISTANCE_THRESHOLD_PX = 2.0;
        const PAUSE_DURATION_THRESHOLD_MS = 100;

        /**
         * Mousemove event listener.
         */
        document.addEventListener('mousemove', (e) => {
            const now = performance.now();

            if (trajectoryPoints.length > 0) {
                const last = trajectoryPoints[trajectoryPoints.length - 1];
                // Ignore identical coordinates or excessively high frequency triggers
                if (last.x === e.clientX && last.y === e.clientY) {
                    return;
                }
                if (now - last.t < MIN_TIME_DELTA_MS) {
                    return;
                }
            }

            trajectoryPoints.push({
                x: e.clientX,
                y: e.clientY,
                t: now
            });

            // Prevent memory growth
            if (trajectoryPoints.length > MAX_POINTS) {
                trajectoryPoints.shift();
            }
        });

        function calcMean(arr) {
            if (arr.length === 0) return 0.0;
            return arr.reduce((acc, val) => acc + val, 0) / arr.length;
        }

        function calcStd(arr, mean) {
            if (arr.length <= 1) return 0.0;
            const variance = arr.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / arr.length;
            return Math.sqrt(variance);
        }

        /**
         * Normalizes angle difference to [0, Math.PI].
         */
        function normalizeAngle(angle) {
            while (angle > Math.PI) angle -= 2 * Math.PI;
            while (angle < -Math.PI) angle += 2 * Math.PI;
            return Math.abs(angle);
        }

        /**
         * Computes aggregate mouse movement features from in-memory trajectory points.
         */
        function extractMouseFeatures() {
            if (trajectoryPoints.length < 3) {
                return { sample_available: false };
            }

            const pts = trajectoryPoints;
            const distances = [];
            const velocities = [];
            const accelerations = [];
            const curvatures = [];
            const pauses = [];

            let totalPathLength = 0;
            let currentPauseDuration = 0;

            // 1. Calculate Distances and Velocities
            for (let i = 0; i < pts.length - 1; i++) {
                const dx = pts[i + 1].x - pts[i].x;
                const dy = pts[i + 1].y - pts[i].y;
                const dt_ms = pts[i + 1].t - pts[i].t;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dt_ms <= 0) continue;

                distances.push(dist);
                totalPathLength += dist;

                const dt_sec = dt_ms / 1000.0;
                const vel = dist / dt_sec; // px / sec
                velocities.push(vel);

                // Pause Detection: Movement < 2px over >= 100ms
                if (dist < PAUSE_DISTANCE_THRESHOLD_PX) {
                    currentPauseDuration += dt_ms;
                } else {
                    if (currentPauseDuration >= PAUSE_DURATION_THRESHOLD_MS) {
                        pauses.push(currentPauseDuration);
                    }
                    currentPauseDuration = 0;
                }
            }

            if (currentPauseDuration >= PAUSE_DURATION_THRESHOLD_MS) {
                pauses.push(currentPauseDuration);
            }

            if (velocities.length === 0) {
                return { sample_available: false };
            }

            // 2. Calculate Accelerations
            for (let i = 0; i < velocities.length - 1; i++) {
                const dv = Math.abs(velocities[i + 1] - velocities[i]);
                const dt_ms = pts[i + 2].t - pts[i + 1].t;
                if (dt_ms > 0) {
                    const dt_sec = dt_ms / 1000.0;
                    accelerations.push(dv / dt_sec); // px / sec^2
                }
            }

            // 3. Calculate Curvature (Direction Changes) and Jitter
            let totalDirectionChange = 0;
            let jitterSum = 0;

            for (let i = 0; i < pts.length - 2; i++) {
                const v1x = pts[i + 1].x - pts[i].x;
                const v1y = pts[i + 1].y - pts[i].y;
                const v2x = pts[i + 2].x - pts[i + 1].x;
                const v2y = pts[i + 2].y - pts[i + 1].y;

                const angle1 = Math.atan2(v1y, v1x);
                const angle2 = Math.atan2(v2y, v2x);
                const dAngle = normalizeAngle(angle2 - angle1);

                curvatures.push(dAngle);
                totalDirectionChange += dAngle;

                const segDist = Math.sqrt(v1x * v1x + v1y * v1y);
                jitterSum += dAngle / (segDist + 1.0);
            }

            // Feature Aggregation
            const avgVel = calcMean(velocities);
            const stdVel = calcStd(velocities, avgVel);
            const minVel = Math.min(...velocities);
            const maxVel = Math.max(...velocities);

            const avgAccel = accelerations.length > 0 ? calcMean(accelerations) : 0.0;
            const stdAccel = accelerations.length > 0 ? calcStd(accelerations, avgAccel) : 0.0;

            const avgCurv = curvatures.length > 0 ? calcMean(curvatures) : 0.0;
            const stdCurv = curvatures.length > 0 ? calcStd(curvatures, avgCurv) : 0.0;

            const jitterScore = curvatures.length > 0 ? (jitterSum / curvatures.length) : 0.0;

            const pauseCount = pauses.length;
            const avgPause = pauseCount > 0 ? calcMean(pauses) : 0.0;
            const maxPause = pauseCount > 0 ? Math.max(...pauses) : 0.0;
            const totalPause = pauses.reduce((acc, val) => acc + val, 0.0);

            const trackingDuration = pts[pts.length - 1].t - pts[0].t;

            return {
                avg_velocity: Number(avgVel.toFixed(2)),
                std_velocity: Number(stdVel.toFixed(2)),
                min_velocity: Number(minVel.toFixed(2)),
                max_velocity: Number(maxVel.toFixed(2)),

                avg_acceleration: Number(avgAccel.toFixed(2)),
                std_acceleration: Number(stdAccel.toFixed(2)),

                avg_curvature: Number(avgCurv.toFixed(4)),
                std_curvature: Number(stdCurv.toFixed(4)),
                total_direction_change: Number(totalDirectionChange.toFixed(4)),

                jitter_score: Number(jitterScore.toFixed(4)),

                pause_count: pauseCount,
                avg_pause_duration: Number(avgPause.toFixed(2)),
                max_pause_duration: Number(maxPause.toFixed(2)),
                total_pause_duration: Number(totalPause.toFixed(2)),

                total_path_length: Number(totalPathLength.toFixed(2)),
                tracking_duration: Number(trackingDuration.toFixed(2)),
                point_count: pts.length
            };
        }

        // Attach mouse feature extraction to login form submission
        loginForm.addEventListener('submit', () => {
            const features = extractMouseFeatures();

            if (features) {
                let hiddenInput = document.getElementById('mouse_data');
                if (!hiddenInput) {
                    hiddenInput = document.createElement('input');
                    hiddenInput.type = 'hidden';
                    hiddenInput.id = 'mouse_data';
                    hiddenInput.name = 'mouse_data';
                    loginForm.appendChild(hiddenInput);
                }
                hiddenInput.value = JSON.stringify(features);
            }

            // Immediately clear in-memory trajectory buffer
            trajectoryPoints = [];
        });
    });
})();
