/* === AWS Cost Optimizer — Tabbed Dashboard JS === */

let allResources = [];
let currentFilter = "all";
let searchQuery = "";
let sortColumn = "waste";
let sortDirection = "desc";
let trendChart = null;
let breakdownChart = null;
let serviceBarChart = null;

Chart.defaults.color = "#94a3b8";
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 12;

const COLORS = {
    EBS: { bg: "rgba(99,102,241,0.15)", border: "#6366f1", solid: "#818cf8" },
    EC2: { bg: "rgba(6,182,212,0.15)", border: "#06b6d4", solid: "#22d3ee" },
    ElasticIP: { bg: "rgba(245,158,11,0.15)", border: "#f59e0b", solid: "#fbbf24" },
    Snapshot: { bg: "rgba(236,72,153,0.15)", border: "#ec4899", solid: "#f472b6" },
};

// === INIT ===
document.addEventListener("DOMContentLoaded", () => {
    initParticles();
    loadDashboard();
    setupFilters();
    setupSorting();
});

// === TAB SWITCHING ===
function switchTab(tabId) {
    document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
    const tab = document.getElementById("tab-" + tabId);
    const nav = document.getElementById("nav-" + tabId);
    if (tab) tab.classList.add("active");
    if (nav) nav.classList.add("active");
    // Lazy-load data when switching to specific tabs
    if (tabId === "dashboard" || tabId === "analytics") loadDashboard();
    if (tabId === "settings") loadSettings();
    if (tabId === "alerts") loadAlerts();
}

// === PARTICLE BACKGROUND ===
function initParticles() {
    const canvas = document.getElementById("particle-canvas");
    const ctx = canvas.getContext("2d");
    let particles = [];
    const PARTICLE_COUNT = 80;

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener("resize", resize);

    for (let i = 0; i < PARTICLE_COUNT; i++) {
        particles.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            vx: (Math.random() - 0.5) * 0.3,
            vy: (Math.random() - 0.5) * 0.3,
            r: Math.random() * 1.5 + 0.5,
            alpha: Math.random() * 0.4 + 0.1,
        });
    }

    function draw() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        // Draw connections
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 150) {
                    ctx.beginPath();
                    ctx.strokeStyle = `rgba(99,102,241,${0.06 * (1 - dist / 150)})`;
                    ctx.lineWidth = 0.5;
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.stroke();
                }
            }
        }
        // Draw particles
        particles.forEach(p => {
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(99,102,241,${p.alpha})`;
            ctx.fill();
            p.x += p.vx;
            p.y += p.vy;
            if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
            if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
        });
        requestAnimationFrame(draw);
    }
    draw();
}

// === DATA LOADING ===
async function loadDashboard() {
    try {
        await Promise.all([loadSummary(), loadTrendChart(), loadResources(), loadHistory(), loadBudget()]);
    } catch (e) { console.error("Load error:", e); }
}

async function loadSummary() {
    try {
        const res = await fetch("/api/summary");
        const d = await res.json();
        animateValue("stat-waste", d.total_waste, "$");
        animateValue("stat-resources", d.resources_found);
        animateValue("stat-annual", d.annual_projection, "$");
        animateValue("stat-scans", d.total_scans);
        // Home tab stats
        animateValue("home-waste", d.total_waste, "$");
        animateValue("home-resources", d.resources_found);
        animateValue("home-annual", d.annual_projection, "$");
        animateValue("home-scans", d.total_scans);
        // Trend
        const trendEl = document.getElementById("stat-trend");
        if (d.trend_change !== 0) {
            const up = d.trend_change > 0;
            trendEl.className = "stat-trend " + (up ? "up" : "down");
            trendEl.textContent = (up ? "\u25b2" : "\u25bc") + " $" + Math.abs(d.trend_change).toFixed(2) + " vs last scan";
        } else { trendEl.textContent = ""; }
        // Status
        const st = document.getElementById("sidebar-status-text");
        if (st) st.textContent = d.last_scan ? "Last scan: " + formatTimeAgo(d.last_scan) : "No scans yet";
        // Breakdown + analytics
        renderBreakdownChart(d.breakdown);
        renderServiceBarChart(d.breakdown);
        // Projections
        setProj(d.total_waste);
        // Severity from resources
        updateSeverity();
    } catch (e) { console.error("Summary error:", e); }
}

function setProj(monthly) {
    const pm = document.getElementById("proj-monthly");
    const pq = document.getElementById("proj-quarterly");
    const pa = document.getElementById("proj-annual");
    if (pm) pm.textContent = "$" + monthly.toFixed(2);
    if (pq) pq.textContent = "$" + (monthly * 3).toFixed(2);
    if (pa) pa.textContent = "$" + (monthly * 12).toFixed(2);
}

function updateSeverity() {
    let high = 0, med = 0, low = 0;
    allResources.forEach(r => {
        if (r.severity === "high") high++;
        else if (r.severity === "medium") med++;
        else low++;
    });
    const total = allResources.length || 1;
    const hb = document.getElementById("sev-high-bar");
    const mb = document.getElementById("sev-med-bar");
    const lb = document.getElementById("sev-low-bar");
    if (hb) hb.style.width = (high / total * 100) + "%";
    if (mb) mb.style.width = (med / total * 100) + "%";
    if (lb) lb.style.width = (low / total * 100) + "%";
    const hc = document.getElementById("sev-high-count");
    const mc = document.getElementById("sev-med-count");
    const lc = document.getElementById("sev-low-count");
    if (hc) hc.textContent = high;
    if (mc) mc.textContent = med;
    if (lc) lc.textContent = low;
}

// === BUDGET ===
async function loadBudget() {
    try {
        const res = await fetch("/api/budget");
        const b = await res.json();
        const card = document.getElementById("budget-card");
        if (!card) return;

        const pct = Math.min(b.percentage, 200);
        const exceeded = b.exceeded;

        // Toggle exceeded class
        card.classList.toggle("exceeded", exceeded);

        // Circular gauge
        const circumference = 326.73;
        const gaugeFill = document.getElementById("budget-gauge-fill");
        const gaugeOffset = circumference - (Math.min(pct, 100) / 100) * circumference;
        if (gaugeFill) gaugeFill.style.strokeDashoffset = gaugeOffset;

        // Percentage text
        const pctEl = document.getElementById("budget-pct");
        if (pctEl) pctEl.textContent = b.percentage.toFixed(0) + "%";

        // Status badge
        const badge = document.getElementById("budget-status-badge");
        if (badge) {
            badge.className = "budget-status-badge";
            if (exceeded) { badge.classList.add("exceeded"); badge.textContent = "EXCEEDED"; }
            else if (b.percentage >= 75) { badge.classList.add("warning"); badge.textContent = "WARNING"; }
            else { badge.classList.add("ok"); badge.textContent = "OK"; }
        }

        // Progress bar
        const barFill = document.getElementById("budget-bar-fill");
        if (barFill) barFill.style.width = Math.min(pct, 100) + "%";

        // Marker position (threshold line)
        const marker = document.getElementById("budget-bar-marker");
        const markerLabel = document.getElementById("budget-marker-label");
        if (marker) {
            const markerPos = exceeded ? (b.threshold / b.total_waste) * 100 : 100;
            marker.style.left = Math.min(markerPos, 100) + "%";
        }
        if (markerLabel) markerLabel.textContent = "$" + b.threshold.toFixed(0);

        // Values
        const we = document.getElementById("budget-waste");
        const te = document.getElementById("budget-threshold");
        const oe = document.getElementById("budget-overage");
        if (we) we.textContent = "$" + b.total_waste.toFixed(2);
        if (te) te.textContent = "$" + b.threshold.toFixed(2);
        if (oe) oe.textContent = exceeded ? "+$" + b.overage.toFixed(2) : "$0.00";

        // Alert box
        const alertIcon = document.getElementById("budget-alert-icon");
        const alertText = document.getElementById("budget-alert-text");
        if (exceeded) {
            if (alertIcon) alertIcon.textContent = "\u26a0\ufe0f";
            if (alertText) alertText.textContent = "Over budget!";
        } else if (b.percentage >= 75) {
            if (alertIcon) alertIcon.textContent = "\u26a0\ufe0f";
            if (alertText) alertText.textContent = "Approaching limit";
        } else {
            if (alertIcon) alertIcon.textContent = "\u2705";
            if (alertText) alertText.textContent = "Under budget";
        }
    } catch (e) { console.error("Budget error:", e); }
}

// === CHARTS ===
async function loadTrendChart() {
    try {
        const res = await fetch("/api/cost-trend");
        const data = await res.json();
        renderTrendChart(data);
    } catch (e) { console.error("Trend error:", e); }
}

function renderTrendChart(data) {
    const ctx = document.getElementById("trendChart");
    if (!ctx) return;
    if (trendChart) trendChart.destroy();
    const labels = data.map(d => new Date(d.timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric" }));
    const values = data.map(d => d.total_waste_usd);
    const counts = data.map(d => d.resources_found);
    const gradient = ctx.getContext("2d").createLinearGradient(0, 0, 0, 250);
    gradient.addColorStop(0, "rgba(99,102,241,0.25)");
    gradient.addColorStop(1, "rgba(99,102,241,0)");
    trendChart = new Chart(ctx, {
        type: "line",
        data: { labels, datasets: [
            { label: "Monthly Waste ($)", data: values, borderColor: "#6366f1", backgroundColor: gradient, borderWidth: 2.5, fill: true, tension: 0.4, pointBackgroundColor: "#6366f1", pointBorderColor: "#0d1117", pointBorderWidth: 2, pointRadius: 4, pointHoverRadius: 7 },
            { label: "Resources", data: counts, borderColor: "#06b6d4", borderWidth: 2, borderDash: [5, 5], fill: false, tension: 0.4, pointRadius: 3, yAxisID: "y1" }
        ]},
        options: { responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
            plugins: { legend: { position: "top", labels: { usePointStyle: true, padding: 16, font: { size: 11, weight: "600" } } },
                tooltip: { backgroundColor: "rgba(6,8,15,0.95)", borderColor: "rgba(99,102,241,0.3)", borderWidth: 1, padding: 12, cornerRadius: 8 } },
            scales: { x: { grid: { color: "rgba(99,102,241,0.05)" } }, y: { grid: { color: "rgba(99,102,241,0.05)" }, ticks: { callback: v => "$" + v } }, y1: { position: "right", grid: { display: false } } }
        }
    });
}

function renderBreakdownChart(breakdown) {
    const ctx = document.getElementById("breakdownChart");
    if (!ctx) return;
    if (breakdownChart) breakdownChart.destroy();
    const labels = Object.keys(breakdown);
    const values = Object.values(breakdown);
    if (!labels.length) return;
    breakdownChart = new Chart(ctx, {
        type: "doughnut",
        data: { labels, datasets: [{ data: values, backgroundColor: labels.map(l => COLORS[l]?.bg || "rgba(148,163,184,0.15)"), borderColor: labels.map(l => COLORS[l]?.border || "#94a3b8"), borderWidth: 2, hoverOffset: 8 }] },
        options: { responsive: true, maintainAspectRatio: false, cutout: "65%",
            plugins: { legend: { position: "bottom", labels: { usePointStyle: true, padding: 14, font: { size: 11, weight: "600" } } },
                tooltip: { backgroundColor: "rgba(6,8,15,0.95)", borderColor: "rgba(99,102,241,0.3)", borderWidth: 1, padding: 12, cornerRadius: 8,
                    callbacks: { label: c => { const t = c.dataset.data.reduce((a, b) => a + b, 0); return " " + c.label + ": $" + c.parsed.toFixed(2) + " (" + ((c.parsed / t) * 100).toFixed(1) + "%)"; } } } }
        }
    });
}

function renderServiceBarChart(breakdown) {
    const ctx = document.getElementById("serviceBarChart");
    if (!ctx) return;
    if (serviceBarChart) serviceBarChart.destroy();
    const labels = Object.keys(breakdown);
    const values = Object.values(breakdown);
    if (!labels.length) return;
    serviceBarChart = new Chart(ctx, {
        type: "bar",
        data: { labels, datasets: [{ label: "Waste ($)", data: values, backgroundColor: labels.map(l => COLORS[l]?.bg || "rgba(148,163,184,0.15)"), borderColor: labels.map(l => COLORS[l]?.border || "#94a3b8"), borderWidth: 2, borderRadius: 6, barPercentage: 0.6 }] },
        options: { responsive: true, maintainAspectRatio: false, indexAxis: "y",
            plugins: { legend: { display: false }, tooltip: { backgroundColor: "rgba(6,8,15,0.95)", padding: 12, cornerRadius: 8, callbacks: { label: c => " $" + c.parsed.x.toFixed(2) } } },
            scales: { x: { grid: { color: "rgba(99,102,241,0.05)" }, ticks: { callback: v => "$" + v } }, y: { grid: { display: false } } }
        }
    });
}

// === RESOURCES ===
async function loadResources() {
    try {
        const res = await fetch("/api/latest-scan");
        if (!res.ok) { showEmptyTable(); return; }
        const data = await res.json();
        allResources = data.resources || [];
        updateResourceCounts();
        updateSeverity();
        renderTable(allResources);
    } catch (e) { showEmptyTable(); }
}

function updateResourceCounts() {
    const counts = { EBS: 0, EC2: 0, ElasticIP: 0, Snapshot: 0 };
    allResources.forEach(r => { if (counts[r.resource_type] !== undefined) counts[r.resource_type]++; });
    const ce = document.getElementById("count-ebs"); if (ce) ce.textContent = counts.EBS;
    const cc = document.getElementById("count-ec2"); if (cc) cc.textContent = counts.EC2;
    const ci = document.getElementById("count-eip"); if (ci) ci.textContent = counts.ElasticIP;
    const cs = document.getElementById("count-snap"); if (cs) cs.textContent = counts.Snapshot;
}

function renderTable(resources) {
    const tbody = document.getElementById("resources-tbody");
    if (!resources.length) { showEmptyTable(); return; }
    let filtered = currentFilter === "all" ? resources : resources.filter(r => r.resource_type === currentFilter);
    if (searchQuery) {
        const q = searchQuery.toLowerCase();
        filtered = filtered.filter(r => (r.resource_id + " " + (r.detail || "") + " " + r.resource_type).toLowerCase().includes(q));
    }
    const sorted = [...filtered].sort((a, b) => {
        let av, bv;
        switch (sortColumn) {
            case "type": av = a.resource_type; bv = b.resource_type; break;
            case "id": av = a.resource_id; bv = b.resource_id; break;
            case "detail": av = a.detail || ""; bv = b.detail || ""; break;
            case "waste": av = a.waste_usd; bv = b.waste_usd; break;
            case "severity": const so = { high: 3, medium: 2, low: 1 }; av = so[a.severity] || 0; bv = so[b.severity] || 0; break;
            default: av = a.waste_usd; bv = b.waste_usd;
        }
        if (typeof av === "string") return sortDirection === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
        return sortDirection === "asc" ? av - bv : bv - av;
    });
    if (!sorted.length) { tbody.innerHTML = '<tr class="empty-row"><td colspan="6"><div class="empty-state"><span class="empty-icon">🔍</span><p>No matching resources</p></div></td></tr>'; return; }
    tbody.innerHTML = sorted.map(r => {
        const tc = { EBS: "type-ebs", EC2: "type-ec2", ElasticIP: "type-eip", Snapshot: "type-snapshot" }[r.resource_type] || "";
        const ti = { EBS: "\ud83d\udcbe", EC2: "\ud83d\udda5\ufe0f", ElasticIP: "\ud83c\udf10", Snapshot: "\ud83d\udcf8" }[r.resource_type] || "\ud83d\udce6";
        const si = r.severity === "high" ? "\ud83d\udd34" : r.severity === "medium" ? "\ud83d\udfe1" : "\ud83d\udfe2";
        return '<tr><td><span class="resource-type ' + tc + '">' + ti + " " + r.resource_type + '</span></td><td><span class="resource-id">' + r.resource_id + "</span></td><td>" + (r.detail || "-") + '</td><td class="cost-cell">$' + r.waste_usd.toFixed(2) + '</td><td><span class="severity-badge severity-' + r.severity + '">' + si + " " + r.severity + '</span></td><td><span class="status-badge status-' + r.status + '">' + r.status + "</span></td></tr>";
    }).join("");
}

function showEmptyTable() {
    document.getElementById("resources-tbody").innerHTML = '<tr class="empty-row"><td colspan="6"><div class="empty-state"><span class="empty-icon">\ud83d\udced</span><p>No scan data yet</p><code>python main.py --scan</code></div></td></tr>';
}

// === HISTORY ===
async function loadHistory() {
    try {
        const res = await fetch("/api/scans");
        const scans = await res.json();
        const el = document.getElementById("history-timeline");
        if (!scans.length) { el.innerHTML = '<div class="empty-state"><span class="empty-icon">\ud83d\udccb</span><p>No scan history</p></div>'; return; }
        el.innerHTML = scans.map((s, i) => {
            const d = new Date(s.timestamp);
            const fmt = d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" });
            return '<div class="history-card" onclick="loadScanDetail(' + s.id + ')"><div class="history-card-left"><span class="history-card-number">#' + (scans.length - i) + '</span><div><div class="history-card-date">' + fmt + '</div><div class="history-card-meta">' + s.resources_found + ' resources detected</div></div></div><div class="history-card-cost">$' + s.total_waste_usd.toFixed(2) + "</div></div>";
        }).join("");
    } catch (e) { console.error("History error:", e); }
}

async function loadScanDetail(id) {
    try {
        const res = await fetch("/api/scan/" + id + "/resources");
        allResources = await res.json();
        currentFilter = "all";
        searchQuery = "";
        updateFilterButtons();
        updateResourceCounts();
        updateSeverity();
        renderTable(allResources);
        switchTab("resources");
    } catch (e) { console.error("Scan detail error:", e); }
}

// === FILTERS & SORT ===
function setupFilters() {
    document.querySelectorAll(".filter-btn").forEach(btn => {
        btn.addEventListener("click", () => { currentFilter = btn.dataset.filter; updateFilterButtons(); renderTable(allResources); });
    });
}
function updateFilterButtons() {
    document.querySelectorAll(".filter-btn").forEach(btn => btn.classList.toggle("active", btn.dataset.filter === currentFilter));
}
function setupSorting() {
    document.querySelectorAll(".sortable").forEach(th => {
        th.addEventListener("click", () => { const c = th.dataset.sort; if (sortColumn === c) sortDirection = sortDirection === "asc" ? "desc" : "asc"; else { sortColumn = c; sortDirection = "desc"; } renderTable(allResources); });
    });
}
function onSearch(val) { searchQuery = val; renderTable(allResources); }

// === EXPORT ===
function exportCSV() {
    if (!allResources.length) { alert("No data to export."); return; }
    const h = ["Type", "Resource ID", "Detail", "Cost/Month", "Severity", "Status", "Region"];
    const rows = allResources.map(r => [r.resource_type, r.resource_id, '"' + (r.detail || "").replace(/"/g, '""') + '"', r.waste_usd.toFixed(2), r.severity, r.status, r.region]);
    const csv = [h.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "aws-waste-" + new Date().toISOString().slice(0, 10) + ".csv"; a.click();
}

// === HELPERS ===
function formatTimeAgo(iso) {
    const ms = Date.now() - new Date(iso).getTime();
    const m = Math.floor(ms / 60000), h = Math.floor(ms / 3600000), d = Math.floor(ms / 86400000);
    if (m < 1) return "just now"; if (m < 60) return m + "m ago"; if (h < 24) return h + "h ago"; if (d < 7) return d + "d ago";
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
function animateValue(id, target, prefix) {
    prefix = prefix || "";
    const el = document.getElementById(id);
    if (!el) return;
    const isFloat = typeof target === "number" && !Number.isInteger(target);
    const dur = 800, start = performance.now();
    function update(now) {
        const p = Math.min((now - start) / dur, 1), e = 1 - Math.pow(1 - p, 3), v = target * e;
        el.textContent = (isFloat || prefix === "$") ? prefix + v.toFixed(2) : prefix + Math.round(v);
        if (p < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}

// === PASSWORD TOGGLE ===
function togglePassword(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const isHidden = input.type === "password";
    input.type = isHidden ? "text" : "password";
    const eyeOpen = btn.querySelector(".eye-open");
    const eyeClosed = btn.querySelector(".eye-closed");
    if (eyeOpen) eyeOpen.style.display = isHidden ? "none" : "block";
    if (eyeClosed) eyeClosed.style.display = isHidden ? "block" : "none";
}

// === SETTINGS ===
async function loadSettings() {
    try {
        const res = await fetch("/api/settings");
        const s = await res.json();

        // AWS
        const awsKey = document.getElementById("set-aws-key");
        const awsSecret = document.getElementById("set-aws-secret");
        const awsRegion = document.getElementById("set-aws-region");
        if (awsKey) awsKey.value = s.aws.access_key || "";
        if (awsSecret) awsSecret.value = s.aws.secret_key || "";
        if (awsRegion) awsRegion.value = s.aws.region || "us-east-1";

        const awsStatus = document.getElementById("aws-status");
        if (awsStatus) {
            awsStatus.className = "settings-status " + (s.aws.configured ? "configured" : "not-configured");
            awsStatus.textContent = s.aws.configured ? "Configured" : "Not configured";
        }

        // Email
        const sh = document.getElementById("set-smtp-host");
        const sp = document.getElementById("set-smtp-port");
        const su = document.getElementById("set-smtp-user");
        const spw = document.getElementById("set-smtp-password");
        const sf = document.getElementById("set-alert-from");
        const st = document.getElementById("set-alert-to");
        if (sh) sh.value = s.email.smtp_host || "";
        if (sp) sp.value = s.email.smtp_port || "";
        if (su) su.value = s.email.smtp_user || "";
        if (spw) spw.value = s.email.smtp_password || "";
        if (sf) sf.value = s.email.alert_from || "";
        if (st) st.value = s.email.alert_to || "";

        const emailStatus = document.getElementById("email-status");
        if (emailStatus) {
            emailStatus.className = "settings-status " + (s.email.configured ? "configured" : "not-configured");
            emailStatus.textContent = s.email.configured ? "Configured" : "Not configured";
        }

        // Budget
        const budgetInput = document.getElementById("set-budget");
        if (budgetInput) budgetInput.value = s.budget.threshold;

        // App
        const snapAge = document.getElementById("set-snap-age");
        const cpuThresh = document.getElementById("set-cpu-thresh");
        const ollama = document.getElementById("set-ollama");
        const demoMode = document.getElementById("set-demo-mode");
        if (snapAge) snapAge.value = s.app.snapshot_age_days || "";
        if (cpuThresh) cpuThresh.value = s.app.ec2_cpu_threshold || "";
        if (ollama) ollama.value = s.app.ollama_model || "";
        if (demoMode) demoMode.checked = s.app.use_demo_data;

    } catch (e) { console.error("Settings load error:", e); }
}

async function saveSettings() {
    const statusEl = document.getElementById("settings-save-status");
    const btn = document.getElementById("save-settings-btn");
    if (btn) btn.disabled = true;
    if (statusEl) { statusEl.className = "settings-save-status"; statusEl.textContent = "Saving..."; }

    const data = {
        aws_access_key: document.getElementById("set-aws-key")?.value || "",
        aws_secret_key: document.getElementById("set-aws-secret")?.value || "",
        aws_region: document.getElementById("set-aws-region")?.value || "",
        smtp_host: document.getElementById("set-smtp-host")?.value || "",
        smtp_port: document.getElementById("set-smtp-port")?.value || "",
        smtp_user: document.getElementById("set-smtp-user")?.value || "",
        smtp_password: document.getElementById("set-smtp-password")?.value || "",
        alert_from: document.getElementById("set-alert-from")?.value || "",
        alert_to: document.getElementById("set-alert-to")?.value || "",
        budget_threshold: document.getElementById("set-budget")?.value || "",
        snapshot_age_days: document.getElementById("set-snap-age")?.value || "",
        ec2_cpu_threshold: document.getElementById("set-cpu-thresh")?.value || "",
        ollama_model: document.getElementById("set-ollama")?.value || "",
        use_demo_data: document.getElementById("set-demo-mode")?.checked || false,
    };

    try {
        const res = await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if (result.status === "ok") {
            if (statusEl) { statusEl.className = "settings-save-status success"; statusEl.textContent = "\u2705 Settings saved successfully!"; }
            setTimeout(() => loadSettings(), 500);
        } else {
            if (statusEl) { statusEl.className = "settings-save-status error"; statusEl.textContent = "\u274c " + result.message; }
        }
    } catch (e) {
        if (statusEl) { statusEl.className = "settings-save-status error"; statusEl.textContent = "\u274c Failed to save"; }
    }
    if (btn) btn.disabled = false;
}

// === RUN SCAN ===
async function runScan() {
    const btn = document.getElementById("run-scan-btn");
    const originalText = btn ? btn.innerHTML : "";
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<svg class="spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/></svg> Scanning...';
    }

    try {
        const res = await fetch("/api/scan/run", { method: "POST" });
        const result = await res.json();
        if (result.status === "ok") {
            // Reload dashboard data
            loadDashboard();
            if (document.getElementById("tab-history").classList.contains("active")) loadHistory();
        } else {
            alert("Scan failed: " + result.message);
        }
    } catch (e) {
        console.error("Run scan error:", e);
        alert("Failed to run scan. Check console for details.");
    }

    if (btn) {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// === ALERTS ===
async function loadAlerts() {
    try {
        const res = await fetch("/api/alerts");
        const alerts = await res.json();
        const el = document.getElementById("alerts-timeline");
        if (!el) return;

        if (!alerts.length) {
            el.innerHTML = '<div class="empty-state"><span class="empty-icon">\ud83d\udd14</span><p>No alerts yet</p><code>Alerts appear when budget threshold is exceeded</code></div>';
            return;
        }

        el.innerHTML = alerts.map(a => {
            const isExceeded = a.alert_type === "budget_exceeded";
            const cls = isExceeded ? "alert-exceeded" : "alert-ok";
            const icon = isExceeded ? "\ud83d\udea8" : "\u2705";
            const d = new Date(a.timestamp);
            const fmt = d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" });
            const emailBadge = a.email_sent
                ? '<span class="alert-email-badge alert-email-sent">Email Sent</span>'
                : '<span class="alert-email-badge alert-email-failed">No Email</span>';
            return '<div class="alert-card ' + cls + '">'
                + '<div class="alert-card-icon">' + icon + '</div>'
                + '<div class="alert-card-body">'
                + '<div class="alert-card-message">' + (a.message || "Budget alert") + '</div>'
                + '<div class="alert-card-time">' + fmt + '</div>'
                + '</div>'
                + '<div class="alert-card-right">'
                + '<span class="alert-card-amount">$' + a.total_waste.toFixed(2) + '</span>'
                + emailBadge
                + '</div></div>';
        }).join("");
    } catch (e) { console.error("Alerts error:", e); }
}
