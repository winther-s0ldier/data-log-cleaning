const API = '';

/* ─── Auth Gate ─── */
(function checkAuth() {
    if (sessionStorage.getItem('demo_token')) {
        document.getElementById('login-overlay').classList.add('hidden');
    }
})();

document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const user = document.getElementById('login-user').value;
    const pass = document.getElementById('login-pass').value;
    const errEl = document.getElementById('login-error');
    errEl.textContent = '';
    try {
        const res = await fetch(API + '/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, password: pass })
        });
        const data = await res.json();
        if (data.success) {
            sessionStorage.setItem('demo_token', data.token);
            document.getElementById('login-overlay').classList.add('hidden');
        } else {
            errEl.textContent = 'Invalid username or password';
        }
    } catch {
        errEl.textContent = 'Connection error. Is the server running?';
    }
});

/* ─── Navigation ─── */
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.getElementById('section-' + btn.dataset.section).classList.add('active');
        btn.classList.add('active');
    });
});

/* ─── Chart.js Defaults ─── */
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.color = '#71717a';
Chart.defaults.scale.grid.color = '#e4e4e7';

/* ─── Utilities ─── */
function fmt(n) { return typeof n === 'number' ? n.toLocaleString() : (n || '\u2014'); }
function pct(n) { return typeof n === 'number' ? n.toFixed(1) + '%' : '\u2014'; }
async function fetchJSON(url) { const r = await fetch(API + url); if (!r.ok) throw new Error(r.statusText); return r.json(); }

function toggleCard(header) {
    const body = header.nextElementSibling;
    const toggle = header.querySelector('.card-toggle');
    body.classList.toggle('open');
    toggle.textContent = body.classList.contains('open') ? 'collapse' : 'expand';
}

function renderMarkdown(text) {
    if (!text) return '';
    return text
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');
}

function tabGroup(containerId, tabs) {
    let html = '<div class="tab-row">';
    tabs.forEach((t, i) => { html += `<button class="tab-btn${i === 0 ? ' active' : ''}" data-target="${containerId}-tab-${i}" onclick="switchTab(this,'${containerId}')">${t.label}</button>`; });
    html += '</div>';
    tabs.forEach((t, i) => { html += `<div id="${containerId}-tab-${i}" class="tab-panel${i === 0 ? ' active' : ''}">${t.content}</div>`; });
    return html;
}

function switchTab(btn, groupId) {
    const row = btn.parentElement;
    row.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const parent = row.parentElement;
    parent.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.getElementById(btn.dataset.target).classList.add('active');
}

/* ─── OVERVIEW ─── */
async function loadOverview() {
    try {
        const data = await fetchJSON('/api/overview');
        document.getElementById('kpi-users').textContent = fmt(data.total_users);
        document.getElementById('kpi-events').textContent = fmt(data.total_events);
        document.getElementById('kpi-metrics').textContent = data.langgraph_metrics_count || '0';
        document.getElementById('kpi-report').textContent = data.report_available ? 'Available' : 'Not Generated';
    } catch { document.getElementById('kpi-users').textContent = '\u2014'; }
    try {
        const status = await fetchJSON('/api/status');
        const badge = document.getElementById('pipeline-badge');
        const info = document.getElementById('pipeline-info');
        const s = status.status;
        badge.textContent = s.charAt(0).toUpperCase() + s.slice(1);
        badge.className = 'badge ' + (s === 'completed' ? 'badge-green' : s === 'failed' ? 'badge-red' : 'badge-muted');
        let h = '';
        if (status.started_at) h += `<p><strong>Started:</strong> ${status.started_at}</p>`;
        if (status.completed_at) h += `<p><strong>Completed:</strong> ${status.completed_at}</p>`;
        if (status.elapsed_sec) h += `<p><strong>Duration:</strong> ${status.elapsed_sec}s</p>`;
        if (status.metrics_completed?.length) h += `<p><strong>Metrics:</strong> ${status.metrics_completed.join(', ')}</p>`;
        if (status.errors?.length) h += `<p style="color:var(--red)"><strong>Errors:</strong> ${status.errors.join(', ')}</p>`;
        info.innerHTML = h || '<p>No pipeline runs recorded yet.</p>';
    } catch { document.getElementById('pipeline-info').innerHTML = '<p>Could not fetch pipeline status.</p>'; }
}

/* ─── USER EXPLORER ─── */
let allUserEvents = [];
async function loadUsers() {
    try {
        const data = await fetchJSON('/api/users');
        const sel = document.getElementById('user-select');
        sel.innerHTML = '<option value="">\u2014 Select a user \u2014</option>';
        data.users.forEach(uid => { const o = document.createElement('option'); o.value = uid; o.textContent = uid; sel.appendChild(o); });
    } catch { document.getElementById('user-select').innerHTML = '<option value="">Users unavailable</option>'; }
}

async function loadUserData(userId) {
    if (!userId) {
        ['user-kpis', 'user-events-section', 'user-reps-section', 'user-journey-section', 'user-ai-section'].forEach(id => document.getElementById(id).style.display = 'none');
        document.getElementById('user-empty').style.display = 'block';
        return;
    }
    document.getElementById('user-empty').style.display = 'none';
    document.getElementById('user-empty').style.display = 'none';
    document.getElementById('ai-interpret-result').innerHTML = '';

    // 1. Events
    try {
        const data = await fetchJSON(`/api/users/${userId}/events`);
        allUserEvents = data.events || [];
        document.getElementById('user-event-count').textContent = fmt(data.total_events);
        document.getElementById('user-unique-events').textContent = fmt(data.unique_event_types);
        document.getElementById('user-kpis').style.display = '';
        const names = [...new Set(allUserEvents.map(e => e.event_name))].sort();
        const fSel = document.getElementById('event-filter');
        fSel.innerHTML = '<option value="">All Events</option>';
        names.forEach(n => { const o = document.createElement('option'); o.value = n; o.textContent = n; fSel.appendChild(o); });
        renderEvents('');
        document.getElementById('user-events-section').style.display = '';
    } catch { document.getElementById('user-events-section').style.display = 'none'; }

    // 2. Repetitions
    try {
        const data = await fetchJSON(`/api/users/${userId}/repetitions`);
        const reps = data.repetitions || [];
        if (!reps.length) { document.getElementById('user-reps-section').style.display = 'none'; }
        else {
            const keys = Object.keys(reps[0]).filter(k => k !== 'user_uuid');
            document.getElementById('reps-thead').innerHTML = '<tr>' + keys.map(k => `<th>${k.replace(/_/g, ' ')}</th>`).join('') + '</tr>';
            document.getElementById('reps-tbody').innerHTML = reps.map(r => '<tr>' + keys.map(k => `<td>${r[k] != null ? r[k] : ''}</td>`).join('') + '</tr>').join('');
            document.getElementById('user-reps-section').style.display = '';
        }
    } catch { document.getElementById('user-reps-section').style.display = 'none'; }

    // 3. User Journey (Flow Cards)
    try {
        const journey = await fetchJSON(`/api/users/${userId}/journey`);
        const meta = journey.metadata || {};
        const dr = meta.date_range || {};
        document.getElementById('user-span-days').textContent = dr.span_days || '—';

        let metaHtml = `<p><strong>Events:</strong> ${journey.total_events} &middot; <strong>Time Range:</strong> ${dr.first_event || '—'} to ${dr.last_event || '—'} &middot; <strong>Sessions Detected:</strong> ${journey.sessions_detected} (30-min gap)</p>`;
        document.getElementById('journey-meta').innerHTML = metaHtml;

        // Render Flow Cards
        const sessions = journey.sessions || [];
        let sessHtml = '<div class="flow-row">';
        sessions.forEach((s, idx) => {
            const eventsJson = encodeURIComponent(JSON.stringify(s.events));
            let eventsHtml = '';
            s.events.slice(0, 6).forEach(e => {
                eventsHtml += `<div class="flow-card-ev"><span class="ev-time">${e.time || ''}</span>${e.event_name}</div>`;
            });
            if (s.events.length > 6) eventsHtml += `<div class="flow-card-ev" style="font-style:italic">... +${s.events.length - 6} more</div>`;

            sessHtml += `<div class="flow-card" onclick="expandJourneySession(${idx}, '${eventsJson}')">
                <div class="flow-card-hd">Session ${s.session_number}</div>
                <div class="flow-card-meta">${s.first_time || ''}<br>${s.event_count} events</div>
                <div style="flex:1;overflow:hidden">${eventsHtml}</div>
            </div>`;
        });
        sessHtml += '</div>';
        document.getElementById('journey-sessions').innerHTML = sessHtml;

        // Event breakdown
        const breakdown = meta.event_breakdown || {};
        const breakdownEntries = Object.entries(breakdown).sort((a, b) => b[1] - a[1]);
        if (breakdownEntries.length) {
            let bdHtml = '<div class="card" style="margin-top:16px"><div class="card-header" onclick="toggleCard(this)"><div class="card-title">Event Breakdown</div><span class="card-toggle">expand</span></div>';
            bdHtml += '<div class="card-body"><div class="table-wrap"><table><thead><tr><th>Event Name</th><th>Count</th></tr></thead><tbody>';
            breakdownEntries.forEach(([name, count]) => {
                bdHtml += `<tr><td>${name}</td><td>${count}</td></tr>`;
            });
            bdHtml += '</tbody></table></div></div></div>';
            document.getElementById('journey-breakdown').innerHTML = bdHtml;
        }
        document.getElementById('user-journey-section').style.display = '';
    } catch { document.getElementById('user-journey-section').style.display = 'none'; }

    document.getElementById('user-ai-section').style.display = '';
}

function renderEvents(filter) {
    let ev = filter ? allUserEvents.filter(e => e.event_name === filter) : allUserEvents;
    const tb = document.getElementById('events-tbody');
    if (!ev.length) { tb.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">No events</td></tr>'; return; }
    tb.innerHTML = ev.map(e => `<tr><td>${e.event_date || ''}</td><td>${e.event_day || ''}</td><td>${e.event_time_only || ''}</td><td>${e.event_name || ''}</td><td>${e.category || ''}</td></tr>`).join('');
}

function expandJourneySession(idx, eventsJson) {
    const events = JSON.parse(decodeURIComponent(eventsJson));
    const overlay = document.getElementById('flow-overlay');
    document.getElementById('flow-expanded-header').textContent = `Session ${idx + 1}: ${events[0].date} (${events[0].time} - ${events[events.length - 1].time})`;
    let html = '';
    events.forEach((e, i) => {
        html += `<div class="flow-expanded-ev"><strong>${e.time}</strong><br>${e.event_name}</div>`;
        if (i < events.length - 1) html += '<div class="flow-arrow">→</div>';
    });
    document.getElementById('flow-expanded-events').innerHTML = html;
    overlay.classList.add('active');
}

function closeFlowOverlay(e) {
    if (e.target.id === 'flow-overlay' || e.target.closest('.flow-close')) {
        document.getElementById('flow-overlay').classList.remove('active');
    }
}

/* ─── AI Functions ─── */
async function runInterpretation() {
    const uid = document.getElementById('user-select').value;
    if (!uid) return;
    const btn = document.getElementById('btn-interpret');
    const container = document.getElementById('ai-interpret-result');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>Analyzing...';
    container.innerHTML = '<p class="loading">Calling LLM for journey interpretation...</p>';

    try {
        const res = await fetch(API + `/api/users/${uid}/interpret`, { method: 'POST' });
        const data = await res.json();

        if (data.success && data.is_structured && data.parsed) {
            const p = data.parsed;
            let html = `
            <div class="llm-insight-box">
                <h3>Journey Narrative</h3>
                <p>${p.overall_narrative || 'No narrative provided.'}</p>
            </div>`;

            if (p.key_observations && p.key_observations.length) {
                html += '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:24px">';
                p.key_observations.forEach(obs => {
                    html += `<div style="background:var(--bg-secondary);padding:8px 14px;border-radius:20px;font-size:13px">💡 ${obs}</div>`;
                });
                html += '</div>';
            }

            if (p.interpreted_sessions && p.interpreted_sessions.length) {
                html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px">';
                p.interpreted_sessions.forEach(s => {
                    const eventsStr = (s.events || []).slice(0, 3).join(' → ') + ((s.events?.length > 3) ? '...' : '');
                    html += `
                    <div class="session-card">
                        <div style="font-weight:600;margin-bottom:4px">${s.session_name || 'Session'}</div>
                        <div style="font-size:12px;color:var(--text-muted);margin-bottom:8px">${s.date || ''} • ${s.start_time || ''} - ${s.end_time || ''}</div>
                        <div style="font-style:italic;background:var(--bg-secondary);padding:10px;border-radius:6px;font-size:13px;margin-bottom:8px">
                            ${s.interpretation || 'No interpretation'}
                        </div>
                        <div style="font-size:12px;color:var(--text-secondary)">${s.events?.length || 0} events: ${eventsStr}</div>
                    </div>`;
                });
                html += '</div>';
            }
            container.innerHTML = html;
        } else if (data.success) {
            container.innerHTML = `<div class="ai-result">${renderMarkdown(data.content)}</div>`;
        } else {
            container.innerHTML = `<div class="ai-result" style="color:var(--red)">Error: ${data.error || 'Unknown error'}</div>`;
        }
    } catch (e) {
        container.innerHTML = `<div class="ai-result" style="color:var(--red)">Error: ${e.message}</div>`;
    }

    btn.disabled = false;
    btn.textContent = 'Generate AI Interpretation';
}



/* ─── SESSION ANALYSIS ─── */
async function loadSessions() {
    const content = document.getElementById('session-content');
    try {
        const profile = await fetchJSON('/api/session-profile');
        const s = profile.sessions || {};
        const stats = profile.basic_stats || {};

        // 1. Overview KPIs
        let html = '<div class="kpi-row">';
        html += `<div class="kpi"><div class="kpi-value">${fmt(s.total_sessions)}</div><div class="kpi-label">Total Sessions</div></div>`;
        html += `<div class="kpi"><div class="kpi-value">${(s.avg_session_length || 0).toFixed(1)}</div><div class="kpi-label">Avg Events/Session</div></div>`;
        html += `<div class="kpi"><div class="kpi-value">${(s.avg_session_duration_minutes || 0).toFixed(1)} min</div><div class="kpi-label">Avg Duration</div></div>`;
        html += `<div class="kpi"><div class="kpi-value">${((s.bounce_rate || 0) * 100).toFixed(1)}%</div><div class="kpi-label">Bounce Rate</div></div>`;
        html += `<div class="kpi"><div class="kpi-value">${fmt(s.session_markers_used)}</div><div class="kpi-label">System Markers</div></div>`;
        html += '</div>';

        // 2. Drop-off Analysis (2-col)
        html += '<div style="display:grid;grid-template-columns:2fr 1fr;gap:24px;margin-bottom:32px">';
        html += '<div class="chart-box"><h3>Drop-off Analysis (Top Exit Events)</h3><canvas id="chart-dropoff"></canvas></div>';

        let dropHtml = '<div class="insight-panel"><h3>🎯 Critical Drop-offs</h3><div style="display:flex;flex-direction:column;gap:12px">';
        const exit = Object.entries(s.common_end_events || {}).sort((a, b) => b[1] - a[1]).slice(0, 5);
        exit.forEach(([name, count]) => {
            const pct = (count / (s.total_sessions || 1)) * 100;
            const priority = pct > 8 ? '🔴 HIGH' : '🟡 MEDIUM';
            dropHtml += `<div class="stat-item">
                <div style="font-weight:600;font-size:13px;margin-bottom:2px">${priority}: ${name}</div>
                <div style="font-size:12px;color:var(--text-secondary)">└─ ${fmt(count)} sessions (${pct.toFixed(1)}%)</div>
             </div>`;
        });
        dropHtml += '</div></div></div>';
        html += dropHtml;

        // 3. Session Start (Full width)
        html += '<div class="chart-box" style="margin-bottom:32px"><h3>🔍 Session Start Patterns</h3><canvas id="chart-start" style="max-height:300px"></canvas></div>';

        // 4. Session Length (2-col)
        const dist = s.session_length_distribution || {};
        html += '<div style="display:grid;grid-template-columns:2fr 1fr;gap:24px;margin-bottom:32px">';
        html += '<div class="chart-box"><h3>📏 Session Length Distribution</h3><canvas id="chart-length"></canvas></div>';

        html += `<div class="insight-panel">
            <h3>💡 Session Length Insights</h3>
            <ul style="font-size:13px;color:var(--text-secondary);line-height:1.8;padding-left:18px">
                <li><strong>25% of sessions</strong> have ≤ ${dist.p25 || 0} events (Quick interactions)</li>
                <li><strong>50% of sessions</strong> have ≤ ${dist.p50 || 0} events (Typical session)</li>
                <li><strong>75% of sessions</strong> have ≤ ${dist.p75 || 0} events (Engaged users)</li>
                <li>Top 10% have > ${dist.p90 || 0} events (Power users)</li>
                <li>Top 5% have > ${dist.p95 || 0} events (Deep exploration)</li>
            </ul>
            <div style="margin-top:16px;font-size:12px;color:var(--text-muted)">
                <strong>Categories:</strong><br>
                • Short (<10 events): Quick search<br>
                • Medium (10-30): Active exploration<br>
                • Long (>30): Complete booking flow
            </div>
        </div>`;
        html += '</div>';

        // 5. Event Classification (2-col)
        html += '<div style="display:grid;grid-template-columns:2fr 1fr;gap:24px;margin-bottom:32px">';
        html += '<div class="chart-box"><h3>🏷️ Event Classification by Category</h3><canvas id="chart-class"></canvas></div>';

        const cls = Object.entries(profile.event_classification || {}).sort((a, b) => b[1].event_count - a[1].event_count);
        let clsHtml = '<div class="insight-panel"><h3>Category Breakdown</h3><div style="display:flex;flex-direction:column;gap:12px">';
        cls.forEach(([name, data]) => {
            clsHtml += `<div class="stat-item">
                <div style="font-weight:600;font-size:13px">${name.replace(/_/g, ' ')}</div>
                <div style="font-size:12px;color:var(--text-secondary)">└─ ${fmt(data.event_count)} events • ${data.unique_event_types} types</div>
            </div>`;
        });
        clsHtml += '</div></div></div>';
        html += clsHtml;

        // 6. Actionable Recommendations (Accordions)
        html += '<h2 class="section-header">💡 Actionable Recommendations</h2>';
        const recs = [
            { p: 'HIGH', t: 'Seat Selection Drop-off', d: 'Simplify seat selection UI. Show real-time availability. Add "Best seats" recommendation.', i: '⬆️ +12-15% conversion', prob: '3,360 users (9.1%) drop off', time: '3-4 weeks', slug: 'seat' },
            { p: 'HIGH', t: 'Login/Auth Friction', d: 'Add social login. Implement guest checkout. Reduce OTP timeout.', i: '⬆️ +8-10% completion', prob: '3,997 users (10.8%) drop off', time: '3-4 weeks', slug: 'login' },
            { p: 'MEDIUM', t: 'User Profile Abandonment', d: 'Make profile setup optional. Show value prop. Allow skip.', i: '⬆️ +5-7% retention', prob: '1,921 users (5.2%) drop off', time: '2-3 weeks', slug: 'profile' },
            { p: 'LOW', t: 'Language Selection', d: 'Auto-detect language. Remember preference.', i: '⬆️ +3-5% onboarding', prob: '1,929 users (5.2%) drop off', time: '1-2 weeks', slug: 'lang' }
        ];

        recs.forEach(r => {
            const color = r.p === 'HIGH' ? 'red' : r.p === 'MEDIUM' ? 'yellow' : 'green';
            const icon = r.p === 'HIGH' ? '🔴' : r.p === 'MEDIUM' ? '🟡' : '🟢';
            html += `<details class="rec-accordion" style="background:var(--bg-card);border:1px solid var(--border);border-radius:8px;margin-bottom:12px;overflow:hidden">
                <summary style="padding:16px;cursor:pointer;font-weight:600;display:flex;align-items:center;gap:12px;list-style:none">
                    <span style="font-size:16px">${icon}</span>
                    <span>${r.p} PRIORITY: ${r.t}</span>
                    <span style="margin-left:auto;font-size:12px;color:var(--text-muted)">${r.prob}</span>
                </summary>
                <div style="padding:0 24px 24px;display:grid;grid-template-columns:1fr 1fr;gap:24px;border-top:1px solid var(--bg-secondary);margin-top:0;padding-top:16px">
                    <div>
                        <div style="font-size:12px;font-weight:600;color:var(--text-secondary);margin-bottom:4px">📊 Problem</div>
                        <div style="font-size:13px;margin-bottom:16px">${r.prob}</div>
                        <div style="font-size:12px;font-weight:600;color:var(--text-secondary);margin-bottom:4px">🎯 Recommended Actions</div>
                        <div style="font-size:13px">${r.d}</div>
                    </div>
                    <div>
                        <div style="font-size:12px;font-weight:600;color:var(--text-secondary);margin-bottom:4px">📈 Expected Impact</div>
                        <div style="font-size:13px;margin-bottom:16px">${r.i}</div>
                        <div style="font-size:12px;font-weight:600;color:var(--text-secondary);margin-bottom:4px">⏱️ Implementation</div>
                        <div style="font-size:13px">Estimated time: ${r.time}</div>
                    </div>
                </div>
            </details>`;
        });

        content.innerHTML = html;

        // Render Charts
        new Chart(document.getElementById('chart-dropoff'), {
            type: 'bar',
            data: { labels: exit.map(e => e[0]), datasets: [{ label: 'Sessions', data: exit.map(e => e[1]), backgroundColor: '#ef4444' }] },
            options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false }
        });

        const start = Object.entries(s.common_start_events || {}).slice(0, 10);
        new Chart(document.getElementById('chart-start'), {
            type: 'bar',
            data: { labels: start.map(e => e[0]), datasets: [{ label: 'Sessions', data: start.map(e => e[1]), backgroundColor: '#6366f1' }] },
            options: { responsive: true, maintainAspectRatio: false }
        });

        new Chart(document.getElementById('chart-length'), {
            type: 'bar',
            data: { labels: ['P25', 'P50', 'P75', 'P90', 'P95'], datasets: [{ label: 'Events', data: [dist.p25, dist.p50, dist.p75, dist.p90, dist.p95], backgroundColor: ['#10b981', '#10b981', '#10b981', '#065f46', '#064e3b'] }] },
            options: { responsive: true, maintainAspectRatio: false }
        });

        new Chart(document.getElementById('chart-class'), {
            type: 'bar',
            data: { labels: cls.map(e => e[0].replace(/_/g, ' ')), datasets: [{ label: 'Events', data: cls.map(e => e[1].event_count), backgroundColor: '#f59e0b' }] },
            options: { responsive: true, maintainAspectRatio: false }
        });

    } catch (e) { console.error(e); content.innerHTML = '<p class="empty">Failed to load session profile.</p>'; }
}

/* ─── PATTERN DISCOVERY ─── */

// Helper to render AI insights as visual blocks
function renderStructuredInsights(text) {
    if (!text) return '';

    // 1. Clean conversational preamble
    text = text.replace(/^(Certainly|Here|Below|Sure|I have analyzed|Based on).+?(:|\.)\s*/si, '');

    // 2. Split by ### Headers (Level 1 Cards)
    // We split by newline+### to handle multiple top-level sections
    // If text starts with ###, we fix it by prepending \n if needed, or just standardizing
    if (text.startsWith('###')) text = '\n' + text;

    const sections = text.split(/\n###\s+/).filter(s => s.trim());

    // 3. Fallback: If no ### headers found, check for Numbered Sections (e.g. "1. **Overall Health**:")
    // This handles Executive Summary format where likely no ### exists or it's just one block
    if (sections.length === 0 || (sections.length === 1 && !text.includes('###'))) {
        // Try splitting by Numbered Bold Headers
        // Regex: (Start or Newline) + Number + . + Space + **Match**
        const numSections = text.split(/(?:^|\n)\d+\.\s+\*\*(.+?)\*\*[:]?/);

        if (numSections.length > 2) {
            // Found numbered sections!
            // split result: [Intro, Title1, Body1, Title2, Body2...]
            let html = '<div class="insight-grid" style="display:flex;flex-direction:column;gap:16px">';

            // Intro
            if (numSections[0].trim()) {
                html += `<div style="font-size:14px;color:var(--text-secondary);margin-bottom:8px">${renderMarkdown(numSections[0])}</div>`;
            }

            for (let i = 1; i < numSections.length; i += 2) {
                const subTitle = numSections[i].trim();
                const subBody = numSections[i + 1];
                html += `<div class="insight-card" style="background:#fff;border:1px solid var(--border);border-radius:8px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.05)">
                     <h4 style="margin:0 0 12px 0;color:var(--text);font-size:16px;font-weight:700;display:flex;align-items:center;gap:8px">
                        <span style="color:var(--primary);background:var(--bg-secondary);width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px">${Math.ceil(i / 2)}</span>
                        ${subTitle}
                    </h4>
                    <div style="font-size:13px;line-height:1.6;color:var(--text-secondary)">${renderMarkdown(subBody)}</div>
                </div>`;
            }
            html += '</div>';
            return html;
        }

        return renderMarkdown(text);
    }

    let html = '<div class="insight-grid" style="display:flex;flex-direction:column;gap:16px">';

    sections.forEach(section => {
        const lines = section.split('\n');
        // First line is title (stripped of ### by split)
        let title = lines[0].trim().replace(/\*+/g, ''); // Remove bold stars
        let body = lines.slice(1).join('\n').trim();

        if (!title && !body) return;

        html += `<div class="insight-card" style="background:#fff;border:1px solid var(--border);border-radius:8px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.05)">`;

        if (title) {
            html += `<h4 style="margin:0 0 16px 0;color:var(--text);font-size:16px;font-weight:700;border-bottom:1px solid var(--border-light);padding-bottom:12px;display:flex;align-items:center;gap:8px">
                <span style="color:var(--primary)">❖</span> ${title}
            </h4>`;
        }

        // 3. Level 2 Split (Numbered Sub-sections e.g. "**1. Persona Profile:**")
        // Regex to capture: Newline + ** + Number + . + Space + Title + : + **
        const subSections = body.split(/(?:^|\n)\*\*\d+\.\s+([^*]+):\*\*/g);

        // Also try logic for Executive Summary style inside a section (1. **Title**)
        const altSubSections = body.split(/(?:^|\n)\d+\.\s+\*\*(.+?)\*\*[:]?/);

        if (subSections.length > 1) {
            // Found sub-sections (Standard Pattern Discovery)
            html += `<div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(280px, 1fr));gap:16px">`;

            // Intro text
            if (subSections[0].trim()) {
                html += `<div style="grid-column:1/-1;font-size:14px;color:var(--text-secondary);margin-bottom:8px">${renderMarkdown(subSections[0])}</div>`;
            }

            for (let i = 1; i < subSections.length; i += 2) {
                const subTitle = subSections[i].trim();
                const subBody = subSections[i + 1];

                html += `<div class="sub-card" style="background:var(--bg-secondary);padding:16px;border-radius:8px;">
                    <div style="font-weight:600;color:var(--text);margin-bottom:8px;font-size:14px">${subTitle}</div>
                    <div style="font-size:13px;line-height:1.6;color:var(--text-secondary)">${renderMarkdown(subBody)}</div>
                </div>`;
            }
            html += `</div>`;
        } else if (altSubSections.length > 2) {
            // Found numbered list with bold title style (Executive Summary Style inside a section?)
            html += `<div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(280px, 1fr));gap:16px">`;
            if (altSubSections[0].trim()) {
                html += `<div style="grid-column:1/-1;font-size:14px;color:var(--text-secondary);margin-bottom:8px">${renderMarkdown(altSubSections[0])}</div>`;
            }
            for (let i = 1; i < altSubSections.length; i += 2) {
                const subTitle = altSubSections[i].trim();
                const subBody = altSubSections[i + 1];
                html += `<div class="sub-card" style="background:var(--bg-secondary);padding:16px;border-radius:8px;">
                    <div style="font-weight:600;color:var(--text);margin-bottom:8px;font-size:14px">${subTitle}</div>
                    <div style="font-size:13px;line-height:1.6;color:var(--text-secondary)">${renderMarkdown(subBody)}</div>
                </div>`;
            }
            html += `</div>`;

        } else {
            // No sub-sections
            if (body.match(/-\s+\*\*.+?:\*\*/)) {
                html += `<div style="font-size:14px;line-height:1.7;color:var(--text-secondary)">${renderMarkdown(body)}</div>`;
            } else {
                html += `<div style="font-size:14px;color:var(--text-secondary)">${renderMarkdown(body)}</div>`;
            }
        }

        html += `</div>`;
    });

    html += '</div>';
    return html;
}

// Reuse this function in loadPatterns
async function loadPatterns() {
    const content = document.getElementById('pattern-content');
    if (!content) return;
    content.innerHTML = '<p class="loading">Loading patterns...</p>';
    try {
        const data = await fetchJSON('/api/pattern-discovery');
        const seq = data.sequential_patterns || {};
        const seg = data.user_segments || {};
        const fric = data.friction_points || {};
        const surv = data.survival_analysis || {};
        const rules = data.intervention_rules || {};

        // Top Metrics
        const metricCounts = {
            patterns: Object.keys(seq.frequent_patterns || {}).length,
            segments: Object.keys(seg.segments || {}).length,
            friction: Object.keys(fric.high_friction_events || {}).length,
            rules: (rules.intervention_triggers || []).length
        };

        let html = '';

        // Executive Summary
        if (data.llm_executive_summary) {
            // Remove redundant title if present so it parses cleanly
            let sumText = data.llm_executive_summary.replace(/^###\s*Executive Summary[:]?\s*/i, '');
            html += `<div class="exec-summary">
                <h2>🎯 Executive Summary</h2>
                <div>${renderStructuredInsights(sumText)}</div>
            </div>`;
        }

        // Top Metrics Bar
        html += `<div class="kpi-row" style="margin-bottom:24px;justify-content:space-around;background:var(--bg-card);padding:16px;border-radius:12px;border:1px solid var(--border)">
            <div style="text-align:center"><div style="font-size:24px;font-weight:700;color:var(--text)">${metricCounts.patterns}</div><div style="font-size:12px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px">Patterns Analyzed</div></div>
            <div style="text-align:center"><div style="font-size:24px;font-weight:700;color:var(--text)">${metricCounts.segments}</div><div style="font-size:12px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px">User Segments</div></div>
            <div style="text-align:center"><div style="font-size:24px;font-weight:700;color:var(--text)">${metricCounts.friction}</div><div style="font-size:12px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px">Friction Points</div></div>
            <div style="text-align:center"><div style="font-size:24px;font-weight:700;color:var(--text)">${metricCounts.rules}</div><div style="font-size:12px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px">Intervention Rules</div></div>
        </div>`;

        // Tabs HTML
        html += '<div class="tab-row" style="margin-bottom:20px">';
        ['Sequences', 'Segments', 'Friction', 'Survival', 'Interventions'].forEach((t, i) => {
            html += `<button class="tab-btn${i === 0 ? ' active' : ''}" onclick="showPatTab(${i})">${t}</button>`;
        });
        html += '</div>';

        // 1. Sequences
        html += `<div id="pat-tab-0" class="pat-tab active">
            <div style="display:grid;grid-template-columns:2fr 1fr;gap:24px">
                <div class="chart-box chart-full" style="height:400px"><canvas id="chart-seq"></canvas></div>
                <div>`;

        // Frequent Patterns List
        html += `<h3>Top Sequences</h3><div class="seq-list" style="margin-top:12px">`;
        const freq = Object.entries(seq.frequent_patterns || {}).slice(0, 10);
        freq.forEach(([p, c]) => {
            html += `<div class="seq-item"><div class="seq-pattern">${p}</div><div class="seq-badge">${c.toLocaleString()}</div></div>`;
        });
        html += `</div></div></div>`;

        // Structured Interpretation (Data-driven)
        if (seq.pattern_insights && Object.keys(seq.pattern_insights).length > 0) {
            html += `<div class="llm-insight-box" style="margin-top:20px;border-left-color:var(--blue)">
                <h3>📊 Quantitative Interpretation</h3>
                <div style="font-size:13px;line-height:1.6">`;
            Object.entries(seq.pattern_insights).slice(0, 5).forEach(([p, i]) => {
                html += `<div style="margin-bottom:8px"><strong>${p}</strong>: ${i}</div>`;
            });
            html += `</div></div>`;
        }

        // AI Strategic Insights (LLM)
        if (seq.llm_insights) {
            html += `<div style="margin-top:20px"><h3>🤖 AI Strategic Insights</h3>${renderStructuredInsights(seq.llm_insights)}</div>`;
        }
        html += `</div>`;

        // 2. Segments
        html += `<div id="pat-tab-1" class="pat-tab" style="display:none">
            <div class="seg-grid">`;
        Object.entries(seg.segments || {}).forEach(([k, v]) => {
            html += `<div class="seg-card"><h4>${k.replace(/_/g, ' ').toUpperCase()}</h4><div class="seg-count">${v.count}</div><div class="seg-pct">${v.percentage}%</div><p style="font-size:12px;margin-top:8px">${v.description}</p></div>`;
        });
        html += `</div>
            <div class="chart-box chart-full" style="margin-top:20px;height:300px"><canvas id="chart-seg"></canvas></div>`;
        if (seg.llm_insights) {
            html += `<div style="margin-top:32px"><h3>🤖 AI Segment Analysis</h3>${renderStructuredInsights(seg.llm_insights)}</div>`;
        }
        html += `</div>`;

        // 3. Friction
        const fricSum = fric.friction_summary || fric.llm_insights;
        html += `<div id="pat-tab-2" class="pat-tab" style="display:none">
            <div class="chart-box chart-full" style="height:400px;margin-bottom:24px"><canvas id="chart-fric"></canvas></div>
            
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
                <div>
                   <h3>Recent Friction Points</h3>
                   <div style="margin-top:12px">`;
        const highFric = Object.entries(fric.high_friction_events || {}).slice(0, 5);
        highFric.forEach(([k, v]) => {
            html += `<div class="friction-item">
                <div class="friction-label">${k}</div>
                <div class="friction-bar-bg"><div class="friction-bar-fill" style="width:${Math.min(v.repetition_rate * 100, 100)}%"></div></div>
                <div class="friction-val">${(v.repetition_rate * 100).toFixed(1)}%</div>
            </div>`;
        });
        html += `   </div>
                </div>
                <div>
                    ${fricSum ? `<h3>📑 Friction Summary</h3><div style="margin-top:12px">${renderStructuredInsights(fricSum)}</div>` : ''}
                </div>
            </div>`;
        html += `</div>`;

        // 4. Survival
        const medianLen = surv.median_session_length || 0;
        const reach10 = surv.sessions_reaching_step_10 || 0;
        const reach20 = surv.sessions_reaching_step_20 || 0;
        const drops = surv.critical_dropoffs || [];

        html += `<div id="pat-tab-3" class="pat-tab" style="display:none">
            <div class="kpi-row" style="margin-bottom:24px;justify-content:flex-start;gap:40px">
                <div><div style="font-size:12px;color:var(--text-secondary)">Median Session Length</div><div style="font-size:24px;font-weight:600">${medianLen} events</div></div>
                <div><div style="font-size:12px;color:var(--text-secondary)">Reach Step 10</div><div style="font-size:24px;font-weight:600">${fmt(reach10)}</div></div>
                <div><div style="font-size:12px;color:var(--text-secondary)">Reach Step 20</div><div style="font-size:24px;font-weight:600">${fmt(reach20)}</div></div>
            </div>

            <div style="display:grid;grid-template-columns:2fr 1fr;gap:24px">
                <div class="chart-box"><canvas id="chart-surv"></canvas></div>
                <div>
                    <h3>⚠️ Critical Drop-offs</h3>
                    <div style="margin-top:16px;display:flex;flex-direction:column;gap:16px">`;
        drops.slice(0, 5).forEach(d => {
            html += `<div>
                <div style="font-weight:600;margin-bottom:4px">Step ${d.step}</div>
                <div style="font-size:20px;font-weight:600;margin-bottom:4px">Drop Rate: ${d.drop_percentage.toFixed(1)}%</div>
                <div style="font-size:12px;color:var(--text-secondary);margin-bottom:4px">${(d.survival_after * 100).toFixed(1)}% surviving after this step</div>
                <div class="progress-bar"><div class="progress-fill" style="width:${(d.survival_after * 100)}%;background:#3b82f6"></div></div>
            </div>`;
        });
        html += `   </div>
                </div>
            </div>
            ${surv.llm_insights ? `<div style="margin-top:32px"><h3>🤖 AI Survival Analysis</h3>${renderStructuredInsights(surv.llm_insights)}</div>` : ''}
        </div>`;

        // 5. Interventions
        const triggers = rules.intervention_triggers || [];
        const highRisk = triggers.filter(r => r.confidence > 0.9);
        const medRisk = triggers.filter(r => r.confidence > 0.7 && r.confidence <= 0.9);
        const lowRisk = triggers.filter(r => r.confidence <= 0.7);

        html += `<div id="pat-tab-4" class="pat-tab" style="display:none">
            <h2 style="font-size:20px;margin-bottom:8px">Discovered ${triggers.length} High-Confidence Rules</h2>
            <p style="color:var(--text-secondary);margin-bottom:24px">Automated rules - conditions that predict user drop-off</p>
            
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;margin-bottom:32px">
                <div><div style="margin-bottom:4px">🔴 High Risk Rules</div><div style="font-size:24px;font-weight:600">${highRisk.length}</div><div style="font-size:12px;color:var(--green)">↑ 90% dropout</div></div>
                <div><div style="margin-bottom:4px">🟡 Medium Risk Rules</div><div style="font-size:24px;font-weight:600">${medRisk.length}</div><div style="font-size:12px;color:var(--green)">↑ 70-90% dropout</div></div>
                <div><div style="margin-bottom:4px">🟢 Low Risk Rules</div><div style="font-size:24px;font-weight:600">${lowRisk.length}</div><div style="font-size:12px;color:var(--green)">↓ <70% dropout</div></div>
            </div>

            <div style="display:flex;flex-direction:column;gap:12px">`;

        triggers.slice(0, 10).forEach(r => {
            const level = r.confidence > 0.9 ? 'High' : r.confidence > 0.7 ? 'Medium' : 'Low';
            const color = r.confidence > 0.9 ? 'red' : r.confidence > 0.7 ? 'yellow' : 'green';
            const icon = r.confidence > 0.9 ? '🔴' : r.confidence > 0.7 ? '🟡' : '🟢';

            html += `<details class="rec-accordion" style="background:#fff;border:1px solid var(--border);border-radius:6px;overflow:hidden">
                <summary style="padding:16px;cursor:pointer;display:flex;align-items:center;gap:12px;list-style:none">
                    <span style="font-size:12px;transform:rotate(0deg)">➤</span>
                    <span style="font-size:16px">${icon}</span>
                    <span style="font-weight:500;font-family:monospace">${r.condition}</span>
                    <span style="margin-left:auto;color:var(--text-secondary);font-size:13px">(${(r.confidence * 100).toFixed(0)}% dropout risk)</span>
                </summary>
                <div style="padding:16px 40px;background:var(--bg-secondary);border-top:1px solid var(--border)">
                    <div><strong>Recommend:</strong> ${r.recommendation}</div>
                    <div style="font-size:12px;color:var(--text-muted);margin-top:8px">Support: ${r.support} sessions</div>
                </div>
            </details>`;
        });
        html += `</div>`;

        if (rules.llm_insights) {
            html += `<div style="margin-top:32px"><h3>🤖 AI Strategy Recommendations</h3>${renderStructuredInsights(rules.llm_insights)}</div>`;
        }
        html += `</div>`;

        content.innerHTML = html;

        // Render Charts
        // Seq
        new Chart(document.getElementById('chart-seq'), {
            type: 'bar',
            data: { labels: freq.map(f => f[0].substring(0, 30) + '...'), datasets: [{ label: 'Frequency', data: freq.map(f => f[1]), backgroundColor: '#3b82f6' }] },
            options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false }
        });

        // Seg
        const segNames = Object.keys(seg.segments || {});
        new Chart(document.getElementById('chart-seg'), {
            type: 'doughnut',
            data: { labels: segNames, datasets: [{ data: segNames.map(k => seg.segments[k].count), backgroundColor: ['#ef4444', '#10b981', '#3b82f6', '#9ca3af'] }] },
            options: { responsive: true, maintainAspectRatio: false }
        });

        // Fric
        new Chart(document.getElementById('chart-fric'), {
            type: 'bar',
            data: { labels: highFric.map(f => f[0].substring(0, 20) + '...'), datasets: [{ label: 'Friction Score', data: highFric.map(f => f[1].friction_score), backgroundColor: '#ef4444' }] },
            options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false }
        });

        // Surv
        const survData = surv.survival_curve || [];
        new Chart(document.getElementById('chart-surv'), {
            type: 'line',
            data: { labels: survData.map(s => 'Step ' + s.step), datasets: [{ label: 'Survival Rate', data: survData.map(s => s.survival_rate * 100), borderColor: '#10b981', fill: true, backgroundColor: 'rgba(16,185,129,0.1)' }] },
            options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 0, max: 100 } } }
        });

        window.showPatTab = (idx) => {
            document.querySelectorAll('.pat-tab').forEach((el, i) => el.style.display = i === idx ? 'block' : 'none');
            const btns = content.querySelectorAll('.tab-btn');
            btns.forEach((b, i) => b.classList.toggle('active', i === idx));
        };

    } catch (e) { console.error(e); content.innerHTML = '<p class="empty">Failed to load patterns.</p>'; }
}

/* ─── PIPELINE ─── */
async function runPipeline() {
    const btn = document.getElementById('btn-run-pipeline');
    const status = document.getElementById('pipeline-run-status');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>Running...';
    try {
        const res = await fetch(API + '/api/run', { method: 'POST' });
        if (res.ok) {
            status.textContent = 'Pipeline started. Polling status...';
            pollPipeline();
        } else {
            status.textContent = 'Failed to start';
            btn.disabled = false;
            btn.textContent = 'Run LangGraph Pipeline';
        }
    } catch {
        status.textContent = 'Error starting pipeline';
        btn.disabled = false;
        btn.textContent = 'Run LangGraph Pipeline';
    }
}

async function pollPipeline() {
    const btn = document.getElementById('btn-run-pipeline');
    const statusEl = document.getElementById('pipeline-run-status');
    const poll = setInterval(async () => {
        try {
            const s = await fetchJSON('/api/status');
            statusEl.textContent = `Status: ${s.status}` + (s.elapsed_sec ? ` (${s.elapsed_sec}s)` : '');
            if (s.status === 'completed' || s.status === 'failed') {
                clearInterval(poll);
                btn.disabled = false;
                btn.textContent = 'Run LangGraph Pipeline';
                loadOverview();
                loadMetrics();
                loadReport();
            }
        } catch { }
    }, 3000);
}

const METRIC_ORDER = ['funnel_analysis', 'dropoff_analysis', 'friction_points', 'session_metrics',
    'retention_analysis', 'user_segmentation', 'conversion_rates', 'time_to_action', 'event_frequency',
    'temporal_patterns', 'user_journey_insights'];

function buildMetricDataPreview(data) {
    if (!data || typeof data !== 'object') return '';
    if (Array.isArray(data)) {
        const rows = data.slice(0, 3);
        if (!rows.length) return '';
        const keys = Object.keys(rows[0]).slice(0, 4);
        return '<div class="metric-data">' + rows.map(r => keys.map(k => {
            const val = r[k];
            const d = typeof val === 'number' ? (Number.isInteger(val) ? val.toLocaleString() : val.toFixed(1)) : val;
            return `<div class="metric-data-item"><span>${d}</span>${k.replace(/_/g, ' ')}</div>`;
        }).join('')).join('') + '</div>';
    }
    const keys = Object.keys(data).slice(0, 6);
    if (!keys.length) return '';
    return '<div class="metric-data">' + keys.map(k => {
        const v = data[k];
        if (typeof v === 'object') return '';
        const d = typeof v === 'number' ? (Number.isInteger(v) ? v.toLocaleString() : v.toFixed(1)) : v;
        return `<div class="metric-data-item"><span>${d}</span>${k.replace(/_/g, ' ')}</div>`;
    }).join('') + '</div>';
}

async function loadMetrics() {
    const container = document.getElementById('metrics-container');
    try {
        const allData = await fetchJSON('/api/metrics/json');
        let html = '';
        const ordered = METRIC_ORDER.filter(k => k in allData);
        const extra = Object.keys(allData).filter(k => !METRIC_ORDER.includes(k));
        [...ordered, ...extra].forEach(key => {
            const m = allData[key];
            const title = m.title || key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            const iters = m.iterations ? `<span class="badge badge-muted" style="margin-left:8px">${m.iterations} iterations</span>` : '';
            html += `<div class="card">
                <div class="card-header" onclick="toggleCard(this)">
                    <div class="card-title">${title}${iters}</div><span class="card-toggle">expand</span>
                </div>
                <div class="card-body">${buildMetricDataPreview(m.data)}<div>${m.insights || ''}</div>
                </div>
            </div>`;
        });
        container.innerHTML = html || '<p class="empty">No metrics available. Run the pipeline first.</p>';
    } catch { container.innerHTML = '<p class="empty">Could not load metrics. Ensure the pipeline has been run.</p>'; }
}

async function loadReport() {
    const container = document.getElementById('report-container');
    try {
        const ov = await fetchJSON('/api/overview');
        if (ov.report_available) {
            container.innerHTML = '<iframe src="/api/report" class="report-frame" style="height:1200px;border:none"></iframe>';
        } else {
            container.innerHTML = '<p class="empty">No report available. Run the analytics pipeline to generate one.</p>';
        }
    } catch { container.innerHTML = '<p class="empty">Could not check report status.</p>'; }
}

/* ─── INIT ─── */
document.getElementById('user-select').addEventListener('change', e => loadUserData(e.target.value));
document.getElementById('event-filter').addEventListener('change', e => renderEvents(e.target.value));

loadOverview();
loadUsers();
loadSessions();
loadPatterns();
loadMetrics();
loadReport();
