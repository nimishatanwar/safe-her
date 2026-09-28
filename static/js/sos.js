/**
 * SafeHer SOS & Emergency Core Controller
 * Handles geolocation, countdown, alert dispatching, sirens, and notifications.
 */

let sosCountdownTimer = null;
let sosCountdownVal = 3;
let currentCoords = { latitude: 28.6139, longitude: 77.2090, accuracy: 25 }; // Default fallback
let isSirenPlaying = false;
let audioCtx = null;
let sirenOscillator = null;
let sirenGain = null;
let sirenInterval = null;

// Initialize location acquisition on load
document.addEventListener('DOMContentLoaded', () => {
    refreshCurrentLocation();
    checkActiveSosState();
});

/**
 * Acquire GPS location using HTML5 Geolocation API
 */
function refreshCurrentLocation(callback) {
    if (!navigator.geolocation) {
        console.warn('Geolocation is not supported by this browser.');
        if (callback) callback(currentCoords);
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (position) => {
            currentCoords = {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
                accuracy: position.coords.accuracy || 15
            };
            console.log('SafeHer GPS Location acquired:', currentCoords);
            const statusEl = document.getElementById('modalLocationStatus');
            if (statusEl) {
                statusEl.innerHTML = `<i class="fa-solid fa-circle-check text-success"></i> GPS Locked: ${currentCoords.latitude.toFixed(4)}, ${currentCoords.longitude.toFixed(4)} (Acc: ±${Math.round(currentCoords.accuracy)}m)`;
            }
            if (callback) callback(currentCoords);
        },
        (error) => {
            console.warn('Geolocation retrieval failed or denied:', error.message);
            const statusEl = document.getElementById('modalLocationStatus');
            if (statusEl) {
                statusEl.innerHTML = `<i class="fa-solid fa-triangle-exclamation text-warning"></i> Using estimated city GPS coordinates.`;
            }
            if (callback) callback(currentCoords);
        },
        {
            enableHighAccuracy: true,
            timeout: 8000,
            maximumAge: 30000
        }
    );
}

/**
 * Open SOS Modal with 3-second countdown
 */
function quickSosTrigger() {
    const sosModalEl = document.getElementById('sosModal');
    if (!sosModalEl) {
        // If triggered from outside, directly execute
        executeSosTriggerNow();
        return;
    }

    const modal = new bootstrap.Modal(sosModalEl);
    modal.show();

    // Reset countdown
    sosCountdownVal = 3;
    const numberEl = document.getElementById('sosCountdownNumber');
    if (numberEl) numberEl.innerText = sosCountdownVal;

    // Refresh GPS right away
    refreshCurrentLocation();

    // Clear any previous timer
    if (sosCountdownTimer) clearInterval(sosCountdownTimer);

    // Start 1-second interval countdown
    sosCountdownTimer = setInterval(() => {
        sosCountdownVal--;
        if (numberEl) numberEl.innerText = sosCountdownVal;

        if (sosCountdownVal <= 0) {
            clearInterval(sosCountdownTimer);
            executeSosTriggerNow();
        }
    }, 1000);

    // Modal close event listener to abort countdown
    sosModalEl.addEventListener('hidden.bs.modal', abortSosCountdown, { once: true });
}

function abortSosCountdown() {
    if (sosCountdownTimer) {
        clearInterval(sosCountdownTimer);
        sosCountdownTimer = null;
    }
}

/**
 * Execute SOS Trigger and notify backend + contacts
 */
async function executeSosTriggerNow() {
    abortSosCountdown();

    const sendBtn = document.getElementById('sosSendNowBtn');
    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> DISPATCHING...';
    }

    const alertType = document.getElementById('modalAlertType') ? document.getElementById('modalAlertType').value : 'Immediate Distress';

    const payload = {
        latitude: currentCoords.latitude,
        longitude: currentCoords.longitude,
        accuracy: currentCoords.accuracy,
        alert_type: alertType,
        notes: 'Dispatched via SafeHer One-Tap SOS emergency trigger.'
    };

    try {
        const response = await fetch('/api/sos/trigger', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        // Close modal if open
        const sosModalEl = document.getElementById('sosModal');
        if (sosModalEl) {
            const modal = bootstrap.Modal.getInstance(sosModalEl);
            if (modal) modal.hide();
        }

        if (data.status === 'success') {
            // Show active SOS banner
            showActiveSosBanner(data.alert);

            // Optional auto siren activation prompt
            playDistressBeepNotification();

            // Automatically launch WhatsApp for the primary contact
            const contactsList = data.contacts || [];
            const primaryContact = contactsList.find(c => c.is_primary) || contactsList[0];
            if (primaryContact && primaryContact.whatsapp_url) {
                try {
                    window.open(primaryContact.whatsapp_url, '_blank');
                } catch(e) {
                    console.log('Popup blocked, available in modal');
                }
            }

            // Notify user with modal listing all direct contact triggers
            showEmergencySuccessAlert(data.alert, data.notifications_count, contactsList, data.has_sms_gateway);
        } else {
            alert('SOS Error: ' + (data.message || 'Unable to record emergency alert. Please dial 112 directly!'));
        }
    } catch (err) {
        console.error('SOS dispatch error:', err);
        alert('Network or server error during SOS dispatch! Please call 112 or Women Helpline 1091 immediately!');
    } finally {
        if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> SEND NOW';
        }
    }
}

/**
 * Show Emergency Dispatched Confirmation Dialog with Direct Contact Buttons
 */
function showEmergencySuccessAlert(alertObj, notificationsCount, contacts = [], hasSmsGateway = false) {
    const lat = alertObj.latitude;
    const lng = alertObj.longitude;

    let contactsHtml = '';
    if (contacts.length > 0) {
        contacts.forEach(c => {
            contactsHtml += `
                <div class="card bg-dark border-secondary p-2 mb-2 text-start">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <div>
                            <strong class="text-white small">${c.name}</strong> 
                            <span class="badge bg-secondary" style="font-size: 0.65rem;">${c.relationship}</span>
                            ${c.is_primary ? '<span class="badge bg-warning text-dark" style="font-size: 0.65rem;">Primary</span>' : ''}
                        </div>
                        <span class="small text-white-50">${c.phone}</span>
                    </div>
                    <div class="d-flex gap-2 mt-1">
                        <a href="${c.whatsapp_url}" target="_blank" class="btn btn-sm btn-success flex-grow-1 fw-bold py-1">
                            <i class="fa-brands fa-whatsapp me-1"></i> Send WhatsApp
                        </a>
                        <a href="${c.sms_url}" class="btn btn-sm btn-outline-info flex-grow-1 fw-bold py-1">
                            <i class="fa-solid fa-comment-sms me-1"></i> Open SMS App
                        </a>
                    </div>
                </div>
            `;
        });
    } else {
        contactsHtml = `
            <div class="alert alert-warning small py-2 mb-2">
                <i class="fa-solid fa-triangle-exclamation me-1"></i> No emergency contacts found. Please add your trusted guardians under Contacts!
            </div>
        `;
    }

    const gatewayNotice = hasSmsGateway
        ? `<div class="badge bg-success bg-opacity-25 text-success border border-success p-2 mb-3 w-100 text-start">
             <i class="fa-solid fa-tower-broadcast me-1"></i> SMS Gateway Active: Automated carrier text dispatched directly to cellular networks.
           </div>`
        : `<div class="card bg-secondary bg-opacity-25 border-secondary p-2 mb-3 text-start small">
             <div class="text-warning fw-bold mb-1"><i class="fa-solid fa-circle-info"></i> Direct Contact Dispatch:</div>
             <div class="text-white-50" style="font-size: 0.78rem;">
               Click <strong>Send WhatsApp</strong> or <strong>Open SMS App</strong> above to instantly broadcast your live GPS to your contacts.
               To enable <em>automatic silent background carrier SMS</em> directly to any phone SIM, configure your free Fast2SMS or Twilio API key below.
             </div>
             <button class="btn btn-sm btn-outline-warning mt-2 py-0 px-2 rounded-pill align-self-start" data-bs-toggle="modal" data-bs-target="#smsGatewayModal">
               <i class="fa-solid fa-key me-1"></i> Configure SMS Gateway (Optional)
             </button>
           </div>`;

    const modalHtml = `
    <div class="modal fade" id="sosDispatchedModal" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered modal-lg">
            <div class="modal-content bg-dark text-white border-danger shadow-2xl">
                <div class="modal-header bg-danger text-white">
                    <h5 class="modal-title fw-bold"><i class="fa-solid fa-tower-broadcast fa-fade"></i> EMERGENCY SOS BROADCASTED!</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body text-center py-3">
                    <div class="display-5 text-danger mb-1"><i class="fa-solid fa-circle-check"></i></div>
                    <h4 class="fw-bold mb-1">SOS Alert Dispatched</h4>
                    <p class="text-white-50 small mb-3">Live satellite coordinates logged & recorded for emergency dispatchers.</p>

                    <div class="card bg-secondary bg-opacity-25 border-secondary p-2 text-start mb-3">
                        <div class="small text-white-50">Location: <strong class="text-white">${alertObj.location_address || 'Current Pinpoint Location'}</strong></div>
                        <div class="small text-white-50">GPS Coordinates: <code class="text-info">${lat.toFixed(5)}, ${lng.toFixed(5)}</code></div>
                    </div>

                    ${gatewayNotice}

                    <div class="text-start mb-2">
                        <h6 class="fw-bold text-white mb-2"><i class="fa-solid fa-paper-plane text-primary me-1"></i> Send Direct Alerts to Contacts:</h6>
                        ${contactsHtml}
                    </div>

                    <div class="d-flex justify-content-center gap-2 mt-3">
                        <button class="btn btn-outline-warning rounded-pill" onclick="toggleSafetySiren()">
                            <i class="fa-solid fa-volume-high me-1"></i> <span id="modalSirenBtnText">Sound Loud Alarm / Siren</span>
                        </button>
                        <a href="/history" class="btn btn-outline-light rounded-pill">View Incident Log</a>
                    </div>
                </div>
                <div class="modal-footer border-secondary justify-content-between">
                    <button type="button" class="btn btn-outline-light rounded-pill" data-bs-dismiss="modal">Close</button>
                    <button type="button" class="btn btn-outline-success rounded-pill" onclick="cancelActiveSos(${alertObj.id})">
                        <i class="fa-solid fa-check"></i> I am Safe Now (Cancel SOS)
                    </button>
                </div>
            </div>
        </div>
    </div>`;

    // Append and trigger modal
    const existing = document.getElementById('sosDispatchedModal');
    if (existing) existing.remove();
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const modal = new bootstrap.Modal(document.getElementById('sosDispatchedModal'));
    modal.show();
}

/**
 * Check if the current user has an active SOS
 */
async function checkActiveSosState() {
    try {
        const response = await fetch('/api/sos/active');
        if (!response.ok) return;
        const data = await response.json();
        if (data.has_active && data.alert) {
            showActiveSosBanner(data.alert);
        } else {
            hideActiveSosBanner();
        }
    } catch (e) {
        // Ignored if user not logged in
    }
}

function showActiveSosBanner(alertObj) {
    const banner = document.getElementById('activeSosBanner');
    const bannerText = document.getElementById('activeSosBannerText');
    if (banner) {
        banner.classList.remove('d-none');
        if (bannerText) {
            bannerText.innerText = `Emergency Alert #${alertObj.id} (${alertObj.alert_type}) active at ${alertObj.location_address || 'Coordinates'}. Responders & contacts notified.`;
        }
    }
}

function hideActiveSosBanner() {
    const banner = document.getElementById('activeSosBanner');
    if (banner) {
        banner.classList.add('d-none');
    }
}

/**
 * User cancels their active SOS alert
 */
async function cancelActiveSos(alertId) {
    if (!confirm('Are you sure you want to mark yourself safe and cancel the active emergency alert?')) {
        return;
    }

    try {
        const response = await fetch('/api/sos/cancel' + (alertId ? `/${alertId}` : ''), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (data.status === 'success') {
            hideActiveSosBanner();
            if (isSirenPlaying) toggleSafetySiren();
            alert('Emergency Alert marked as resolved. Contacts notified that you are safe.');
            window.location.reload();
        } else {
            alert(data.message || 'Unable to cancel alert.');
        }
    } catch (e) {
        console.error('Error cancelling alert:', e);
    }
}

/**
 * Web Audio API Distress Siren Sound Generator (Zero External Sound File Needed)
 * Produces a loud dual-frequency oscillating police/distress siren.
 */
function toggleSafetySiren() {
    const sirenBtn = document.getElementById('sirenToggleBtn');
    const modalSirenBtnText = document.getElementById('modalSirenBtnText');

    if (isSirenPlaying) {
        // Stop Siren
        if (sirenInterval) clearInterval(sirenInterval);
        if (sirenOscillator) {
            try { sirenOscillator.stop(); sirenOscillator.disconnect(); } catch (e) {}
        }
        if (audioCtx) {
            try { audioCtx.close(); } catch (e) {}
            audioCtx = null;
        }
        isSirenPlaying = false;

        if (sirenBtn) {
            sirenBtn.classList.remove('siren-toggle-active');
            sirenBtn.innerHTML = '<i class="fa-solid fa-volume-high text-warning"></i> Start Loud Siren';
        }
        if (modalSirenBtnText) modalSirenBtnText.innerText = 'Sound Loud Alarm / Siren';
    } else {
        // Start Siren
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            audioCtx = new AudioContext();
            sirenOscillator = audioCtx.createOscillator();
            sirenGain = audioCtx.createGain();

            sirenOscillator.type = 'sawtooth';
            sirenGain.gain.setValueAtTime(0.8, audioCtx.currentTime);

            sirenOscillator.connect(sirenGain);
            sirenGain.connect(audioCtx.destination);

            let freqHigh = true;
            sirenOscillator.frequency.setValueAtTime(800, audioCtx.currentTime);
            sirenOscillator.start();

            // Modulate pitch every 350ms
            sirenInterval = setInterval(() => {
                if (!audioCtx) return;
                const targetFreq = freqHigh ? 1200 : 700;
                sirenOscillator.frequency.exponentialRampToValueAtTime(targetFreq, audioCtx.currentTime + 0.3);
                freqHigh = !freqHigh;
            }, 350);

            isSirenPlaying = true;

            if (sirenBtn) {
                sirenBtn.classList.add('siren-toggle-active');
                sirenBtn.innerHTML = '<i class="fa-solid fa-volume-xmark"></i> STOP SIREN ALARM';
            }
            if (modalSirenBtnText) modalSirenBtnText.innerText = 'STOP Siren Alarm';
        } catch (err) {
            console.error('AudioContext error:', err);
            alert('Web Audio API not supported on this browser device.');
        }
    }
}

/**
 * Quick short notification beep
 */
function playDistressBeepNotification() {
    try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        const ctx = new AudioContext();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, ctx.currentTime);
        gain.gain.setValueAtTime(0.3, ctx.currentTime);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.4);
    } catch(e) {}
}
