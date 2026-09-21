/* ============================================================
   BELTSENTINEL AI
   MAINTENANCE REPORTING & EXPORTS
   Additive module: preserves existing report/dashboard logic.
   ============================================================ */
(function () {
    "use strict";

    let cachedReport = null;

    const esc = (v) => String(v ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

    const num = (v, digits = 2) => {
        const n = Number(v);
        return Number.isFinite(n) ? n.toFixed(digits) : "0.00";
    };

    function dateText(v) {
        if (!v) return "--";
        const d = new Date(v);
        return Number.isNaN(d.getTime()) ? String(v) : d.toLocaleString("en-IN", { hour12: false });
    }

    function downloadBlob(filename, content, type) {
        const blob = new Blob([content], { type });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    }

    function csvCell(v) {
        const s = String(v ?? "");
        return `"${s.replace(/"/g, '""')}"`;
    }

    function nearestTelemetry(timestamp, telemetry) {
        if (!timestamp || !Array.isArray(telemetry) || !telemetry.length) return {};
        const target = new Date(timestamp).getTime();
        let best = telemetry[0];
        let bestDiff = Infinity;
        for (const row of telemetry) {
            const t = new Date(row.timestamp).getTime();
            const diff = Number.isFinite(t) ? Math.abs(t - target) : Infinity;
            if (diff < bestDiff) {
                best = row;
                bestDiff = diff;
            }
        }
        return best || {};
    }

    function abnormalityRemark(item) {
        const parts = [];
        const severity = String(item.severity || "").toUpperCase();
        const detection = String(item.detection || "").toLowerCase();
        const vibration = Number(item.vibration_pulses || 0);
        const acoustic = Number(item.acoustic_pulses || 0);
        const temperature = Number(item.temperature || 0);
        const current = Number(item.current_amps || 0);

        if (detection && detection !== "normal") parts.push(`AI abnormality detected: ${detection.replace(/_/g, " ")}`);
        if (severity === "CRITICAL") parts.push("Critical alert condition recorded");
        else if (severity === "WARNING") parts.push("Warning condition recorded");
        if (vibration > 0) parts.push(`vibration activity ${num(vibration, 1)}`);
        if (acoustic > 0) parts.push(`acoustic activity ${num(acoustic, 1)}`);
        if (temperature >= 38) parts.push(`temperature elevated at ${num(temperature, 1)} °C`);
        if (current >= 3) parts.push(`motor current elevated at ${num(current, 2)} A`);
        if (!parts.length) parts.push("No abnormality recorded in this event");
        return parts.join("; ");
    }

    function maintenanceAction(row) {
        const severity = String(row.severity || "").toUpperCase();
        const detection = String(row.detection || "").toLowerCase();
        if (severity === "CRITICAL" || detection === "belt_tear" || detection === "joint_damage") {
            return "Isolate the affected conveyor section when operationally safe and perform targeted joint/belt inspection.";
        }
        if (detection === "belt_crack" || detection === "edge_damage") {
            return "Inspect the affected belt area and verify damage progression during the next maintenance window.";
        }
        return "Continue monitoring and review the related sensor trend before scheduled maintenance.";
    }

    async function getReport() {
        const requests = await Promise.all([
            fetch("/api/telemetry/history?limit=1000", { cache: "no-store" }).then(r => r.ok ? r.json() : []),
            fetch("/api/detection/history?limit=1000", { cache: "no-store" }).then(r => r.ok ? r.json() : []),
            fetch("/api/alerts?limit=1000", { cache: "no-store" }).then(r => r.ok ? r.json() : []),
            fetch("/api/intelligence/summary", { cache: "no-store" }).then(r => r.ok ? r.json() : ({})),
            fetch("/api/health", { cache: "no-store" }).then(r => r.ok ? r.json() : ({}))
        ]);

        const telemetry = Array.isArray(requests[0]) ? requests[0] : [];
        const detections = Array.isArray(requests[1]) ? requests[1] : [];
        const alerts = Array.isArray(requests[2]) ? requests[2] : [];
        const intelligence = requests[3] || {};
        const health = requests[4] || {};
        const prediction = intelligence.prediction || {};
        const twin = intelligence.digital_twin || {};
        const maintenance = Array.isArray(intelligence.maintenance) ? intelligence.maintenance : [];

        const alertKeys = new Set(alerts.map(a => `${a.timestamp}|${a.joint || ""}|${a.message || ""}`));
        const events = [];

        for (const d of detections) {
            const t = nearestTelemetry(d.timestamp, telemetry);
            const relatedAlert = alerts.find(a =>
                String(a.joint || "") === String(d.joint || "") &&
                Math.abs(new Date(a.timestamp).getTime() - new Date(d.timestamp).getTime()) < 10000
            );
            events.push({
                timestamp: d.timestamp,
                solution_area: "AI Vision / Joint Inspection",
                joint: d.joint || "Unassigned",
                detection: d.detection || "normal",
                confidence: d.confidence,
                severity: relatedAlert?.severity || (String(d.status).toUpperCase() === "DAMAGED" ? "WARNING" : "NORMAL"),
                encoder_pulses: t.encoder_pulses,
                temperature: t.temperature,
                humidity: t.humidity,
                vibration_pulses: t.vibration_pulses,
                acoustic_pulses: t.acoustic_pulses,
                acoustic_raw: t.acoustic_raw,
                current_amps: t.current_amps,
                remarks: abnormalityRemark({ ...d, ...t, severity: relatedAlert?.severity }),
                maintenance_action: maintenanceAction({ ...d, ...t, severity: relatedAlert?.severity })
            });
        }

        for (const a of alerts) {
            const key = `${a.timestamp}|${a.joint || ""}|${a.message || ""}`;
            if (alertKeys.has(key)) {
                const hasCloseDetection = detections.some(d =>
                    String(d.joint || "") === String(a.joint || "") &&
                    Math.abs(new Date(d.timestamp).getTime() - new Date(a.timestamp).getTime()) < 10000
                );
                if (hasCloseDetection) continue;
            }
            const t = nearestTelemetry(a.timestamp, telemetry);
            events.push({
                timestamp: a.timestamp,
                solution_area: "Condition Monitoring / Alert",
                joint: a.joint || "System",
                detection: "",
                confidence: "",
                severity: a.severity || "WARNING",
                encoder_pulses: t.encoder_pulses,
                temperature: t.temperature,
                humidity: t.humidity,
                vibration_pulses: t.vibration_pulses,
                acoustic_pulses: t.acoustic_pulses,
                acoustic_raw: t.acoustic_raw,
                current_amps: t.current_amps,
                remarks: `${a.message || "Abnormal condition recorded"}. ${abnormalityRemark({ ...a, ...t })}`,
                maintenance_action: maintenanceAction({ ...a, ...t })
            });
        }

        events.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

        const abnormalCount = events.filter(e => String(e.severity).toUpperCase() !== "NORMAL").length;
        const report = {
            system: "BELTSENTINEL AI",
            report_type: "Maintenance & Conveyor Health Report",
            generated_at: new Date().toISOString(),
            operating_mode: health.mode || window.latestHealth?.mode || "LIVE_ESP32",
            summary: {
                telemetry_records: telemetry.length,
                ai_detections: detections.length,
                alerts: alerts.length,
                critical_alerts: alerts.filter(a => String(a.severity).toUpperCase() === "CRITICAL").length,
                abnormality_events: abnormalCount,
                forecast_risk: prediction.available ? prediction.forecast_score : null,
                forecast_level: prediction.forecast_level || "COLLECTING",
                trend_direction: prediction.trend_direction || "COLLECTING",
                inspection_horizon: prediction.inspection_horizon || "Collecting history",
                current_joint: twin.current_joint || window.latestCurrentJoint?.name || "Unknown"
            },
            solution_coverage: [
                "AI vision inspection",
                "IoT telemetry monitoring",
                "Sensor-fusion risk assessment",
                "Five-joint localization",
                "Predictive health trend analysis",
                "Maintenance guidance",
                "Historical event reporting"
            ],
            joint_status: Array.isArray(twin.joints) ? twin.joints : [],
            maintenance_recommendations: maintenance,
            events
        };
        cachedReport = report;
        return report;
    }

    function renderMaintenancePanel(report) {
        let panel = document.getElementById("maintenance-report-panel");
        if (!panel) return;
        const events = (report.events || []).slice(0, 30);
        panel.querySelector("#maintenance-report-count").textContent = `${report.summary.abnormality_events} abnormal events`;
        const body = panel.querySelector("#maintenance-report-body");
        body.innerHTML = events.length ? events.map(e => `
            <tr>
                <td>${esc(dateText(e.timestamp))}</td>
                <td>${esc(e.joint)}</td>
                <td>${esc((e.detection || "Condition").replace(/_/g, " "))}</td>
                <td>${esc(e.severity)}</td>
                <td>${esc(e.remarks)}</td>
                <td>${esc(e.maintenance_action)}</td>
            </tr>
        `).join("") : `<tr><td colspan="6" class="empty-state">No abnormality events recorded.</td></tr>`;
    }

    async function refreshMaintenanceReport() {
        try {
            const report = await getReport();
            renderMaintenancePanel(report);
        } catch (error) {
            console.error("Maintenance report error:", error);
        }
    }

    async function exportMaintenanceJSON() {
        const report = cachedReport || await getReport();
        downloadBlob("beltsentinel_maintenance_report.json", JSON.stringify(report, null, 2), "application/json;charset=utf-8");
    }

    async function exportMaintenanceCSV() {
        const report = cachedReport || await getReport();
        const headers = ["Timestamp","Solution Area","Joint","Detection","Confidence %","Severity","Encoder Pulses","Temperature °C","Humidity %","Vibration Pulses","Acoustic Pulses","Acoustic Raw","Motor Current A","Remarks","Maintenance Action"];
        const rows = (report.events || []).map(e => [
            e.timestamp, e.solution_area, e.joint, e.detection || "", e.confidence === "" ? "" : num(e.confidence, 1), e.severity,
            e.encoder_pulses, e.temperature, e.humidity, e.vibration_pulses, e.acoustic_pulses, e.acoustic_raw, e.current_amps,
            e.remarks, e.maintenance_action
        ]);
        const csv = [headers, ...rows].map(row => row.map(csvCell).join(",")).join("\r\n");
        downloadBlob("beltsentinel_maintenance_report.csv", csv, "text/csv;charset=utf-8");
    }

    function ensureUI() {
        const page = document.getElementById("page-reports");
        if (!page || document.getElementById("maintenance-report-panel")) return;

        const header = page.querySelector(".report-header");
        if (header) {
            const controls = document.createElement("div");
            controls.className = "maintenance-export-controls";
            controls.innerHTML = `
                <button class="outline-button" id="maintenance-export-csv">Export CSV</button>
                <button class="primary-button" id="maintenance-export-json">Export JSON</button>
            `;
            const oldButton = header.querySelector("button[onclick='downloadReport()']");
            if (oldButton) oldButton.replaceWith(controls);
        }

        const panel = document.createElement("div");
        panel.id = "maintenance-report-panel";
        panel.className = "panel maintenance-report-panel";
        panel.innerHTML = `
            <div class="panel-header">
                <div>
                    <span class="eyebrow">MAINTENANCE RECORD</span>
                    <h3>Abnormality & Maintenance Log</h3>
                    <p>Detected abnormalities are identified in the Remarks column with the associated maintenance action.</p>
                </div>
                <span class="chart-tag" id="maintenance-report-count">0 abnormal events</span>
            </div>
            <div class="table-container maintenance-report-table-wrap">
                <table class="data-table maintenance-report-table">
                    <thead><tr>
                        <th>TIME</th><th>JOINT</th><th>DETECTION</th><th>SEVERITY</th><th>REMARKS</th><th>MAINTENANCE ACTION</th>
                    </tr></thead>
                    <tbody id="maintenance-report-body"><tr><td colspan="6" class="empty-state">Loading maintenance history...</td></tr></tbody>
                </table>
            </div>
        `;
        const grid = page.querySelector(".report-grid");
        if (grid) grid.insertAdjacentElement("afterend", panel);
        else page.appendChild(panel);

        document.getElementById("maintenance-export-csv")?.addEventListener("click", exportMaintenanceCSV);
        document.getElementById("maintenance-export-json")?.addEventListener("click", exportMaintenanceJSON);
    }

    document.addEventListener("DOMContentLoaded", () => {
        ensureUI();
        refreshMaintenanceReport();
        window.setInterval(() => {
            if (document.getElementById("page-reports")?.style.display !== "none") refreshMaintenanceReport();
        }, 15000);
    });

    window.BeltSentinelMaintenanceReport = {
        refresh: refreshMaintenanceReport,
        exportCSV: exportMaintenanceCSV,
        exportJSON: exportMaintenanceJSON
    };
})();
