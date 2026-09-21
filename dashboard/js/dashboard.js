/*
============================================================
BELTSENTINEL AI
MODULE 7.9

COMPLETE DASHBOARD CONTROLLER

Pages:
    Dashboard
    Live Feed
    Analytics
    Alerts
    Reports
    Settings

Connected APIs:
    /api/status
    /api/telemetry
    /api/telemetry/history
    /api/risk
    /api/detection
    /api/joints
    /api/joints/current
    /api/joints/calibration
    /api/alerts
    /api/health

Phase 2 Camera APIs:
    /api/camera/status
    /api/camera/feed

Current ESP32 telemetry:
    encoder_pulses
    vibration_events_per_sec
    acoustic_events_per_sec
    acoustic_raw
    temperature
    humidity
    current_amps
    motor_running
    motor_pwm

============================================================
*/


// ============================================================
// CONFIGURATION
// ============================================================

const API_BASE = "";

const UPDATE_INTERVAL = 1000;

const CAMERA_FEED_URL =
    `${API_BASE}/api/camera/feed`;


// ============================================================
// HTTP ALERT FALLBACK
//
// Web Push requires HTTPS on mobile browsers. When this dashboard
// is opened over normal HTTP, keep the existing push system intact
// but provide an in-page/mobile-friendly alert fallback while the
// dashboard tab is open.
// ============================================================

let httpAlertFallbackInitialized = false;
let httpAlertFallbackLastSignature = "";
let httpAlertFallbackFirstRun = true;


function ensureHttpAlertToastStyles() {

    if (document.getElementById("beltsentinel-http-alert-style")) {
        return;
    }

    const style = document.createElement("style");

    style.id = "beltsentinel-http-alert-style";

    style.textContent = `
        #beltsentinel-http-alert-toast {
            position: fixed;
            right: 22px;
            bottom: 22px;
            z-index: 99999;
            width: min(390px, calc(100vw - 44px));
            padding: 16px 18px;
            border: 1px solid rgba(255,255,255,.18);
            background: rgba(18, 23, 26, .97);
            box-shadow: 0 12px 34px rgba(0,0,0,.45);
            backdrop-filter: blur(8px);
            font-family: inherit;
            color: #e8edef;
            opacity: 0;
            transform: translateY(16px);
            pointer-events: none;
            transition: opacity .2s ease, transform .2s ease;
        }
        #beltsentinel-http-alert-toast.show {
            opacity: 1;
            transform: translateY(0);
        }
        #beltsentinel-http-alert-toast .bs-http-alert-title {
            font-size: 11px;
            font-weight: 800;
            letter-spacing: .12em;
            margin-bottom: 7px;
        }
        #beltsentinel-http-alert-toast .bs-http-alert-message {
            font-size: 13px;
            line-height: 1.45;
            color: #c5ced1;
        }
        #beltsentinel-http-alert-toast .bs-http-alert-meta {
            margin-top: 8px;
            font-size: 10px;
            color: #879398;
            letter-spacing: .05em;
        }
    `;

    document.head.appendChild(style);
}


function showHttpAlertToast(alertData) {

    ensureHttpAlertToastStyles();

    let toast = document.getElementById(
        "beltsentinel-http-alert-toast"
    );

    if (!toast) {
        toast = document.createElement("div");
        toast.id = "beltsentinel-http-alert-toast";
        document.body.appendChild(toast);
    }

    const severity = String(
        alertData?.severity || "WARNING"
    ).toUpperCase();

    const message = String(
        alertData?.message || "Conveyor alert detected."
    );

    const joint = String(
        alertData?.joint || "System"
    );

    toast.innerHTML = `
        <div class="bs-http-alert-title">
            BELTSENTINEL AI — ${severity}
        </div>
        <div class="bs-http-alert-message">
            ${escapeHtmlForDashboard(message)}
        </div>
        <div class="bs-http-alert-meta">
            ${escapeHtmlForDashboard(joint)} • Open Alerts for details
        </div>
    `;

    toast.classList.add("show");

    if (
        typeof navigator.vibrate === "function"
    ) {
        try {
            navigator.vibrate(
                severity === "CRITICAL"
                    ? [180, 80, 180]
                    : [120]
            );
        } catch (_) {
            // Vibration is optional.
        }
    }

    document.title = `⚠ ${severity} — BELTSENTINEL AI`;

    window.clearTimeout(
        showHttpAlertToast._timer
    );

    showHttpAlertToast._timer = window.setTimeout(
        () => {
            toast.classList.remove("show");
            document.title = "BELTSENTINEL AI";
        },
        7000
    );
}


function escapeHtmlForDashboard(value) {

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


async function pollHttpAlertFallback() {

    try {

        const response = await fetch(
            `${API_BASE}/api/alerts?limit=1`,
            { cache: "no-store" }
        );

        if (!response.ok) {
            return;
        }

        const data = await response.json();

        if (!Array.isArray(data) || data.length === 0) {
            return;
        }

        const latest = data[0] || {};

        const signature = JSON.stringify({
            id: latest.id ?? null,
            timestamp: latest.timestamp ?? latest.created_at ?? null,
            severity: latest.severity ?? null,
            alert_type: latest.alert_type ?? latest.type ?? null,
            message: latest.message ?? null,
            joint: latest.joint ?? null
        });

        if (httpAlertFallbackFirstRun) {
            httpAlertFallbackLastSignature = signature;
            httpAlertFallbackFirstRun = false;
            return;
        }

        if (
            signature &&
            signature !== httpAlertFallbackLastSignature
        ) {
            httpAlertFallbackLastSignature = signature;
            showHttpAlertToast(latest);
        }

    } catch (error) {
        // Keep the dashboard running if the backend is temporarily unavailable.
    }
}


function setupHttpAlertFallback() {

    if (httpAlertFallbackInitialized) {
        return;
    }

    httpAlertFallbackInitialized = true;

    // Web Push remains the primary mechanism on HTTPS.
    // HTTP uses the visible in-dashboard fallback only.
    if (window.isSecureContext) {
        return;
    }

    pollHttpAlertFallback();

    window.setInterval(
        pollHttpAlertFallback,
        2000
    );
}


// ============================================================
// WEB PUSH NOTIFICATIONS
// ============================================================

let pushRegistration = null;
let pushSubscription = null;
let pushPublicKey = "";


function setPushButtonState(state, label) {

    const button = document.getElementById(
        "push-notification-button"
    );

    if (!button) return;

    button.textContent = label;
    button.classList.toggle(
        "is-enabled",
        state === "enabled"
    );
    button.classList.toggle(
        "is-disabled",
        state === "disabled"
    );

}


function urlBase64ToUint8Array(base64String) {

    const padding = "=".repeat(
        (4 - (base64String.length % 4)) % 4
    );

    const base64 =
        (base64String + padding)
            .replace(/-/g, "+")
            .replace(/_/g, "/");

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(
        rawData.length
    );

    for (let i = 0; i < rawData.length; i += 1) {
        outputArray[i] = rawData.charCodeAt(i);
    }

    return outputArray;
}


async function registerPushServiceWorker() {

    if (!("serviceWorker" in navigator)) {
        throw new Error(
            "This browser does not support service workers."
        );
    }

    if (!window.isSecureContext) {
        throw new Error(
            "Push notifications require HTTPS on a phone. Use an HTTPS address for the mobile dashboard."
        );
    }

    pushRegistration =
        await navigator.serviceWorker.register(
            "/sw.js",
            { scope: "/" }
        );

    await navigator.serviceWorker.ready;

    return pushRegistration;
}


async function getPushPublicKey() {

    const response = await fetch(
        "/api/push/public-key",
        { cache: "no-store" }
    );

    const data = await response.json();

    if (!data.public_key) {
        throw new Error(
            "Web Push is not configured on the BELTSENTINEL backend."
        );
    }

    pushPublicKey = data.public_key;
    return pushPublicKey;
}


async function enablePushNotifications() {

    if (!("Notification" in window)) {
        throw new Error(
            "This browser does not support notifications."
        );
    }

    setPushButtonState(
        "disabled",
        "SETTING UP..."
    );

    const permission =
        await Notification.requestPermission();

    if (permission !== "granted") {
        setPushButtonState(
            "disabled",
            "ENABLE ALERTS"
        );
        throw new Error(
            "Notification permission was not granted."
        );
    }

    await registerPushServiceWorker();
    await getPushPublicKey();

    pushSubscription =
        await pushRegistration.pushManager.getSubscription();

    if (!pushSubscription) {
        pushSubscription =
            await pushRegistration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey:
                    urlBase64ToUint8Array(pushPublicKey)
            });
    }

    const response = await fetch(
        "/api/push/subscribe",
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(
                pushSubscription.toJSON()
            )
        }
    );

    const data = await response.json();

    if (!response.ok || !data.success) {
        throw new Error(
            data.message ||
            "The backend rejected the push subscription."
        );
    }

    localStorage.setItem(
        "beltsentinel_push_enabled",
        "1"
    );

    setPushButtonState(
        "enabled",
        "ALERTS ON"
    );

    return true;
}


async function disablePushNotifications() {

    if (!pushSubscription) {
        if (pushRegistration) {
            pushSubscription =
                await pushRegistration.pushManager.getSubscription();
        }
    }

    if (pushSubscription) {
        await fetch(
            "/api/push/unsubscribe",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    endpoint: pushSubscription.endpoint
                })
            }
        );

        await pushSubscription.unsubscribe();
        pushSubscription = null;
    }

    localStorage.removeItem(
        "beltsentinel_push_enabled"
    );

    setPushButtonState(
        "disabled",
        "ENABLE ALERTS"
    );
}


async function setupPushNotifications() {

    const button = document.getElementById(
        "push-notification-button"
    );

    if (!button) return;

    if (!("Notification" in window) || !("serviceWorker" in navigator)) {
        setPushButtonState(
            "disabled",
            "NO PUSH"
        );
        button.disabled = true;
        return;
    }

    button.addEventListener(
        "click",
        async () => {
            try {
                if (Notification.permission === "granted") {
                    await enablePushNotifications();
                } else {
                    await enablePushNotifications();
                }

                alert(
                    "BELTSENTINEL AI push notifications are enabled on this device."
                );
            } catch (error) {
                console.error(
                    "Push notification setup error:",
                    error
                );
                setPushButtonState(
                    "disabled",
                    "ENABLE ALERTS"
                );
                alert(
                    error.message ||
                    "Unable to enable push notifications."
                );
            }
        }
    );

    if (
        Notification.permission === "granted"
        &&
        localStorage.getItem(
            "beltsentinel_push_enabled"
        ) === "1"
    ) {
        try {
            await enablePushNotifications();
        } catch (error) {
            console.warn(
                "Push auto-registration skipped:",
                error
            );
        }
    }
}


// ============================================================
// PAGE CONFIG
// ============================================================

const pageConfig = {

    dashboard: {
        title: "Control Dashboard"
    },

    "live-feed": {
        title: "Live Camera Feed"
    },

    analytics: {
        title: "Analytics"
    },

    alerts: {
        title: "Alerts & Events"
    },

    reports: {
        title: "Monitoring Reports"
    },

    settings: {
        title: "Settings & System Health"
    }

};


// ============================================================
// GLOBAL STATE
// ============================================================

let latestTelemetry = {};

let latestRisk = {};

let latestDetection = {};

let latestJoints = {};

let latestCurrentJoint = {};

let latestAlerts = [];

let latestHealth = {};

let latestCalibration = {};

let latestCameraStatus = {};

let backendOnline = false;

let cameraOnline = false;

let cameraModelLoaded = false;


// ============================================================
// DOM HELPER
// ============================================================

function getElement(id) {

    return document.getElementById(id);

}


// ============================================================
// SAFE TEXT
// ============================================================

function setText(id, value) {

    const element = getElement(id);

    if (!element) {
        return;
    }

    element.textContent = value;

}


// ============================================================
// FETCH JSON
// ============================================================

async function fetchJSON(
    endpoint,
    options = {}
) {

    const response = await fetch(

        `${API_BASE}${endpoint}`,

        {
            cache: "no-store",
            ...options
        }

    );


    if (!response.ok) {

        throw new Error(
            `HTTP ${response.status}`
        );

    }


    return await response.json();

}


// ============================================================
// PAGE FROM HASH
// ============================================================

function getPageFromHash() {

    const page =
        window.location.hash.replace("#", "");


    if (pageConfig[page]) {

        return page;

    }


    return "dashboard";

}


// ============================================================
// SHOW PAGE
// ============================================================

function showPage(pageName) {

    if (!pageConfig[pageName]) {

        pageName = "dashboard";

    }


    document
        .querySelectorAll(".app-page")
        .forEach(page => {

            page.style.display = "none";

        });


    const selectedPage =
        getElement(
            `page-${pageName}`
        );


    if (selectedPage) {

        selectedPage.style.display = "";

    }


    document
        .querySelectorAll("[data-page]")
        .forEach(item => {

            item.classList.toggle(

                "active",

                item.dataset.page === pageName

            );

        });


    setText(

        "page-title",

        pageConfig[
            pageName
        ].title

    );


    updateSecondaryPages();

}


// ============================================================
// CLOCK
// ============================================================

function updateClock() {

    const now = new Date();


    setText(

        "local-time",

        now.toLocaleTimeString(

            [],

            {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit"
            }

        )

    );

}


// ============================================================
// DATE TIME
// ============================================================

function formatDateTime(value) {

    if (!value) {

        return "--";

    }


    const date = new Date(value);


    if (
        Number.isNaN(
            date.getTime()
        )
    ) {

        return value;

    }


    return date.toLocaleString();

}


// ============================================================
// BACKEND STATUS
// ============================================================

function updateBackendStatus(online) {

    backendOnline = online;


    document
        .querySelectorAll(
            ".system-status"
        )
        .forEach(element => {

            if (online) {

                element.textContent =
                    "ONLINE";

                element.classList.remove(
                    "offline"
                );

            } else {

                element.textContent =
                    "OFFLINE";

                element.classList.add(
                    "offline"
                );

            }

        });


    const dot =
        document.querySelector(
            ".connection-dot"
        );


    if (dot) {

        dot.style.background =
            online
                ? ""
                : "#ff5c65";

    }

}


// ============================================================
// TELEMETRY
// ============================================================

async function fetchTelemetry() {

    try {

        const data =
            await fetchJSON(
                "/api/telemetry"
            );


        latestTelemetry = data;


        updateTelemetry(
            data
        );


        return data;

    } catch (error) {

        console.error(
            "Telemetry error:",
            error
        );

        return null;

    }

}


// ============================================================
// UPDATE TELEMETRY
// ============================================================

function updateTelemetry(data) {

    if (!data) {

        return;

    }


    // --------------------------------------------------------
    // ENCODER
    // --------------------------------------------------------

    setText(

        "belt-speed",

        `${data.encoder_pulses ?? 0} pulses`

    );


    // --------------------------------------------------------
    // VIBRATION
    // --------------------------------------------------------

    const vibration =
        Number(
            data.vibration_events_per_sec ??
            data.vibration_pulses ??
            0
        );


    setText(
        "vibration",
        vibration
    );


    // --------------------------------------------------------
    // TEMPERATURE
    // --------------------------------------------------------

    setText(

        "temperature",

        `${Number(
            data.temperature ?? 0
        ).toFixed(1)} °C`

    );


    // --------------------------------------------------------
    // HUMIDITY
    // --------------------------------------------------------

    setText(

        "humidity",

        `${Number(
            data.humidity ?? 0
        ).toFixed(1)} %`

    );


    // --------------------------------------------------------
    // CURRENT
    //
    // ACS712 is currently not connected.
    // Therefore 0.00 A is expected.
    // --------------------------------------------------------

    setText(

        "current",

        `${Number(
            data.current_amps ?? 0
        ).toFixed(2)} A`

    );


    // --------------------------------------------------------
    // ACOUSTIC
    // --------------------------------------------------------

    const acousticEvents =
        Number(
            data.acoustic_events_per_sec ??
            data.acoustic_pulses ??
            0
        );


    setText(

        "acoustic",

        acousticEvents

    );


    // --------------------------------------------------------
    // MOTOR STATUS
    // --------------------------------------------------------

    const motorRunning =
        Boolean(
            data.motor_running
        );


    setText(

        "motor-status",

        motorRunning
            ? "RUNNING"
            : "STOPPED"

    );


    setText(

        "motor-pwm",

        data.motor_pwm ?? 0

    );


    // --------------------------------------------------------
    // LIVE PAGE
    // --------------------------------------------------------

    setText(

        "live-temperature",

        `${Number(
            data.temperature ?? 0
        ).toFixed(1)} °C`

    );


    setText(

        "live-humidity",

        `${Number(
            data.humidity ?? 0
        ).toFixed(1)} %`

    );


    setText(

        "live-vibration",

        vibration

    );


    setText(

        "live-acoustic",

        acousticEvents

    );


    setText(

        "live-current",

        `${Number(
            data.current_amps ?? 0
        ).toFixed(2)} A`

    );


    setText(

        "live-encoder-position",

        data.encoder_pulses ?? 0

    );


    // --------------------------------------------------------
    // LIVE MOTOR
    // --------------------------------------------------------

    setText(

        "live-motor-status",

        motorRunning
            ? "RUNNING"
            : "STOPPED"

    );


    setText(

        "live-motor-pwm",

        data.motor_pwm ?? 0

    );


    // --------------------------------------------------------
    // ANALYTICS
    // --------------------------------------------------------

    setText(

        "analytics-speed",

        `${data.encoder_pulses ?? 0} pulses`

    );


    setText(

        "analytics-vibration",

        vibration

    );


    setText(

        "analytics-temperature",

        `${Number(
            data.temperature ?? 0
        ).toFixed(1)} °C`

    );


    setText(

        "analytics-humidity",

        `${Number(
            data.humidity ?? 0
        ).toFixed(1)} %`

    );


    setText(

        "analytics-current",

        `${Number(
            data.current_amps ?? 0
        ).toFixed(2)} A`

    );


    setText(

        "analytics-acoustic",

        acousticEvents

    );

}


// ============================================================
// RISK
// ============================================================

async function fetchRisk() {

    try {

        const data =
            await fetchJSON(
                "/api/risk"
            );


        latestRisk = data;


        updateRisk(
            data
        );


        return data;

    } catch (error) {

        console.error(
            "Risk error:",
            error
        );

        return null;

    }

}


// ============================================================
// UPDATE RISK
// ============================================================

function updateRisk(data) {

    if (!data) {

        return;

    }


    const level =
        data.risk_level || "NORMAL";


    const score =
        Number(
            data.risk_score || 0
        );


    setText(
        "risk-level",
        level
    );


    setText(
        "analytics-risk",
        level
    );


    setText(
        "analytics-risk-score",
        `${score} / 100`
    );


    setText(

        "ai-message",

        data.message ||
        "System operating normally."

    );


    const fill =
        getElement(
            "risk-progress-fill"
        );


    if (fill) {

        fill.style.width =
            `${Math.max(
                0,
                Math.min(
                    score,
                    100
                )
            )}%`;

    }


    const reasons =
        getElement(
            "analytics-reasons"
        );


    if (!reasons) {

        return;

    }


    if (

        Array.isArray(
            data.reasons
        )

        &&

        data.reasons.length > 0

    ) {

        reasons.innerHTML =

            data.reasons

                .map(

                    reason =>

                        `<div class="reason">
                            ${escapeHTML(reason)}
                        </div>`

                )

                .join("");

    } else {

        reasons.innerHTML = `

            <div class="empty-state">

                No abnormal conditions detected.

            </div>

        `;

    }

}


// ============================================================
// DETECTION
// ============================================================

async function fetchDetection() {

    try {

        const data =
            await fetchJSON(
                "/api/detection"
            );


        latestDetection = data;


        updateDetection(
            data
        );


        return data;

    } catch (error) {

        console.error(
            "Detection error:",
            error
        );

        return null;

    }

}


// ============================================================
// UPDATE DETECTION
// ============================================================

function updateDetection(data) {

    if (!data) {

        return;

    }


    const detection =
        data.detection ||
        "NORMAL";


    const confidence =
        Number(
            data.confidence || 0
        );


    const joint =
        data.joint ||
        "None";


    const status =
        data.status ||
        "NORMAL";


    setText(
        "detection-type",
        detection
    );


    setText(
        "confidence",
        `${confidence.toFixed(1)}%`
    );


    setText(
        "joint-location",
        joint
    );


    setText(
        "detection-time",
        formatDateTime(
            data.timestamp
        )
    );


    setText(
        "ai-status",
        status
    );


    setText(
        "live-detection-type",
        detection
    );


    setText(
        "live-confidence",
        `${confidence.toFixed(1)}%`
    );


    setText(
        "live-joint",
        joint
    );


    setText(
        "live-risk",
        status
    );


    document
        .querySelectorAll(
            ".confidence-bar-fill"
        )
        .forEach(bar => {

            bar.style.width =
                `${Math.max(
                    0,
                    Math.min(
                        confidence,
                        100
                    )
                )}%`;

        });

}


// ============================================================
// JOINTS
// ============================================================

async function fetchJoints() {

    try {

        const data =
            await fetchJSON(
                "/api/joints"
            );


        latestJoints = data;


        updateJointCards(
            data
        );


        updateReportJoints(
            data
        );


        return data;

    } catch (error) {

        console.error(
            "Joint error:",
            error
        );

        return null;

    }

}


// ============================================================
// UPDATE JOINT CARDS
// ============================================================

function updateJointCards(data) {

    if (!data) {

        return;

    }


    const cards =
        document.querySelectorAll(
            ".joint-card"
        );


    cards.forEach(
        (card, index) => {

            const id =
                String(index + 1);


            const joint =
                data[id];


            if (!joint) {

                return;

            }


            const status =
                String(
                    joint.status ||
                    "NORMAL"
                ).toUpperCase();


            const statusElement =
                card.querySelector(
                    ".joint-status"
                );


            if (statusElement) {

                statusElement.textContent =
                    status;

            }


            const indicator =
                card.querySelector(
                    ".joint-indicator"
                );


            if (indicator) {

                if (
                    status === "DAMAGED" ||
                    status === "CRITICAL"
                ) {

                    indicator.textContent =
                        "✕";

                } else if (
                    status === "WARNING"
                ) {

                    indicator.textContent =
                        "!";

                } else {

                    indicator.textContent =
                        "✓";

                }

            }


            card.classList.remove(

                "normal",
                "warning",
                "damaged",
                "critical"

            );


            if (
                status === "DAMAGED"
            ) {

                card.classList.add(
                    "damaged"
                );

            } else if (
                status === "CRITICAL"
            ) {

                card.classList.add(
                    "critical"
                );

            } else if (
                status === "WARNING"
            ) {

                card.classList.add(
                    "warning"
                );

            } else {

                card.classList.add(
                    "normal"
                );

            }

        }
    );

}


// ============================================================
// CURRENT JOINT
// ============================================================

async function fetchCurrentJoint() {

    try {

        const data =
            await fetchJSON(
                "/api/joints/current"
            );


        latestCurrentJoint =
            data.current_joint || {};


        updateCurrentJoint(
            data
        );


        return data;

    } catch (error) {

        console.error(
            "Current joint error:",
            error
        );

        return null;

    }

}


// ============================================================
// UPDATE CURRENT JOINT
// ============================================================

function updateCurrentJoint(data) {

    if (
        !data ||
        !data.current_joint
    ) {

        return;

    }


    const current =
        data.current_joint;


    const currentId =
        Number(
            current.joint_id
        );


    const position =
        Number(
            current.encoder_position
        );


    setText(

        "current-joint",

        `Joint ${currentId}`

    );


    setText(

        "encoder-position",

        position

    );


    const cards =
        document.querySelectorAll(
            ".joint-card"
        );


    cards.forEach(
        (card, index) => {

            const id =
                index + 1;


            card.classList.remove(
                "encoder-current"
            );


            const old =
                card.querySelector(
                    ".encoder-current-marker"
                );


            if (old) {

                old.remove();

            }


            if (
                id === currentId
            ) {

                card.classList.add(
                    "encoder-current"
                );


                const marker =
                    document.createElement(
                        "span"
                    );


                marker.className =
                    "encoder-current-marker";


                marker.textContent =
                    "ENCODER • CURRENT";


                card.appendChild(
                    marker
                );

            }

        }
    );


    if (
        !latestDetection.joint
    ) {

        setText(
            "live-joint",
            `Joint ${currentId}`
        );

    }

}


// ============================================================
// ALERTS
// ============================================================

async function fetchAlerts() {

    try {

        const data =
            await fetchJSON(
                "/api/alerts?limit=100"
            );


        latestAlerts =
            Array.isArray(data)
                ? data
                : [];


        updateAlertSummary(
            latestAlerts
        );


        updateAlertTables(
            latestAlerts
        );


        return latestAlerts;

    } catch (error) {

        console.error(
            "Alerts error:",
            error
        );

        return null;

    }

}


// ============================================================
// ALERT SUMMARY
// ============================================================

function updateAlertSummary(alerts) {

    const total =
        alerts.length;


    const warning =
        alerts.filter(

            alert =>

                String(
                    alert.severity || ""
                ).toUpperCase() ===
                "WARNING"

        ).length;


    const critical =
        alerts.filter(

            alert =>

                String(
                    alert.severity || ""
                ).toUpperCase() ===
                "CRITICAL"

        ).length;


    setText(
        "alerts-total",
        total
    );


    setText(
        "alerts-warning",
        warning
    );


    setText(
        "alerts-critical",
        critical
    );


    setText(
        "alerts-page-total",
        total
    );


    setText(
        "alerts-page-warning",
        warning
    );


    setText(
        "alerts-page-critical",
        critical
    );

}


// ============================================================
// ALERT TABLES
// ============================================================

function updateAlertTables(alerts) {

    const container =
        getElement(
            "alerts-table-container"
        );


    if (container) {

        if (
            alerts.length === 0
        ) {

            container.innerHTML = `

                <div class="empty-state">

                    No alerts recorded yet.

                </div>

            `;

        } else {

            container.innerHTML = `

                <table class="data-table">

                    <thead>

                        <tr>

                            <th>TIME</th>
                            <th>TYPE</th>
                            <th>SEVERITY</th>
                            <th>JOINT</th>
                            <th>MESSAGE</th>

                        </tr>

                    </thead>

                    <tbody>

                        ${alerts

                            .map(

                                alert => {

                                    const severity =
                                        String(
                                            alert.severity ||
                                            "WARNING"
                                        ).toUpperCase();


                                    return `

                                        <tr>

                                            <td>

                                                ${escapeHTML(
                                                    formatDateTime(
                                                        alert.timestamp
                                                    )
                                                )}

                                            </td>

                                            <td>

                                                ${escapeHTML(
                                                    alert.alert_type ||
                                                    "UNKNOWN"
                                                )}

                                            </td>

                                            <td class="${
                                                severity ===
                                                "CRITICAL"

                                                    ? "severity-critical"

                                                    : "severity-warning"

                                            }">

                                                ${escapeHTML(
                                                    severity
                                                )}

                                            </td>

                                            <td>

                                                ${escapeHTML(
                                                    alert.joint ||
                                                    "System"
                                                )}

                                            </td>

                                            <td>

                                                ${escapeHTML(
                                                    alert.message ||
                                                    ""
                                                )}

                                            </td>

                                        </tr>

                                    `;

                                }

                            )

                            .join("")}

                    </tbody>

                </table>

            `;

        }

    }


    // --------------------------------------------------------
    // Dashboard recent alerts
    // --------------------------------------------------------

    const recent =
        getElement(
            "recent-alerts-list"
        );


    if (recent) {

        const five =
            alerts.slice(
                0,
                5
            );


        if (
            five.length === 0
        ) {

            recent.innerHTML = `

                <div class="empty-state">

                    No alerts recorded yet.

                </div>

            `;

        } else {

            recent.innerHTML = `

                <table class="data-table">

                    <thead>

                        <tr>

                            <th>TIME</th>
                            <th>TYPE</th>
                            <th>SEVERITY</th>
                            <th>JOINT</th>

                        </tr>

                    </thead>

                    <tbody>

                        ${five

                            .map(

                                alert => {

                                    const severity =
                                        String(
                                            alert.severity ||
                                            "WARNING"
                                        ).toUpperCase();


                                    return `

                                        <tr>

                                            <td>

                                                ${escapeHTML(
                                                    formatDateTime(
                                                        alert.timestamp
                                                    )
                                                )}

                                            </td>

                                            <td>

                                                ${escapeHTML(
                                                    alert.alert_type ||
                                                    "UNKNOWN"
                                                )}

                                            </td>

                                            <td class="${
                                                severity ===
                                                "CRITICAL"

                                                    ? "severity-critical"

                                                    : "severity-warning"

                                            }">

                                                ${escapeHTML(
                                                    severity
                                                )}

                                            </td>

                                            <td>

                                                ${escapeHTML(
                                                    alert.joint ||
                                                    "System"
                                                )}

                                            </td>

                                        </tr>

                                    `;

                                }

                            )

                            .join("")}

                    </tbody>

                </table>

            `;

        }

    }

}


// ============================================================
// TELEMETRY HISTORY
// ============================================================

async function fetchTelemetryHistory() {

    try {

        const data =
            await fetchJSON(
                "/api/telemetry/history?limit=20"
            );


        updateTelemetryTable(
            data
        );


        setText(

            "report-telemetry-count",

            Array.isArray(data)
                ? data.length
                : 0

        );


        return data;

    } catch (error) {

        console.error(
            "Telemetry history error:",
            error
        );

        return null;

    }

}


// ============================================================
// TELEMETRY TABLE
// ============================================================

function updateTelemetryTable(rows) {

    const container =
        getElement(
            "telemetry-table-container"
        );


    if (!container) {

        return;

    }


    if (
        !Array.isArray(rows)
        ||
        rows.length === 0
    ) {

        container.innerHTML = `

            <div class="empty-state">

                Waiting for telemetry data...

            </div>

        `;

        return;

    }


    container.innerHTML = `

        <table class="data-table">

            <thead>

                <tr>

                    <th>TIME</th>
                    <th>ENCODER</th>
                    <th>VIBRATION EVENTS/S</th>
                    <th>TEMP</th>
                    <th>HUMIDITY</th>
                    <th>CURRENT</th>
                    <th>ACOUSTIC EVENTS/S</th>

                </tr>

            </thead>

            <tbody>

                ${rows

                    .map(

                        row => `

                            <tr>

                                <td>

                                    ${escapeHTML(
                                        formatDateTime(
                                            row.timestamp
                                        )
                                    )}

                                </td>

                                <td>

                                    ${row.encoder_pulses ?? 0}

                                </td>

                                <td>

                                    ${Number(
                                        row.vibration_events_per_sec ??
                                        row.vibration_pulses ??
                                        0
                                    )}

                                </td>

                                <td>

                                    ${Number(
                                        row.temperature ?? 0
                                    ).toFixed(1)} °C

                                </td>

                                <td>

                                    ${Number(
                                        row.humidity ?? 0
                                    ).toFixed(1)} %

                                </td>

                                <td>

                                    ${Number(
                                        row.current_amps ?? 0
                                    ).toFixed(2)} A

                                </td>

                                <td>

                                    ${Number(
                                        row.acoustic_events_per_sec ??
                                        row.acoustic_pulses ??
                                        0
                                    )}

                                </td>

                            </tr>

                        `

                    )

                    .join("")}

            </tbody>

        </table>

    `;

}


// ============================================================
// CALIBRATION
// ============================================================

async function fetchCalibration() {

    try {

        const data =
            await fetchJSON(
                "/api/joints/calibration"
            );


        latestCalibration =
            data;


        updateCalibration(
            data
        );


        return data;

    } catch (error) {

        console.error(
            "Calibration error:",
            error
        );

        return null;

    }

}


// ============================================================
// UPDATE CALIBRATION
// ============================================================

function updateCalibration(data) {

    const container =
        getElement(
            "settings-calibration"
        );


    if (!container) {

        return;

    }


    const positions =
        data.joint_positions || {};


    container.innerHTML =

        Object

            .entries(
                positions
            )

            .map(

                ([id, position]) => `

                    <div class="calibration-row">

                        <span>

                            Joint ${escapeHTML(id)}

                        </span>

                        <strong>

                            ${escapeHTML(
                                String(position)
                            )} pulses

                        </strong>

                    </div>

                `

            )

            .join("");

}


// ============================================================
// HEALTH
// ============================================================

async function fetchHealth() {

    try {

        const data =
            await fetchJSON(
                "/api/health"
            );


        latestHealth =
            data;


        updateHealth(
            data
        );


        return data;

    } catch (error) {

        console.error(
            "Health error:",
            error
        );

        return null;

    }

}


// ============================================================
// UPDATE HEALTH
// ============================================================

function updateHealth(data) {

    if (!data) {

        return;

    }


    setText(
        "settings-yolo",
        data.yolo || "STANDBY"
    );


    setText(
        "settings-camera",
        data.camera || "STANDBY"
    );


    setText(
        "settings-mode",
        data.mode || "SIMULATION"
    );


    setText(
        "report-mode",
        data.mode || "SIMULATION"
    );

}


// ============================================================
// REPORT JOINTS
// ============================================================

function updateReportJoints(data) {

    const container =
        getElement(
            "report-joints"
        );


    if (!container) {

        return;

    }


    container.innerHTML =

        Object

            .values(
                data || {}
            )

            .map(

                joint => `

                    <div class="report-joint">

                        <span>

                            ${escapeHTML(
                                joint.name ||
                                "Joint"
                            )}

                        </span>

                        <strong
                            class="report-joint-status"
                        >

                            ${escapeHTML(
                                joint.status ||
                                "NORMAL"
                            )}

                        </strong>

                    </div>

                `

            )

            .join("");

}


// ============================================================
// REPORT COUNTS
// ============================================================

function updateReportCounts() {

    setText(

        "report-alert-count",

        latestAlerts.length

    );


    setText(

        "report-critical-count",

        latestAlerts.filter(

            alert =>

                String(
                    alert.severity || ""
                ).toUpperCase() ===
                "CRITICAL"

        ).length

    );


    setText(

        "report-detection-count",

        latestDetection &&

        latestDetection.detection !== "NORMAL"

            ? 1

            : 0

    );


    setText(

        "report-generated",

        `Generated: ${new Date().toLocaleString()}`

    );

}


// ============================================================
// SECONDARY PAGE UPDATES
// ============================================================

function updateSecondaryPages() {

    updateReportCounts();

}


// ============================================================
// PHASE 2
// CAMERA STATUS
// ============================================================

async function fetchCameraStatus() {

    try {

        const data =
            await fetchJSON(
                "/api/camera/status"
            );


        latestCameraStatus =
            data || {};


        const inference =
            data && data.inference
                ? data.inference
                : {};


        const yolo =
            data && data.yolo
                ? data.yolo
                : {};


        cameraOnline =
            inference.camera_available === true;


        cameraModelLoaded =
            inference.model_loaded === true ||
            yolo.loaded === true;


        const statusText =
            cameraOnline

                ? (

                    cameraModelLoaded

                        ? "CAMERA CONNECTED • YOLO ACTIVE"

                        : "CAMERA CONNECTED • YOLO STANDBY"

                )

                : "CAMERA NOT AVAILABLE";


        // ----------------------------------------------------
        // Status text
        // ----------------------------------------------------

        setText(
            "camera-status",
            statusText
        );


        setText(
            "camera-status-dashboard",
            statusText
        );


        // ----------------------------------------------------
        // Optional detailed fields
        // ----------------------------------------------------

        setText(
            "camera-state",
            cameraOnline
                ? "CONNECTED"
                : "OFFLINE"
        );


        setText(
            "yolo-state",
            cameraModelLoaded
                ? "LOADED"
                : "STANDBY"
        );


        setText(
            "inference-state",
            inference.status ||
            "WAITING"
        );


        // ----------------------------------------------------
        // Camera feed elements
        // ----------------------------------------------------

        const liveFeed =
            getElement(
                "live-camera-feed"
            );


        const dashboardFeed =
            getElement(
                "dashboard-camera-feed"
            );


        const offlineMessage =
            getElement(
                "camera-offline-message"
            );


        const dashboardOffline =
            getElement(
                "dashboard-camera-offline"
            );


        // ----------------------------------------------------
        // Live feed
        // ----------------------------------------------------

        if (liveFeed) {

            if (
                cameraOnline
            ) {

                liveFeed.style.display =
                    "block";


                // Set stream URL only once.
                // Avoid reloading the MJPEG stream
                // every 1 second.

                if (
                    !liveFeed.src ||
                    !liveFeed.src.includes(
                        "/api/camera/feed"
                    )
                ) {

                    liveFeed.src =
                        CAMERA_FEED_URL;

                }

            } else {

                liveFeed.style.display =
                    "none";

            }

        }


        // ----------------------------------------------------
        // Dashboard camera feed
        // ----------------------------------------------------

        if (dashboardFeed) {

            if (
                cameraOnline
            ) {

                dashboardFeed.style.display =
                    "block";


                if (
                    !dashboardFeed.src ||
                    !dashboardFeed.src.includes(
                        "/api/camera/feed"
                    )
                ) {

                    dashboardFeed.src =
                        CAMERA_FEED_URL;

                }

            } else {

                dashboardFeed.style.display =
                    "none";

            }

        }


        // ----------------------------------------------------
        // Offline messages
        // ----------------------------------------------------

        if (offlineMessage) {

            offlineMessage.style.display =
                cameraOnline
                    ? "none"
                    : "flex";

        }


        if (dashboardOffline) {

            dashboardOffline.style.display =
                cameraOnline
                    ? "none"
                    : "flex";

        }


        // ----------------------------------------------------
        // Camera indicators
        // ----------------------------------------------------

        document
            .querySelectorAll(
                ".camera-indicator"
            )
            .forEach(indicator => {

                indicator.classList.remove(
                    "online",
                    "offline"
                );


                indicator.classList.add(

                    cameraOnline
                        ? "online"
                        : "offline"

                );

            });


        // ----------------------------------------------------
        // Camera status classes
        // ----------------------------------------------------

        document
            .querySelectorAll(
                ".camera-status"
            )
            .forEach(element => {

                element.classList.remove(
                    "online",
                    "offline"
                );


                element.classList.add(

                    cameraOnline
                        ? "online"
                        : "offline"

                );

            });


        return data;

    } catch (error) {

        console.error(
            "Camera status error:",
            error
        );


        cameraOnline = false;


        setText(
            "camera-status",
            "CAMERA STATUS ERROR"
        );


        const liveFeed =
            getElement(
                "live-camera-feed"
            );


        const dashboardFeed =
            getElement(
                "dashboard-camera-feed"
            );


        const offlineMessage =
            getElement(
                "camera-offline-message"
            );


        const dashboardOffline =
            getElement(
                "dashboard-camera-offline"
            );


        if (liveFeed) {

            liveFeed.style.display =
                "none";

        }


        if (dashboardFeed) {

            dashboardFeed.style.display =
                "none";

        }


        if (offlineMessage) {

            offlineMessage.style.display =
                "flex";

        }


        if (dashboardOffline) {

            dashboardOffline.style.display =
                "flex";

        }


        return null;

    }

}


// ============================================================
// CAMERA FEED ERROR HANDLING
// ============================================================

function setupCameraFeedHandling() {

    const feeds =
        document.querySelectorAll(
            "#live-camera-feed, #dashboard-camera-feed"
        );


    feeds.forEach(feed => {

        feed.addEventListener(
            "error",
            () => {

                console.warn(
                    "Camera feed connection error."
                );


                const offlineMessage =
                    getElement(
                        "camera-offline-message"
                    );


                const dashboardOffline =
                    getElement(
                        "dashboard-camera-offline"
                    );


                if (
                    feed.id ===
                    "live-camera-feed"
                ) {

                    if (offlineMessage) {

                        offlineMessage.style.display =
                            "flex";

                    }

                }


                if (
                    feed.id ===
                    "dashboard-camera-feed"
                ) {

                    if (dashboardOffline) {

                        dashboardOffline.style.display =
                            "flex";

                    }

                }

            }
        );


        feed.addEventListener(
            "load",
            () => {

                if (
                    feed.src.includes(
                        "/api/camera/feed"
                    )
                ) {

                    const offlineMessage =
                        getElement(
                            "camera-offline-message"
                        );


                    const dashboardOffline =
                        getElement(
                            "dashboard-camera-offline"
                        );


                    if (
                        feed.id ===
                        "live-camera-feed"
                    ) {

                        if (offlineMessage) {

                            offlineMessage.style.display =
                                "none";

                        }

                    }


                    if (
                        feed.id ===
                        "dashboard-camera-feed"
                    ) {

                        if (dashboardOffline) {

                            dashboardOffline.style.display =
                                "none";

                        }

                    }

                }

            }
        );

    });

}


// ============================================================
// SYSTEM STATUS
// ============================================================

async function fetchSystemStatus() {

    try {

        const data =
            await fetchJSON(
                "/api/status"
            );


        updateBackendStatus(
            true
        );


        if (
            data.last_update
        ) {

            setText(

                "last-update",

                formatDateTime(
                    data.last_update
                )

            );

        }


        return data;

    } catch (error) {

        updateBackendStatus(
            false
        );


        return null;

    }

}


// ============================================================
// HTML ESCAPE
// ============================================================

function escapeHTML(value) {

    return String(
        value ?? ""
    )

        .replace(
            /&/g,
            "&amp;"
        )

        .replace(
            /</g,
            "&lt;"
        )

        .replace(
            />/g,
            "&gt;"
        )

        .replace(
            /"/g,
            "&quot;"
        )

        .replace(
            /'/g,
            "&#039;"
        );

}


// ============================================================
// DOWNLOAD REPORT
// ============================================================

function downloadReport() {

    const report = {

        system:
            "BELTSENTINEL AI",

        generated_at:
            new Date().toISOString(),

        mode:
            latestHealth.mode ||
            "LIVE_ESP32",

        telemetry_records:
            latestTelemetry,

        risk:
            latestRisk,

        detection:
            latestDetection,

        joints:
            latestJoints,

        alerts:
            latestAlerts,

        camera:
            latestCameraStatus

    };


    const blob =
        new Blob(

            [

                JSON.stringify(
                    report,
                    null,
                    4
                )

            ],

            {
                type:
                    "application/json"
            }

        );


    const url =
        URL.createObjectURL(
            blob
        );


    const link =
        document.createElement(
            "a"
        );


    link.href =
        url;


    link.download =
        "beltsentinel_report.json";


    document.body.appendChild(
        link
    );


    link.click();


    link.remove();


    URL.revokeObjectURL(
        url
    );

}


// ============================================================
// NAVIGATION
// ============================================================

function setupNavigation() {

    document
        .querySelectorAll(
            "[data-page]"
        )
        .forEach(
            item => {

                item.addEventListener(

                    "click",

                    event => {

                        event.preventDefault();


                        const page =
                            item.dataset.page;


                        window.location.hash =
                            page;

                    }

                );

            }
        );


    window.addEventListener(

        "hashchange",

        () => {

            showPage(
                getPageFromHash()
            );

        }

    );

}


// ============================================================
// MAIN REFRESH
// ============================================================

async function refreshDashboard() {

    const results =
        await Promise.allSettled([

            fetchTelemetry(),

            fetchRisk(),

            fetchDetection(),

            fetchJoints(),

            fetchCurrentJoint(),

            fetchAlerts(),

            fetchTelemetryHistory(),

            fetchCalibration(),

            fetchHealth(),

            fetchSystemStatus(),

            fetchCameraStatus()

        ]);


    const success =
        results.some(

            result =>

                result.status ===
                "fulfilled"

        );


    if (success) {

        updateBackendStatus(
            true
        );

    }


    updateReportCounts();

}


// ============================================================
// INITIALIZE
// ============================================================

function initializeDashboard() {

    console.log(
        "BELTSENTINEL AI MODULE 7.9"
    );


    console.log(
        "PHASE 2 CAMERA INTEGRATION ACTIVE"
    );


    setupNavigation();


    setupCameraFeedHandling();


    setupPushNotifications();


    setupHttpAlertFallback();


    showPage(
        getPageFromHash()
    );


    updateClock();


    setInterval(

        updateClock,

        1000

    );


    refreshDashboard();


    setInterval(

        refreshDashboard,

        UPDATE_INTERVAL

    );

}


// ============================================================
// DOM READY
// ============================================================

document.addEventListener(

    "DOMContentLoaded",

    initializeDashboard

);

// ============================================================
// INDUSTRIAL SCADA TREND RECORDER
// ============================================================

const TREND_REFRESH_INTERVAL = 3000;
const TREND_LIMIT = 120;

let trendTelemetry = [];
let trendDetections = [];
let lastTrendFetch = 0;
let graphConsoleOpen = false;


async function fetchTrendHistory(force = false) {

    const now = Date.now();

    if (!force && (now - lastTrendFetch) < TREND_REFRESH_INTERVAL) {
        return;
    }

    lastTrendFetch = now;

    try {

        const [telemetry, detections] = await Promise.all([

            fetchJSON(
                `/api/telemetry/history?limit=${TREND_LIMIT}`
            ),

            fetchJSON(
                `/api/detection/history?limit=${TREND_LIMIT}`
            )

        ]);

        trendTelemetry = Array.isArray(telemetry)
            ? telemetry.reverse()
            : [];

        trendDetections = Array.isArray(detections)
            ? detections.reverse()
            : [];

        updateTrendCounters();
        drawAllTrendCharts();

    } catch (error) {

        console.error(
            "Trend history error:",
            error
        );

        setText(
            "graph-recording-status",
            "DATABASE WAIT"
        );

    }
}


function updateTrendCounters() {

    const telemetryCount = trendTelemetry.length;
    const detectionCount = trendDetections.length;

    setText(
        "graph-sample-count",
        `${telemetryCount} samples`
    );

    setText(
        "console-telemetry-count",
        telemetryCount
    );

    setText(
        "console-detection-count",
        detectionCount
    );

}


function graphTimeLabel(value) {

    if (!value) {
        return "--:--";
    }

    const d = new Date(value);

    if (Number.isNaN(d.getTime())) {
        return String(value).slice(-8);
    }

    return d.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
    });
}


function numberValue(value) {

    const n = Number(value);

    return Number.isFinite(n) ? n : 0;
}


function resizeCanvas(canvas) {

    if (!canvas) {
        return null;
    }

    const rect = canvas.getBoundingClientRect();

    const width = Math.max(
        320,
        Math.floor(rect.width || canvas.clientWidth || 640)
    );

    const height = Math.max(
        170,
        Math.floor(rect.height || 185)
    );

    const ratio = window.devicePixelRatio || 1;

    canvas.width = Math.floor(width * ratio);
    canvas.height = Math.floor(height * ratio);

    const ctx = canvas.getContext("2d");

    ctx.setTransform(
        ratio,
        0,
        0,
        ratio,
        0,
        0
    );

    return {
        ctx,
        width,
        height
    };
}


function drawEmptyChart(canvas, message = "WAITING FOR RECORDED DATA") {

    const surface = resizeCanvas(canvas);

    if (!surface) {
        return;
    }

    const { ctx, width, height } = surface;

    ctx.clearRect(0, 0, width, height);

    ctx.fillStyle = "#111517";
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = "#333d41";
    ctx.lineWidth = 1;

    for (let y = 25; y < height; y += 35) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
    }

    ctx.fillStyle = "#7d898e";
    ctx.font = "10px Segoe UI, Arial";
    ctx.textAlign = "center";
    ctx.fillText(
        message,
        width / 2,
        height / 2
    );
}


function drawIndustrialLineChart(
    canvasId,
    rows,
    series,
    options = {}
) {

    const canvas = getElement(canvasId);

    if (!canvas) {
        return;
    }

    if (!rows || rows.length < 2) {
        drawEmptyChart(canvas);
        return;
    }

    const surface = resizeCanvas(canvas);

    if (!surface) {
        return;
    }

    const { ctx, width, height } = surface;

    ctx.clearRect(0, 0, width, height);

    const left = 48;
    const right = 42;
    const top = 22;
    const bottom = 30;

    const plotW = width - left - right;
    const plotH = height - top - bottom;

    /* background */
    ctx.fillStyle = "#101416";
    ctx.fillRect(0, 0, width, height);

    /* technical grid */
    ctx.lineWidth = 1;
    ctx.strokeStyle = "#303a3e";

    for (let i = 0; i <= 4; i++) {

        const y = top + (plotH * i / 4);

        ctx.beginPath();
        ctx.moveTo(left, y);
        ctx.lineTo(width - right, y);
        ctx.stroke();
    }

    const xCount = Math.min(6, rows.length);

    for (let i = 0; i < xCount; i++) {

        const x = left + (plotW * i / Math.max(1, xCount - 1));

        ctx.beginPath();
        ctx.moveTo(x, top);
        ctx.lineTo(x, height - bottom);
        ctx.stroke();
    }

    /* frame */
    ctx.strokeStyle = "#5b666b";
    ctx.strokeRect(
        left,
        top,
        plotW,
        plotH
    );

    /* gather ranges per series */
    const prepared = series.map(item => {

        const values = rows.map(row =>
            numberValue(row[item.key])
        );

        let min = Math.min(...values);
        let max = Math.max(...values);

        if (min === max) {
            const pad = Math.abs(min) * .08 || 1;
            min -= pad;
            max += pad;
        } else {
            const pad = (max - min) * .10;
            min -= pad;
            max += pad;
        }

        return {
            ...item,
            values,
            min,
            max
        };
    });

    /* y-axis labels for first series */
    ctx.font = "9px Segoe UI, Arial";
    ctx.fillStyle = "#89959a";
    ctx.textAlign = "right";

    const primary = prepared[0];

    for (let i = 0; i <= 4; i++) {

        const ratio = i / 4;
        const value = primary.max -
            ((primary.max - primary.min) * ratio);

        const y = top + plotH * ratio;

        ctx.fillText(
            formatGraphValue(value, primary.decimals),
            left - 7,
            y + 3
        );
    }

    /* second axis */
    if (prepared.length > 1) {

        const secondary = prepared[1];

        ctx.textAlign = "left";
        ctx.fillStyle = "#78858a";

        for (let i = 0; i <= 4; i++) {

            const ratio = i / 4;
            const value = secondary.max -
                ((secondary.max - secondary.min) * ratio);

            const y = top + plotH * ratio;

            ctx.fillText(
                formatGraphValue(value, secondary.decimals),
                width - right + 7,
                y + 3
            );
        }
    }

    /* x labels */
    ctx.textAlign = "center";
    ctx.fillStyle = "#707c81";

    const labelCount = Math.min(5, rows.length);

    for (let i = 0; i < labelCount; i++) {

        const index = Math.floor(
            i * (rows.length - 1) /
            Math.max(1, labelCount - 1)
        );

        const x = left +
            (plotW * index / Math.max(1, rows.length - 1));

        ctx.fillText(
            graphTimeLabel(rows[index].timestamp),
            x,
            height - 9
        );
    }

    /* lines */
    prepared.forEach(item => {

        ctx.beginPath();

        item.values.forEach((value, index) => {

            const x = left +
                (plotW * index /
                Math.max(1, rows.length - 1));

            const y = top +
                plotH *
                (1 - ((value - item.min) /
                (item.max - item.min)));

            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        ctx.strokeStyle = item.color;
        ctx.lineWidth = 2;
        ctx.lineJoin = "round";
        ctx.lineCap = "round";
        ctx.stroke();

        /* current point */
        const lastIndex = item.values.length - 1;
        const lastValue = item.values[lastIndex];
        const lastX = left + plotW;
        const lastY = top + plotH *
            (1 - ((lastValue - item.min) /
            (item.max - item.min)));

        ctx.beginPath();
        ctx.arc(lastX, lastY, 3, 0, Math.PI * 2);
        ctx.fillStyle = item.color;
        ctx.fill();
    });

    /* legend */
    let legendX = left + 8;

    series.forEach(item => {

        ctx.fillStyle = item.color;
        ctx.fillRect(
            legendX,
            8,
            16,
            3
        );

        ctx.fillStyle = "#b6c0c4";
        ctx.font = "8px Segoe UI, Arial";
        ctx.textAlign = "left";
        ctx.fillText(
            item.label,
            legendX + 21,
            11
        );

        legendX +=
            24 +
            ctx.measureText(item.label).width;
    });
}


function formatGraphValue(value, decimals = 1) {

    const n = numberValue(value);

    return n.toFixed(decimals);
}


function drawIndustrialBarChart(
    canvasId,
    values,
    labels
) {

    const canvas = getElement(canvasId);

    if (!canvas) {
        return;
    }

    if (!values || !values.length) {
        drawEmptyChart(canvas, "NO AI DETECTION RECORDS");
        return;
    }

    const surface = resizeCanvas(canvas);

    if (!surface) {
        return;
    }

    const { ctx, width, height } = surface;

    ctx.clearRect(0, 0, width, height);

    ctx.fillStyle = "#101416";
    ctx.fillRect(0, 0, width, height);

    const left = 52;
    const right = 22;
    const top = 25;
    const bottom = 35;

    const plotW = width - left - right;
    const plotH = height - top - bottom;

    const maxValue = Math.max(...values, 1);

    ctx.strokeStyle = "#303a3e";
    ctx.lineWidth = 1;

    for (let i = 0; i <= 4; i++) {

        const y = top + plotH * i / 4;

        ctx.beginPath();
        ctx.moveTo(left, y);
        ctx.lineTo(width - right, y);
        ctx.stroke();

        ctx.fillStyle = "#7f8b90";
        ctx.font = "9px Segoe UI, Arial";
        ctx.textAlign = "right";
        ctx.fillText(
            Math.round(maxValue * (1 - i / 4)),
            left - 7,
            y + 3
        );
    }

    const barGap = 14;
    const barWidth = Math.max(
        25,
        (plotW - barGap * (values.length + 1)) /
        values.length
    );

    values.forEach((value, index) => {

        const x = left + barGap +
            index * (barWidth + barGap);

        const barH = plotH * value / maxValue;
        const y = top + plotH - barH;

        ctx.fillStyle = [
            "#8e999e",
            "#c5a85f",
            "#b56a70",
            "#6f9da2",
            "#7b858a",
            "#a9b1b5"
        ][index % 6];

        ctx.fillRect(
            x,
            y,
            barWidth,
            barH
        );

        ctx.strokeStyle = "#c7ced1";
        ctx.strokeRect(
            x,
            y,
            barWidth,
            barH
        );

        ctx.fillStyle = "#d4dbde";
        ctx.font = "9px Segoe UI, Arial";
        ctx.textAlign = "center";
        ctx.fillText(
            value,
            x + barWidth / 2,
            Math.max(16, y - 5)
        );

        ctx.fillStyle = "#89959a";
        ctx.font = "8px Segoe UI, Arial";
        ctx.fillText(
            labels[index],
            x + barWidth / 2,
            height - 13
        );
    });
}


function getDetectionConfidenceRows() {

    return trendDetections.map(row => ({
        timestamp: row.timestamp,
        confidence: Number(row.confidence) <= 1
            ? Number(row.confidence) * 100
            : Number(row.confidence)
    }));
}


function getDetectionTypeCounts() {

    const counts = {};

    trendDetections.forEach(row => {

        const type = String(
            row.detection || "NORMAL"
        ).toUpperCase();

        counts[type] =
            (counts[type] || 0) + 1;
    });

    const entries = Object.entries(counts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 6);

    return {
        labels: entries.map(item => item[0]),
        values: entries.map(item => item[1])
    };
}


function drawAllTrendCharts() {

    const sensorRows = trendTelemetry;

    drawIndustrialLineChart(
        "chart-temp-humidity",
        sensorRows,
        [
            {
                key: "temperature",
                label: "TEMP °C",
                color: "#c6cdd0",
                decimals: 1
            },
            {
                key: "humidity",
                label: "HUMIDITY %",
                color: "#7faeb5",
                decimals: 1
            }
        ]
    );

    drawIndustrialLineChart(
        "chart-vibration-acoustic",
        sensorRows,
        [
            {
                key: "vibration_pulses",
                label: "VIBRATION",
                color: "#d1b76b",
                decimals: 0
            },
            {
                key: "acoustic_pulses",
                label: "ACOUSTIC",
                color: "#a9b1b5",
                decimals: 0
            }
        ]
    );

    drawIndustrialLineChart(
        "chart-current",
        sensorRows,
        [
            {
                key: "current_amps",
                label: "CURRENT A",
                color: "#8cc3c7",
                decimals: 2
            }
        ]
    );

    drawIndustrialLineChart(
        "chart-encoder",
        sensorRows,
        [
            {
                key: "encoder_pulses",
                label: "ENCODER PULSES",
                color: "#d0d6d8",
                decimals: 0
            }
        ]
    );

    const confidenceRows =
        getDetectionConfidenceRows();

    drawIndustrialLineChart(
        "chart-detection-confidence",
        confidenceRows,
        [
            {
                key: "confidence",
                label: "YOLO CONFIDENCE %",
                color: "#c5a85f",
                decimals: 1
            }
        ]
    );

    const eventCounts =
        getDetectionTypeCounts();

    drawIndustrialBarChart(
        "chart-detection-events",
        eventCounts.values,
        eventCounts.labels
    );

    /* dashboard quick console copies */
    drawIndustrialLineChart(
        "console-temp-humidity",
        sensorRows,
        [
            { key: "temperature", label: "TEMP °C", color: "#c6cdd0", decimals: 1 },
            { key: "humidity", label: "HUMIDITY %", color: "#7faeb5", decimals: 1 }
        ]
    );

    drawIndustrialLineChart(
        "console-vibration-acoustic",
        sensorRows,
        [
            { key: "vibration_pulses", label: "VIBRATION", color: "#d1b76b", decimals: 0 },
            { key: "acoustic_pulses", label: "ACOUSTIC", color: "#a9b1b5", decimals: 0 }
        ]
    );

    drawIndustrialLineChart(
        "console-current",
        sensorRows,
        [
            { key: "current_amps", label: "CURRENT A", color: "#8cc3c7", decimals: 2 }
        ]
    );

    drawIndustrialLineChart(
        "console-encoder",
        sensorRows,
        [
            { key: "encoder_pulses", label: "ENCODER PULSES", color: "#d0d6d8", decimals: 0 }
        ]
    );

    drawIndustrialLineChart(
        "console-detection-confidence",
        confidenceRows,
        [
            { key: "confidence", label: "YOLO CONFIDENCE %", color: "#c5a85f", decimals: 1 }
        ]
    );

    drawIndustrialBarChart(
        "console-detection-events",
        eventCounts.values,
        eventCounts.labels
    );
}


function setupGraphConsole() {

    const button =
        getElement("graph-console-button");

    const overlay =
        getElement("graph-console-overlay");

    const close =
        getElement("graph-console-close");

    if (!button || !overlay) {
        return;
    }

    function openConsole() {

        graphConsoleOpen = true;

        overlay.classList.add("open");
        overlay.setAttribute("aria-hidden", "false");

        fetchTrendHistory(true);
    }

    function closeConsole() {

        graphConsoleOpen = false;

        overlay.classList.remove("open");
        overlay.setAttribute("aria-hidden", "true");
    }

    button.addEventListener(
        "click",
        openConsole
    );

    if (close) {
        close.addEventListener(
            "click",
            closeConsole
        );
    }

    overlay.addEventListener(
        "click",
        event => {
            if (event.target === overlay) {
                closeConsole();
            }
        }
    );

    document.addEventListener(
        "keydown",
        event => {
            if (event.key === "Escape" && graphConsoleOpen) {
                closeConsole();
            }
        }
    );
}


/* Extend initialization without replacing the existing controller. */
document.addEventListener(
    "DOMContentLoaded",
    () => {
        setupGraphConsole();
        fetchTrendHistory(true);
    }
);


/* Continuous graph refresh using already-recorded backend data. */
setInterval(
    () => {
        fetchTrendHistory(false);
    },
    1000
);


window.addEventListener(
    "resize",
    () => {
        window.requestAnimationFrame(
            drawAllTrendCharts
        );
    }
);


/* ============================================================
   NAVIGATION SAFETY FALLBACK
   Keeps the existing sidebar/page structure unchanged.
   ============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        const navItems = document.querySelectorAll(
            "[data-page]"
        );

        navItems.forEach(
            item => {

                item.addEventListener(
                    "click",
                    () => {

                        const page = item.dataset.page;

                        if (pageConfig[page]) {
                            window.setTimeout(
                                () => showPage(page),
                                0
                            );
                        }
                    }
                );
            }
        );

        window.setTimeout(
            () => showPage(getPageFromHash()),
            0
        );
    }
);

