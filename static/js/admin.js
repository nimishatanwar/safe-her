/**
 * SafeHer Administrative Monitoring Command Center
 * Real-time SOS incident monitoring, live status dispatch, and map tracking.
 */

let adminMapInstance = null;
let adminMarkers = [];
let knownActiveAlertIds = new Set();
let pollInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    initAdminMap();
    loadActiveAlerts();
    // Poll every 12 seconds
    pollInterval = setInterval(loadActiveAlerts, 12000);
});

/**
 * Initialize Admin Live Map
 */
function initAdminMap() {
    const mapEl = document.getElementById('adminLiveMap');
    if (!mapEl) return;

    adminMapInstance = L.map('adminLiveMap', {
        center: [28.6139, 77.2090],
        zoom: 12
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap | SafeHer Central Command'
    }).addTo(adminMapInstance);
}

/**
 * Fetch and render Active Alerts
 */
async function loadActiveAlerts() {
    try {
        const res = await fetch('/api/admin/active-alerts');
        if (!res.ok) return;
        const data = await res.json();
        const alerts = data.alerts || [];

        renderAlertsTable(alerts);
        renderAdminMapMarkers(alerts);
        updateCommandStats(data.stats);

        // Check if any new active alert arrived to play alert chime
        let hasNew = false;
        alerts.forEach(a => {
            if (a.status === 'ACTIVE' && !knownActiveAlertIds.has(a.id)) {
                hasNew = true;
                knownActiveAlertIds.add(a.id);
            }
        });

        if (hasNew) {
            playAdminEmergencyChime();
        }
    } catch (e) {
        console.error('Error fetching admin alerts:', e);
    }
}

/**
 * Render Live Alerts Table in Admin Dashboard
 */
function renderAlertsTable(alerts) {
    const tbody = document.getElementById('adminAlertsTableBody');
    if (!tbody) return;

    if (alerts.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4 text-white-50">
                    <i class="fa-solid fa-shield-check text-success fs-3 mb-2 d-block"></i>
                    All Clear. No active emergency incidents reported.
                </td>
            </tr>
        `;
        return;
    }

    let rowsHtml = '';
    alerts.forEach(alert => {
        let badgeClass = 'badge-status-active';
        if (alert.status === 'IN_PROGRESS') badgeClass = 'badge-status-in-progress';
        if (alert.status === 'RESOLVED') badgeClass = 'badge-status-resolved';
        if (alert.status === 'CANCELLED') badgeClass = 'badge-status-cancelled';

        const gmapsLink = `https://maps.google.com/?q=${alert.latitude},${alert.longitude}`;

        rowsHtml += `
            <tr class="${alert.status === 'ACTIVE' ? 'table-danger bg-opacity-10' : ''}">
                <td class="fw-bold">#${alert.id}</td>
                <td>
                    <div class="fw-semibold text-white">${alert.user_name}</div>
                    <div class="text-white-50 small"><i class="fa-solid fa-phone"></i> ${alert.user_phone} | Blood: <span class="text-danger fw-bold">${alert.user_blood_group || 'N/A'}</span></div>
                </td>
                <td>
                    <span class="badge bg-secondary text-light">${alert.alert_type}</span>
                </td>
                <td>
                    <div class="small text-white-50">${alert.location_address || 'Coordinates'}</div>
                    <a href="${gmapsLink}" target="_blank" class="small text-info text-decoration-none">
                        <i class="fa-solid fa-location-dot"></i> ${alert.latitude.toFixed(4)}, ${alert.longitude.toFixed(4)}
                    </a>
                </td>
                <td>
                    <span class="badge ${badgeClass} px-2 py-1">${alert.status}</span>
                </td>
                <td class="small text-white-50 font-monospace">${alert.created_at || 'Just now'}</td>
                <td class="text-end">
                    <div class="dropdown">
                        <button class="btn btn-sm btn-outline-light dropdown-toggle" type="button" data-bs-toggle="dropdown">
                            Action
                        </button>
                        <ul class="dropdown-menu dropdown-menu-dark dropdown-menu-end shadow">
                            <li><h6 class="dropdown-header">Update Status</h6></li>
                            <li><button class="dropdown-item text-warning" onclick="openUpdateStatusModal(${alert.id}, 'IN_PROGRESS')"><i class="fa-solid fa-truck-fast"></i> Mark In-Progress / Dispatched</button></li>
                            <li><button class="dropdown-item text-success" onclick="openUpdateStatusModal(${alert.id}, 'RESOLVED')"><i class="fa-solid fa-check-double"></i> Mark Safe & Resolved</button></li>
                            <li><button class="dropdown-item text-secondary" onclick="openUpdateStatusModal(${alert.id}, 'CANCELLED')"><i class="fa-solid fa-ban"></i> False Alarm / Cancel</button></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="tel:${alert.user_phone}"><i class="fa-solid fa-phone"></i> Call User Directly</a></li>
                        </ul>
                    </div>
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = rowsHtml;
}

/**
 * Render Map Markers on Admin Map
 */
function renderAdminMapMarkers(alerts) {
    if (!adminMapInstance) return;

    // Clear old
    adminMarkers.forEach(m => adminMapInstance.removeLayer(m));
    adminMarkers = [];

    const bounds = [];

    alerts.forEach(alert => {
        let pinColor = '#ef4444';
        if (alert.status === 'IN_PROGRESS') pinColor = '#f59e0b';
        if (alert.status === 'RESOLVED') pinColor = '#10b981';

        const markerHtml = `
            <div style="
                width: 34px; height: 34px;
                border-radius: 50%;
                background: ${pinColor};
                border: 3px solid #ffffff;
                color: #ffffff;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 15px;
                box-shadow: 0 0 15px ${pinColor};
                animation: ${alert.status === 'ACTIVE' ? 'sosPulse 1.5s infinite' : 'none'};">
                <i class="fa-solid fa-triangle-exclamation"></i>
            </div>
        `;

        const icon = L.divIcon({
            html: markerHtml,
            className: 'admin-alert-marker',
            iconSize: [34, 34],
            iconAnchor: [17, 17]
        });

        const popupContent = `
            <div style="color: #0f172a; min-width: 220px;">
                <strong>Incident #${alert.id} - ${alert.alert_type}</strong><br>
                <div style="color: #334155; margin: 4px 0;"><strong>Victim:</strong> ${alert.user_name} (${alert.user_phone})</div>
                <div style="color: #64748b; font-size: 0.8rem;">${alert.location_address || 'Location Coordinates'}</div>
                <div style="margin-top: 6px;">
                    <span style="font-weight: 700; color: ${pinColor}; font-size: 0.85rem;">Status: ${alert.status}</span>
                </div>
                <div style="margin-top: 8px;">
                    <a href="tel:${alert.user_phone}" style="display: inline-block; padding: 4px 8px; background: #0f172a; color: white; border-radius: 4px; font-size: 0.8rem; text-decoration: none;">Call Victim</a>
                </div>
            </div>
        `;

        const marker = L.marker([alert.latitude, alert.longitude], { icon: icon }).addTo(adminMapInstance);
        marker.bindPopup(popupContent);
        adminMarkers.push(marker);
        bounds.push([alert.latitude, alert.longitude]);
    });

    if (bounds.length > 0 && adminMapInstance) {
        adminMapInstance.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 });
    }
}

/**
 * Open Status Update Modal
 */
let targetAlertId = null;
let targetStatus = null;

function openUpdateStatusModal(alertId, newStatus) {
    targetAlertId = alertId;
    targetStatus = newStatus;

    document.getElementById('statusModalAlertId').innerText = alertId;
    document.getElementById('statusModalNewState').innerText = newStatus;
    document.getElementById('statusModalNotes').value = '';

    const modalEl = document.getElementById('updateAlertModal');
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
}

/**
 * Submit Alert Status Update
 */
async function submitAlertStatusUpdate() {
    if (!targetAlertId) return;

    const notes = document.getElementById('statusModalNotes').value;
    const responder = document.getElementById('statusModalResponder').value || 'Central Dispatch';

    try {
        const res = await fetch(`/api/admin/alert/${targetAlertId}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                status: targetStatus,
                notes: notes,
                responded_by: responder
            })
        });

        const data = await res.json();
        if (data.status === 'success') {
            const modalEl = document.getElementById('updateAlertModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
            loadActiveAlerts();
            showToast('Incident #' + targetAlertId + ' updated to ' + targetStatus, 'success');
        } else {
            alert(data.message || 'Error updating status.');
        }
    } catch (e) {
        console.error(e);
        alert('Server communication error.');
    }
}

/**
 * Update quick stat counters
 */
function updateCommandStats(stats) {
    if (!stats) return;
    if (document.getElementById('statActiveAlerts')) document.getElementById('statActiveAlerts').innerText = stats.active_alerts;
    if (document.getElementById('statInProgress')) document.getElementById('statInProgress').innerText = stats.in_progress;
    if (document.getElementById('statResolved')) document.getElementById('statResolved').innerText = stats.resolved;
    if (document.getElementById('statTotalUsers')) document.getElementById('statTotalUsers').innerText = stats.total_users;
}

/**
 * Audio Chime when an incoming emergency arrives
 */
function playAdminEmergencyChime() {
    try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        const ctx = new AudioContext();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = 'triangle';
        osc.frequency.setValueAtTime(523.25, ctx.currentTime); // C5
        osc.frequency.setValueAtTime(659.25, ctx.currentTime + 0.15); // E5
        osc.frequency.setValueAtTime(783.99, ctx.currentTime + 0.3); // G5
        osc.frequency.setValueAtTime(1046.50, ctx.currentTime + 0.45); // C6

        gain.gain.setValueAtTime(0.4, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.8);

        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.8);
    } catch (e) {}
}
