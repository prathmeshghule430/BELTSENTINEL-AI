/*
 BELTSENTINEL AI - ADDITIVE SIH INTELLIGENCE UI
 This file injects one optional analytics panel and does not alter the
 existing navigation, charts, dashboard cards, camera or alerts.
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
        if (document.getElementById("bs-sih-intelligence-style")) return;
        const style = document.createElement("style");
        style.id = "bs-sih-intelligence-style";
        style.textContent = `
            .bs-sih-intelligence-panel { margin-top: 18px; }
            .bs-sih-intelligence-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-top:14px; }
            .bs-sih-metric { border:1px solid rgba(255,255,255,.10); padding:13px; background:rgba(255,255,255,.025); }
            .bs-sih-metric span { display:block; font-size:10px; letter-spacing:.10em; opacity:.65; text-transform:uppercase; }
            .bs-sih-metric strong { display:block; margin-top:7px; font-size:18px; }
            .bs-sih-ok { color:#8fc7a0; }
            .bs-sih-warn { color:#d9b66a; }
            .bs-sih-high { color:#e79a68; }
            .bs-sih-critical { color:#e47777; }
            .bs-sih-columns { display:grid; grid-template-columns:1.1fr .9fr; gap:16px; margin-top:14px; }
            .bs-sih-list { margin:0; padding-left:18px; }
            .bs-sih-list li { margin:7px 0; line-height:1.4; font-size:12px; }
            .bs-sih-bar { height:7px; background:rgba(255,255,255,.08); margin-top:8px; overflow:hidden; }
            .bs-sih-bar i { display:block; height:100%; background:currentColor; }
            .bs-sih-foot { margin-top:12px; font-size:10px; opacity:.58; line-height:1.5; }
            .bs-sih-twin { display:grid; grid-template-columns:repeat(5,1fr); gap:7px; margin-top:10px; }
            .bs-sih-joint { padding:9px 5px; border:1px solid rgba(255,255,255,.10); text-align:center; font-size:10px; }
            .bs-sih-joint b { display:block; font-size:11px; margin-bottom:4px; }
            @media(max-width:900px){ .bs-sih-intelligence-grid,.bs-sih-columns{grid-template-columns:1fr 1fr}.bs-sih-twin{grid-template-columns:repeat(5,1fr)} }
            @media(max-width:600px){ .bs-sih-intelligence-grid,.bs-sih-columns{grid-template-columns:1fr}.bs-sih-twin{grid-template-columns:repeat(2,1fr)} }
        `;
        document.head.appendChild(style);
    }

    function ensurePanel() {
        const page = document.getElementById("page-analytics");
        if (!page || panel) return panel;
        ensureStyles();
        panel = document.createElement("div");
        panel.id = "bs-sih-intelligence-panel";
        panel.className = "panel bs-sih-intelligence-panel";
        panel.innerHTML = `
            <div class="panel-header">
                <div>
                    <span class="eyebrow">SIH INTELLIGENCE LAYER</span>
                    <h3>Predictive Health &amp; Conveyor Digital Twin</h3>
                    <p>Additional trend-based risk projection and maintenance intelligence. Existing analytics remain unchanged.</p>
                </div>
                <span class="chart-tag" id="bs-sih-forecast-level">COLLECTING</span>
            </div>
            <div class="bs-sih-intelligence-grid">
                <div class="bs-sih-metric"><span>Forecast Risk</span><strong id="bs-sih-forecast-score">--</strong></div>
                <div class="bs-sih-metric"><span>Trend Direction</span><strong id="bs-sih-trend">--</strong></div>
                <div class="bs-sih-metric"><span>Inspection Horizon</span><strong id="bs-sih-horizon">--</strong></div>
                <div class="bs-sih-metric"><span>History Samples</span><strong id="bs-sih-samples">0</strong></div>
            </div>
            <div class="bs-sih-columns">
                <div>
                    <span class="eyebrow">MAINTENANCE INTELLIGENCE</span>
                    <ul id="bs-sih-recommendations" class="bs-sih-list"><li>Collecting trend history...</li></ul>
                </div>
                <div>
                    <span class="eyebrow">DIGITAL TWIN STATE</span>
                    <div id="bs-sih-twin" class="bs-sih-twin"></div>
                </div>
            </div>
            <div class="bs-sih-foot" id="bs-sih-method"></div>
        `;
        const riskDisplay = page.querySelector(".analytics-grid");
        if (riskDisplay) riskDisplay.insertAdjacentElement("afterend", panel);
        else page.appendChild(panel);
        return panel;
    }

    function levelClass(level) {
        level = String(level || "").toUpperCase();
        if (level === "HIGH") return "bs-sih-critical";
        if (level === "ELEVATED") return "bs-sih-high";
        if (level === "WATCH") return "bs-sih-warn";
        return "bs-sih-ok";
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
            const scoreEl = document.getElementById("bs-sih-forecast-score");
            scoreEl.textContent = p.available ? `${score.toFixed(0)} / 100` : "--";
            scoreEl.className = levelClass(level);
            document.getElementById("bs-sih-forecast-level").textContent = level;
            document.getElementById("bs-sih-trend").textContent = p.trend_direction || "--";
            document.getElementById("bs-sih-horizon").textContent = p.inspection_horizon || "Collecting history";
            document.getElementById("bs-sih-samples").textContent = p.data_points ?? 0;
            document.getElementById("bs-sih-method").textContent = p.method || "";
            document.getElementById("bs-sih-recommendations").innerHTML =
                (data.maintenance || []).slice(0, 6).map(x => `<li><b>${esc(x.priority)}:</b> ${esc(x.action)}</li>`).join("") || "<li>Continue monitoring.</li>";
            const joints = (data.digital_twin || {}).joints || [];
            document.getElementById("bs-sih-twin").innerHTML = joints.map(j => `<div class="bs-sih-joint"><b>${esc(j.name)}</b><span>${esc(j.status)}</span></div>`).join("");
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
