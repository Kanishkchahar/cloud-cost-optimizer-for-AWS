/* ======================================================
   Cloud Cost Optimizer — Dashboard JS
   Features: Welcome page, stacked bar chart (AWS-style),
   tab navigation, budget checker, anomaly detection.
   ====================================================== */

const SVC_COLORS = ['#fbbf24', '#60a5fa', '#34d399', '#a78bfa', '#22d3ee', '#f87171'];
const SVC_COLORS_DIM = [
    'rgba(251,191,36,0.7)', 'rgba(96,165,250,0.7)', 'rgba(52,211,153,0.7)',
    'rgba(167,139,250,0.7)', 'rgba(34,211,238,0.7)', 'rgba(248,113,113,0.7)'
];
let allFlaggedData = [];

// ============= WELCOME PAGE =============
function enterDashboard() {
    // Switch to Overview tab
    const tabBar = document.getElementById('tab-bar');
    if (tabBar) {
        const overviewBtn = tabBar.querySelector('[data-tab="overview"]');
        if (overviewBtn) overviewBtn.click();
    }
}

// ============= TAB NAVIGATION =============
document.addEventListener('DOMContentLoaded', () => {
    const tabBar = document.getElementById('tab-bar');
    if (!tabBar) return;

    tabBar.addEventListener('click', e => {
        const btn = e.target.closest('.tab');
        if (!btn) return;
        const tabId = btn.dataset.tab;

        tabBar.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        btn.classList.add('active');
        const content = document.getElementById('content-' + tabId);
        if (content) content.classList.add('active');

        history.replaceState(null, '', '#' + tabId);
    });

    // Restore tab from URL hash
    const hash = window.location.hash.replace('#', '');
    if (hash) {
        const btn = tabBar.querySelector(`[data-tab="${hash}"]`);
        if (btn) btn.click();
    }

    // Keyboard shortcuts: 1-4 to switch tabs
    document.addEventListener('keydown', e => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        const map = { '1': 'home', '2': 'overview', '3': 'services', '4': 'recommendations', '5': 'anomalies', '6': 'budget' };
        if (map[e.key]) {
            const btn = tabBar.querySelector(`[data-tab="${map[e.key]}"]`);
            if (btn) btn.click();
        }
    });

    // Filter tabs within recommendations
    const filterTabs = document.getElementById('filter-tabs');
    if (!filterTabs) return;
    filterTabs.addEventListener('click', e => {
        const btn = e.target.closest('.ftab');
        if (!btn) return;
        filterTabs.querySelectorAll('.ftab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const filter = btn.dataset.filter;
        if (filter === 'all') {
            renderTable(allFlaggedData);
        } else {
            renderTable(allFlaggedData.filter(r => {
                if (filter === 'idle') return r.issue.includes('Idle');
                if (filter === 'unattached') return r.issue.includes('Unattached');
                return !r.issue.includes('Idle') && !r.issue.includes('Unattached');
            }));
        }
    });
});

// ============= STATUS INDICATOR =============
function setStatus(state, text) {
    const dot = document.getElementById('status-dot');
    const txt = document.getElementById('status-text');
    if (dot) {
        dot.className = 'status-dot';
        if (state === 'ok') dot.classList.add('connected');
        if (state === 'error') dot.classList.add('error');
    }
    if (txt) txt.textContent = text;
}

let fetchDone = 0;
const TOTAL_FETCHES = 3;

function trackFetch() {
    fetchDone++;
    if (fetchDone >= TOTAL_FETCHES) {
        setStatus('ok', 'All systems operational');
    }
}

// ============= INIT DASHBOARD (called on page load) =============
function initDashboard() {
    fetchSummary();
    fetchRecommendations();
    fetchStackedChart();
    fetchAnomalies();
    fetchInstances();
    fetchForecast();
    fetchRegionChart();
}

// Auto-init on load
document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
    const wrapper = document.getElementById('dashboard-wrapper');
    if (wrapper) wrapper.classList.add('loaded');
});

// ============= FETCH: SUMMARY =============
function fetchSummary() {
    fetch('http://127.0.0.1:5000/api/summary')
        .then(r => r.json())
        .then(d => {
            document.getElementById('daily').textContent = '$' + d.total_daily_cost;
            document.getElementById('monthly').textContent = '$' + d.total_monthly_cost;
            document.getElementById('savings').textContent = '$' + d.potential_savings;
            document.getElementById('flagged').textContent = d.flagged_count;

            const pct = d.total_monthly_cost > 0
                ? ((d.potential_savings / d.total_monthly_cost) * 100).toFixed(1) : 0;
            const spEl = document.getElementById('savings-pct');
            if (spEl) spEl.textContent = pct + '% of monthly spend';

            const stEl = document.getElementById('service-total-value');
            if (stEl) stEl.textContent = '$' + d.total_monthly_cost.toLocaleString();

            trackFetch();
        })
        .catch(() => {
            setStatus('error', 'API connection failed');
            trackFetch();
        });
}

// ============= FETCH: RECOMMENDATIONS =============
function fetchRecommendations() {
    fetch('http://127.0.0.1:5000/api/recommendations')
        .then(r => r.json())
        .then(data => {
            allFlaggedData = data.flagged;
            renderTable(data.flagged);
            updateFilterCounts(data.flagged);
            populateTopWaste(data.flagged);
            populateServiceBreakdown(data.flagged);
            populateFlaggedBreakdown(data.flagged);

            const recBadge = document.getElementById('tab-rec-count');
            if (recBadge) recBadge.textContent = data.flagged.length;

            const totalWaste = data.flagged.reduce((s, r) => s + r.monthly_waste, 0);
            const twEl = document.getElementById('total-waste');
            if (twEl) twEl.textContent = '$' + totalWaste.toLocaleString() + ' / month';

            trackFetch();
        })
        .catch(() => {
            setStatus('error', 'API connection failed');
            trackFetch();
        });
}

// ============= TABLE RENDERING =============
function renderTable(items) {
    const tbody = document.getElementById('table');
    tbody.innerHTML = '';
    items.forEach(r => {
        const badge = r.issue.includes('Idle') ? 'badge-purple' :
                      r.issue.includes('Unattached') ? 'badge-red' : 'badge-orange';
        const dot = r.issue.includes('Idle') ? 'dot-orange' :
                    r.issue.includes('Unattached') ? 'dot-red' : 'dot-green';
        const dtype = r.issue.includes('Idle') ? 'idle' :
                      r.issue.includes('Unattached') ? 'unattached' : 'over';
        tbody.innerHTML += `
            <tr data-type="${dtype}">
                <td class="cell-id">${r.id}</td>
                <td><span class="type-badge">${r.type}</span></td>
                <td class="cell-region">${r.region}</td>
                <td><span class="badge ${badge}"><span class="${dot}"></span>${r.issue}</span></td>
                <td>$${r.current_cost}</td>
                <td class="savings">$${r.monthly_waste}</td>
                <td class="action">→ ${r.action}</td>
            </tr>`;
    });
}

// ============= FILTER COUNTS =============
function updateFilterCounts(flagged) {
    const counts = { all: flagged.length, idle: 0, unattached: 0, over: 0 };
    flagged.forEach(r => {
        if (r.issue.includes('Idle')) counts.idle++;
        else if (r.issue.includes('Unattached')) counts.unattached++;
        else counts.over++;
    });
    const el = id => document.getElementById(id);
    if (el('fc-all')) el('fc-all').textContent = counts.all;
    if (el('fc-idle')) el('fc-idle').textContent = counts.idle;
    if (el('fc-unattached')) el('fc-unattached').textContent = counts.unattached;
    if (el('fc-over')) el('fc-over').textContent = counts.over;
}

// ============= TOP WASTE SOURCE =============
function populateTopWaste(flagged) {
    const byService = {};
    flagged.forEach(r => {
        byService[r.service] = (byService[r.service] || 0) + r.monthly_waste;
    });
    let topName = '—', topVal = 0;
    for (const [k, v] of Object.entries(byService)) {
        if (v > topVal) { topName = k; topVal = v; }
    }
    const el = document.getElementById('top-waste');
    if (el) el.textContent = topName;
    const detEl = document.getElementById('top-waste-detail');
    if (detEl) detEl.textContent = '$' + topVal.toLocaleString() + '/mo · Idle VMs';
}

// ============= SERVICE BREAKDOWN =============
function populateServiceBreakdown(flagged) {
    const services = {};
    flagged.forEach(r => {
        services[r.service] = (services[r.service] || 0) + r.current_cost;
    });
    const total = Object.values(services).reduce((a, b) => a + b, 0);
    const container = document.getElementById('service-breakdown');
    if (!container) return;
    container.innerHTML = '';
    const svcNames = { 'Compute': 'Compute (EC2)', 'Database': 'Database (RDS)', 'Storage': 'Storage (EBS/S3)' };
    let i = 0;
    for (const [name, cost] of Object.entries(services)) {
        const monthly = (cost * 30).toFixed(0);
        const pct = total > 0 ? ((cost / total) * 100).toFixed(0) : 0;
        const color = SVC_COLORS[i % SVC_COLORS.length];
        container.innerHTML += `
            <div class="svc-row">
                <div class="svc-left">
                    <div class="svc-bar" style="background:${color}"></div>
                    <span class="svc-name">${svcNames[name] || name}</span>
                </div>
                <div class="svc-right">
                    <span class="svc-cost">$${Number(monthly).toLocaleString()}</span>
                    <span class="svc-pct">${pct}%</span>
                </div>
            </div>`;
        i++;
    }
}

// ============= FLAGGED BREAKDOWN =============
function populateFlaggedBreakdown(flagged) {
    const el = document.getElementById('flagged-breakdown');
    if (!el) return;
    let idle = 0, unattached = 0, over = 0;
    flagged.forEach(r => {
        if (r.issue.includes('Idle')) idle++;
        else if (r.issue.includes('Unattached')) unattached++;
        else over++;
    });
    el.innerHTML = `<div class="flag-dots">
        <span class="flag-dot"><span class="flag-dot-circle" style="background:#fc8181"></span>${idle} Critical</span>
        <span class="flag-dot"><span class="flag-dot-circle" style="background:#f6ad55"></span>${unattached} Med</span>
        <span class="flag-dot"><span class="flag-dot-circle" style="background:#68d391"></span>${over} Low</span>
    </div>`;
}

// ============= BUDGET CHECKER =============
function checkBudget() {
    const budget = parseFloat(document.getElementById('budget-input').value);
    if (!budget) return;

    const btn = document.getElementById('btn-check-budget');
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Checking…';
    }

    fetch('http://127.0.0.1:5000/api/check-budget', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({budget: budget})
    })
    .then(r => r.json())
    .then(d => {
        const resultEl = document.getElementById('budget-result');
        const iconEl = document.getElementById('budget-result-icon');
        const textEl = document.getElementById('budget-result-text');

        if (resultEl) resultEl.style.display = 'flex';

        if (d.status === 'over') {
            if (iconEl) { iconEl.className = 'budget-result-icon over'; iconEl.textContent = '🚨'; }
            if (textEl) textEl.innerHTML = `<strong>Over Budget!</strong> Monthly cost <strong>$${d.monthly}</strong> exceeds budget by <strong style="color:var(--red)">$${d.over}</strong>. Alert email sent.`;
        } else {
            if (iconEl) { iconEl.className = 'budget-result-icon ok'; iconEl.textContent = '✅'; }
            if (textEl) textEl.innerHTML = `<strong>Within Budget</strong> — Monthly cost <strong>$${d.monthly}</strong> is under your $${budget} limit.`;
        }

        const banner = document.getElementById('alert-banner');
        const msg = document.getElementById('alert-msg');
        if (d.status === 'over') {
            msg.textContent = `Monthly cost $${d.monthly} exceeds budget by $${d.over}. Alert email sent.`;
            banner.style.color = 'var(--red)';
            banner.style.background = 'var(--red-dim)';
            banner.style.border = '1px solid var(--border-light)';
        } else {
            msg.textContent = `Monthly cost $${d.monthly} is within budget.`;
            banner.style.color = 'var(--green)';
            banner.style.background = 'var(--green-dim)';
            banner.style.border = '1px solid var(--border-light)';
        }
        banner.style.display = 'flex';

        resetBudgetBtn(btn);
    })
    .catch(() => resetBudgetBtn(btn));
}

function resetBudgetBtn(btn) {
    if (!btn) return;
    btn.disabled = false;
    btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Check Budget`;
}

// ============= STACKED BAR CHART (AWS Cost Explorer style) =============
function fetchStackedChart() {
    fetch('http://127.0.0.1:5000/api/historical-stacked')
        .then(r => r.json())
        .then(data => {
            if (!data.length) return;

            // Map data for CSV export
            _costData = data.map(day => {
                const total = Object.values(day.services).reduce((a, b) => a + b, 0);
                return { date: day.date, cost: total.toFixed(2) };
            });

            // Collect all unique services
            const allServices = new Set();
            data.forEach(day => {
                Object.keys(day.services).forEach(s => allServices.add(s));
            });
            const serviceList = Array.from(allServices);

            // Build datasets — one per service
            const datasets = serviceList.map((svc, i) => ({
                label: svc,
                data: data.map(day => day.services[svc] || 0),
                backgroundColor: SVC_COLORS_DIM[i % SVC_COLORS_DIM.length],
                borderColor: SVC_COLORS[i % SVC_COLORS.length],
                borderWidth: 1,
                borderRadius: { topLeft: 3, topRight: 3 },
                borderSkipped: false,
                barPercentage: 0.7,
                categoryPercentage: 0.8,
            }));

            const ctx = document.getElementById('historical-chart').getContext('2d');

            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.map(d => {
                        // Format date to shorter label
                        const dt = new Date(d.date);
                        return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                    }),
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            align: 'end',
                            labels: {
                                color: '#5a6a85',
                                font: { size: 11, family: 'Inter' },
                                boxWidth: 12,
                                boxHeight: 12,
                                borderRadius: 3,
                                useBorderRadius: true,
                                padding: 16,
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(14,17,30,0.95)',
                            titleColor: '#edf2f7',
                            bodyColor: '#a0aec0',
                            bodyFont: { family: 'JetBrains Mono', size: 12 },
                            titleFont: { family: 'Inter', size: 13, weight: '600' },
                            borderColor: 'rgba(55,65,100,0.4)',
                            borderWidth: 1,
                            cornerRadius: 10,
                            padding: 14,
                            callbacks: {
                                label: ctx => `  ${ctx.dataset.label}: $${ctx.parsed.y.toFixed(2)}`,
                                footer: items => {
                                    const total = items.reduce((sum, item) => sum + item.parsed.y, 0);
                                    return `\n  Total: $${total.toFixed(2)}`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            stacked: true,
                            ticks: {
                                color: '#5a6a85',
                                font: { size: 10, family: 'Inter' },
                                maxRotation: 45,
                                maxTicksLimit: 10
                            },
                            grid: { display: false },
                            border: { color: 'rgba(55,65,100,0.3)' }
                        },
                        y: {
                            stacked: true,
                            ticks: {
                                color: '#5a6a85',
                                font: { size: 11, family: 'Inter' },
                                callback: v => '$' + v
                            },
                            grid: { color: 'rgba(55,65,100,0.15)', drawBorder: false },
                            border: { display: false }
                        }
                    }
                }
            });
        })
        .catch(() => setStatus('error', 'API connection failed'));
}

// ============= FETCH: ANOMALIES =============
function fetchAnomalies() {
    fetch('http://127.0.0.1:5000/api/anomalies')
        .then(r => r.json())
        .then(data => {
            _anomalyData = data.map(a => ({date: a.date, cost: parseFloat(a.cost), average: parseFloat(a.average), spike: a.spike || '?'}));
            trackFetch();
            if (!data.length) return;

            // Toast notification
            showToast(`⚠️ ${data.length} cost anomal${data.length === 1 ? 'y' : 'ies'} detected!`, 'warning');

            const emptyEl = document.getElementById('anomaly-empty');
            if (emptyEl) emptyEl.style.display = 'none';

            document.getElementById('anomaly-panel').style.display = 'block';

            const anomBadge = document.getElementById('tab-anom-count');
            if (anomBadge) {
                anomBadge.textContent = data.length;
                anomBadge.style.display = 'inline-flex';
            }

            const metaEl = document.getElementById('anomaly-meta');
            if (metaEl) metaEl.textContent = data.length + ' anomal' + (data.length === 1 ? 'y' : 'ies') + ' detected';

            const tbody = document.getElementById('anomaly-table');
            data.forEach(a => {
                tbody.innerHTML += `
                    <tr>
                        <td>${a.date}</td>
                        <td style="color:var(--red);font-weight:600;font-family:var(--mono)">$${a.cost}</td>
                        <td style="color:var(--text-muted)">$${a.average}</td>
                        <td style="color:var(--orange)">${a.message}</td>
                    </tr>`;
            });
        })
        .catch(() => {
            setStatus('error', 'API connection failed');
            trackFetch();
        });
}

// ============= FETCH: EC2 INSTANCES =============
function fetchInstances() {
    fetch('http://127.0.0.1:5000/api/instances')
        .then(r => r.json())
        .then(data => {
            const tbody = document.getElementById('instances-table');
            tbody.innerHTML = '';

            const running = data.filter(i => i.State === 'running').length;
            const stopped = data.filter(i => i.State === 'stopped' || i.State === 'stopping').length;

            const metaEl = document.getElementById('svc-meta');
            if (metaEl) metaEl.textContent = `${running} running · ${stopped} stopped`;

            const totalEl = document.getElementById('svc-total');
            if (totalEl) totalEl.textContent = data.length;

            const svcBadge = document.getElementById('tab-svc-count');
            if (svcBadge) svcBadge.textContent = data.length;

            data.forEach(inst => {
                const stateClass = inst.State === 'running' ? 'state-running' :
                                   inst.State === 'stopped' ? 'state-stopped' : 'state-pending';
                const launched = inst.LaunchTime ? new Date(inst.LaunchTime).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—';

                let actions = '';
                if (inst.State === 'running') {
                    actions = `<div class="action-group">
                        <button class="btn-stop" onclick="stopInstance('${inst.InstanceId}')" id="btn-stop-${inst.InstanceId}">Stop</button>
                        <button class="btn-terminate" onclick="terminateInstance('${inst.InstanceId}')" id="btn-term-${inst.InstanceId}">Terminate</button>
                    </div>`;
                } else if (inst.State === 'stopped') {
                    actions = `<div class="action-group">
                        <button class="btn-start" onclick="startInstance('${inst.InstanceId}')" id="btn-start-${inst.InstanceId}">Start</button>
                        <button class="btn-terminate" onclick="terminateInstance('${inst.InstanceId}')" id="btn-term-${inst.InstanceId}">Terminate</button>
                    </div>`;
                } else {
                    actions = `<span class="state-badge state-pending"><span class="state-dot"></span>${inst.State}</span>`;
                }

                tbody.innerHTML += `
                    <tr id="row-${inst.InstanceId}">
                        <td class="cell-name">${inst.Name || '—'}</td>
                        <td class="cell-id">${inst.InstanceId}</td>
                        <td><span class="type-badge">${inst.InstanceType}</span></td>
                        <td class="cell-region">${inst.Region}</td>
                        <td><span class="state-badge ${stateClass}"><span class="state-dot"></span>${inst.State}</span></td>
                        <td style="color:var(--text-muted);font-size:12px">${launched}</td>
                        <td>${actions}</td>
                    </tr>`;
            });
        })
        .catch(() => {
            const metaEl = document.getElementById('svc-meta');
            if (metaEl) metaEl.textContent = 'Failed to load instances';
        });
}

function stopInstance(instanceId) {
    const btn = document.getElementById('btn-stop-' + instanceId);
    if (btn) { btn.disabled = true; btn.textContent = 'Stopping…'; btn.classList.add('btn-stop--loading'); }

    fetch('http://127.0.0.1:5000/api/instances/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instance_id: instanceId })
    })
    .then(r => r.json())
    .then(d => {
        if (d.success) {
            updateRowState(instanceId, 'stopping');
            if (btn) { btn.textContent = 'Stopped'; btn.classList.remove('btn-stop--loading'); btn.classList.add('btn-stop--done'); }
            setTimeout(fetchInstances, 2000);
        } else {
            if (btn) { btn.disabled = false; btn.textContent = 'Stop'; btn.classList.remove('btn-stop--loading'); }
        }
    })
    .catch(() => { if (btn) { btn.disabled = false; btn.textContent = 'Stop'; btn.classList.remove('btn-stop--loading'); } });
}

function startInstance(instanceId) {
    const btn = document.getElementById('btn-start-' + instanceId);
    if (btn) { btn.disabled = true; btn.textContent = 'Starting…'; btn.classList.add('btn-start--loading'); }

    fetch('http://127.0.0.1:5000/api/instances/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instance_id: instanceId })
    })
    .then(r => r.json())
    .then(d => {
        if (d.success) {
            updateRowState(instanceId, 'pending');
            if (btn) { btn.textContent = 'Started'; btn.classList.remove('btn-start--loading'); btn.classList.add('btn-start--done'); }
            setTimeout(fetchInstances, 2000);
        } else {
            if (btn) { btn.disabled = false; btn.textContent = 'Start'; btn.classList.remove('btn-start--loading'); }
        }
    })
    .catch(() => { if (btn) { btn.disabled = false; btn.textContent = 'Start'; btn.classList.remove('btn-start--loading'); } });
}

function terminateInstance(instanceId) {
    if (!confirm(`⚠ TERMINATE instance ${instanceId}?\n\nThis action is PERMANENT and cannot be undone. All data on the instance will be lost.`)) return;

    const btn = document.getElementById('btn-term-' + instanceId);
    if (btn) { btn.disabled = true; btn.textContent = 'Terminating…'; }

    fetch('http://127.0.0.1:5000/api/instances/terminate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instance_id: instanceId })
    })
    .then(r => r.json())
    .then(d => {
        if (d.success) {
            const row = document.getElementById('row-' + instanceId);
            if (row) {
                row.style.opacity = '0.3';
                row.style.transition = 'opacity 0.5s ease';
            }
            setTimeout(fetchInstances, 1500);
        } else {
            if (btn) { btn.disabled = false; btn.textContent = 'Terminate'; }
        }
    })
    .catch(() => { if (btn) { btn.disabled = false; btn.textContent = 'Terminate'; } });
}

function updateRowState(instanceId, state) {
    const row = document.getElementById('row-' + instanceId);
    if (!row) return;
    const badge = row.querySelector('.state-badge');
    if (badge) {
        badge.className = 'state-badge state-pending';
        badge.innerHTML = `<span class="state-dot"></span>${state}`;
    }
}


// ============= DARK / LIGHT THEME TOGGLE =============
function toggleTheme() {
    const html = document.documentElement;
    const isDark = html.getAttribute('data-theme') !== 'light';
    html.setAttribute('data-theme', isDark ? 'light' : 'dark');

    const darkIcon = document.querySelector('.theme-icon--dark');
    const lightIcon = document.querySelector('.theme-icon--light');
    if (darkIcon) darkIcon.style.display = isDark ? 'none' : 'block';
    if (lightIcon) lightIcon.style.display = isDark ? 'block' : 'none';

    localStorage.setItem('theme', isDark ? 'light' : 'dark');
}

// Restore saved theme
(function restoreTheme() {
    const saved = localStorage.getItem('theme');
    if (saved === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
        const darkIcon = document.querySelector('.theme-icon--dark');
        const lightIcon = document.querySelector('.theme-icon--light');
        if (darkIcon) darkIcon.style.display = 'none';
        if (lightIcon) lightIcon.style.display = 'block';
    }
})();


// ============= EXPORT CSV =============
let _anomalyData = [];
let _costData = [];

function exportCSV(type) {
    let csv = '';
    let filename = '';

    if (type === 'costs') {
        csv = 'Date,Cost\n';
        _costData.forEach(d => { csv += `${d.date},${d.cost}\n`; });
        filename = 'cost_data.csv';
    } else if (type === 'anomalies') {
        csv = 'Date,Cost,Average,Spike\n';
        _anomalyData.forEach(d => {
            csv += `${d.date},$${d.cost.toFixed(2)},$${d.average.toFixed(2)},${d.spike}x\n`;
        });
        filename = 'anomaly_data.csv';
    }

    if (!csv) return;
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast(`${filename} downloaded successfully`, 'success');
}


// ============= COST FORECAST =============
function fetchForecast() {
    fetch('http://127.0.0.1:5000/api/forecast')
        .then(r => r.json())
        .then(data => {
            const el = id => document.getElementById(id);
            el('fc-daily-avg').textContent = `$${data.daily_avg.toFixed(2)}`;
            el('fc-days').textContent = `${data.days_elapsed} / ${data.days_in_month}`;
            el('fc-projected').textContent = `$${data.projected.toFixed(2)}`;

            const changePct = data.change_pct;
            const changeEl = el('fc-change');
            if (changePct > 0) {
                changeEl.innerHTML = `<span class="change-up">▲ +${changePct}%</span>`;
            } else if (changePct < 0) {
                changeEl.innerHTML = `<span class="change-down">▼ ${changePct}%</span>`;
            } else {
                changeEl.textContent = '—';
            }

            // Update comparison badge on monthly card
            const badge = el('month-change');
            if (badge && changePct !== 0) {
                badge.style.display = 'inline-flex';
                badge.className = changePct > 0 ? 'change-badge change-badge--up' : 'change-badge change-badge--down';
                badge.textContent = `${changePct > 0 ? '▲' : '▼'} ${Math.abs(changePct)}%`;
            }
        })
        .catch(() => {});
}


// ============= REGION DONUT CHART =============
let regionChartInstance = null;

function fetchRegionChart() {
    fetch('http://127.0.0.1:5000/api/costs-by-region')
        .then(r => r.json())
        .then(data => {
            const ctx = document.getElementById('region-chart');
            if (!ctx) return;

            if (regionChartInstance) regionChartInstance.destroy();

            regionChartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.map(d => d.region),
                    datasets: [{
                        data: data.map(d => d.cost),
                        backgroundColor: data.map(d => d.color),
                        borderColor: 'rgba(5,7,16,0.8)',
                        borderWidth: 2,
                        hoverBorderColor: '#fff',
                        hoverBorderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '65%',
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(10,12,22,0.95)',
                            titleColor: '#edf2f7',
                            bodyColor: '#a0aec0',
                            borderColor: 'rgba(255,255,255,0.08)',
                            borderWidth: 1,
                            cornerRadius: 10,
                            padding: 12,
                            callbacks: {
                                label: ctx => `$${ctx.parsed.toFixed(2)} (${((ctx.parsed / data.reduce((a,b)=>a+b.cost,0)) * 100).toFixed(1)}%)`
                            }
                        }
                    }
                }
            });

            // Build legend
            const legend = document.getElementById('region-legend');
            if (legend) {
                const total = data.reduce((a, b) => a + b.cost, 0);
                legend.innerHTML = data.map(d => `
                    <div class="region-legend-item">
                        <span class="region-dot" style="background:${d.color}"></span>
                        <span class="region-name">${d.region}</span>
                        <span class="region-cost">$${d.cost.toFixed(0)}</span>
                        <span class="region-pct">${((d.cost/total)*100).toFixed(1)}%</span>
                    </div>
                `).join('');
            }
        })
        .catch(() => {});
}


// ============= FILTER INSTANCES =============
function filterInstances() {
    const search = (document.getElementById('svc-filter')?.value || '').toLowerCase();
    const state = document.getElementById('svc-state-filter')?.value || 'all';
    const rows = document.querySelectorAll('#instances-table tr');
    let visible = 0;

    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const rowState = row.querySelector('.state-badge')?.textContent.trim().toLowerCase() || '';
        const matchSearch = !search || text.includes(search);
        const matchState = state === 'all' || rowState.includes(state);
        const show = matchSearch && matchState;
        row.style.display = show ? '' : 'none';
        if (show) visible++;
    });

    const meta = document.getElementById('svc-meta');
    if (meta) meta.textContent = `${visible} shown`;
}


// ============= TOAST NOTIFICATIONS =============
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const icons = { success: '✅', warning: '⚠️', error: '❌', info: 'ℹ️' };
    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || icons.info}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
    `;
    container.appendChild(toast);

    // Auto-remove after 5s
    setTimeout(() => {
        toast.classList.add('toast--leaving');
        setTimeout(() => toast.remove(), 400);
    }, 5000);
}


// ============= AUTO-REFRESH =============
let autoRefreshInterval = null;
let autoRefreshCountdown = 30;
let autoRefreshTimer = null;

function toggleAutoRefresh() {
    const pill = document.getElementById('auto-refresh-pill');
    const timerEl = document.getElementById('refresh-timer');

    if (autoRefreshInterval) {
        // Turn off
        clearInterval(autoRefreshInterval);
        clearInterval(autoRefreshTimer);
        autoRefreshInterval = null;
        autoRefreshTimer = null;
        timerEl.textContent = 'OFF';
        pill.classList.remove('auto-refresh--active');
        showToast('Auto-refresh disabled', 'info');
    } else {
        // Turn on
        autoRefreshCountdown = 30;
        timerEl.textContent = '30s';
        pill.classList.add('auto-refresh--active');

        autoRefreshTimer = setInterval(() => {
            autoRefreshCountdown--;
            timerEl.textContent = `${autoRefreshCountdown}s`;
            if (autoRefreshCountdown <= 0) autoRefreshCountdown = 30;
        }, 1000);

        autoRefreshInterval = setInterval(() => {
            autoRefreshCountdown = 30;
            initDashboard();
        }, 30000);

        showToast('Auto-refresh enabled (30s)', 'success');
    }
}