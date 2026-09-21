/*
 BELTSENTINEL AI - PREDICTIVE HEALTH UI
 This file injects one predictive health panel and preserves the existing navigation, charts, dashboard cards, camera and alerts.
*/
(function () {
    "use strict";

    let panel = null;

    function esc(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function ensureStyles() {
        if (document.getElementById("bs-health-intelligence-style")) return;
        const style = document.createElement("style");
        style.id = "bs-health-intelligence-style";
        style.textContent = `
            .bs-health-intelligence-panel { margin-top: 18px; }
            .bs-health-intelligence-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-top:14px; }
            .bs-health-metric { border:1px solid rgba(255,255,255,.10); padding:13px; background:rgba(255,255,255,.025); }
            .bs-health-metric span { display:block; font-size:10px; letter-spacing:.10em; opacity:.65; text-transform:uppercase; }
            .bs-health-metric strong { display:block; margin-top:7px; font-size:18px; }
            .bs-health-ok { color:#8fc7a0; }
            .bs-health-warn { color:#d9b66a; }
            .bs-health-high { color:#e79a68; }
            .bs-health-critical { color:#e47777; }
            .bs-health-columns { display:grid; grid-template-columns:1.1fr .9fr; gap:16px; margin-top:14px; }
            .bs-health-list { margin:0; padding-left:18px; }
            .bs-health-list li { margin:7px 0; line-height:1.4; font-size:12px; }
            .bs-health-bar { height:7px; background:rgba(255,255,255,.08); margin-top:8px; overflow:hidden; }
            .bs-health-bar i { display:block; height:100%; background:currentColor; }
            .bs-health-foot { margin-top:12px; font-size:10px; opacity:.58; line-height:1.5; }
            .bs-health-twin { display:grid; grid-template-columns:repeat(5,1fr); gap:7px; margin-top:10px; }
            .bs-health-joint { padding:9px 5px; border:1px solid rgba(255,255,255,.10); text-align:center; font-size:10px; }
            .bs-health-joint b { display:block; font-size:11px; margin-bottom:4px; }
            @media(max-width:900px){ .bs-health-intelligence-grid,.bs-health-columns{grid-template-columns:1fr 1fr}.bs-health-twin{grid-template-columns:repeat(5,1fr)} }
            @media(max-width:600px){ .bs-health-intelligence-grid,.bs-health-columns{grid-template-columns:1fr}.bs-health-twin{grid-template-columns:repeat(2,1fr)} }
        `;
        document.head.appendChild(style);
    }

    function ensurePanel() {
        const page = document.getElementById("page-analytics");
        if (!page || panel) return panel;
        ensureStyles();
        panel = document.createElement("div");
        panel.id = "bs-health-intelligence-panel";
        panel.className = "panel bs-health-intelligence-panel";
        panel.innerHTML = `
            <div class="panel-header">
                <div>
                    <span class="eyebrow">PREDICTIVE HEALTH</span>
                    <h3>Predictive Health &amp; Conveyor State</h3>
                    <p>Predictive health trends, maintenance guidance and conveyor state.</p>
                </div>
                <span class="chart-tag" id="bs-health-forecast-level">COLLECTING</span>
            </div>
            <div class="bs-health-intelligence-grid">
                <div class="bs-health-metric"><span>Forecast Risk</span><strong id="bs-health-forecast-score">--</strong></div>
                <div class="bs-health-metric"><span>Trend Direction</span><strong id="bs-health-trend">--</strong></div>
                <div class="bs-health-metric"><span>Inspection Horizon</span><strong id="bs-health-horizon">--</strong></div>
                <div class="bs-health-metric"><span>History Samples</span><strong id="bs-health-samples">0</strong></div>
            </div>
            <div class="bs-health-columns">
                <div>
                    <span class="eyebrow">MAINTENANCE INTELLIGENCE</span>
                    <ul id="bs-health-recommendations" class="bs-health-list"><li>Collecting trend history...</li></ul>
                </div>
                <div>
                    <span class="eyebrow">CONVEYOR STATE</span>
                    <div id="bs-health-twin" class="bs-health-twin"></div>
                </div>
            </div>
            <div class="bs-health-foot" id="bs-health-method"></div>
        `;
        const riskDisplay = page.querySelector(".analytics-grid");
        if (riskDisplay) riskDisplay.insertAdjacentElement("afterend", panel);
        else page.appendChild(panel);
        return panel;
    }

    function levelClass(level) {
        level = String(level || "").toUpperCase();
        if (level === "HIGH") return "bs-health-critical";
        if (level === "ELEVATED") return "bs-health-high";
        if (level === "WATCH") return "bs-health-warn";
        return "bs-health-ok";
    }

    async function refresh() {
        if (!document.getElementById("page-analytics")) return;
        ensurePanel();
        try {
            const response = await fetch("/api/intelligence/summary", { cache: "no-store" });
            if (!response.ok) return;
            const data = await response.json();
            const p = data.prediction || {};
            const score = Number(p.forecast_score || 0);
            const level = p.forecast_level || "COLLECTING";
            const scoreEl = document.getElementById("bs-health-forecast-score");
            scoreEl.textContent = p.available ? `${score.toFixed(0)} / 100` : "--";
            scoreEl.className = levelClass(level);
            document.getElementById("bs-health-forecast-level").textContent = level;
            document.getElementById("bs-health-trend").textContent = p.trend_direction || "--";
            document.getElementById("bs-health-horizon").textContent = p.inspection_horizon || "Collecting history";
            document.getElementById("bs-health-samples").textContent = p.data_points ?? 0;
            document.getElementById("bs-health-method").textContent = p.method || "";
            document.getElementById("bs-health-recommendations").innerHTML =
                (data.maintenance || []).slice(0, 6).map(x => `<li><b>${esc(x.priority)}:</b> ${esc(x.action)}</li>`).join("") || "<li>Continue monitoring.</li>";
            const joints = (data.digital_twin || {}).joints || [];
            document.getElementById("bs-health-twin").innerHTML = joints.map(j => `<div class="bs-health-joint"><b>${esc(j.name)}</b><span>${esc(j.status)}</span></div>`).join("");
        } catch (_) {
            // Optional panel must never interfere with the existing dashboard.
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        ensurePanel();
        refresh();
        window.setInterval(refresh, 5000);
    });
})();
