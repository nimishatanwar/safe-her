/**
 * SafeHer Global Utilities and UI Helpers
 */

document.addEventListener('DOMContentLoaded', () => {
    // Auto dismiss standard alerts after 5 seconds
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(alert => {
            const bsAlert = bootstrap.Alert.getInstance(alert);
            if (bsAlert) bsAlert.close();
        });
    }, 6000);
});

/**
 * Toast / In-app Flash notification helper
 */
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    const id = 'toast_' + Date.now();
    const toastHtml = `
        <div id="${id}" class="toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0 shadow" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fa-solid ${type === 'danger' || type === 'error' ? 'fa-circle-exclamation' : 'fa-circle-check'} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    const toastEl = document.getElementById(id);
    const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
    toast.show();
}

function createToastContainer() {
    const div = document.createElement('div');
    div.id = 'toastContainer';
    div.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    div.style.zIndex = '9999';
    document.body.appendChild(div);
    return div;
}

/**
 * Copy location coordinates to clipboard
 */
function copyCoordsToClipboard(lat, lng) {
    const text = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
    navigator.clipboard.writeText(text).then(() => {
        showToast('Coordinates copied to clipboard: ' + text, 'success');
    }).catch(() => {
        showToast('Coordinates: ' + text, 'info');
    });
}

/**
 * Save SMS Gateway Configuration (Fast2SMS / Twilio)
 */
async function saveSmsGatewayConfig() {
    const fast2sms_key = document.getElementById('gatewayFast2SmsKey') ? document.getElementById('gatewayFast2SmsKey').value : '';
    const twilio_sid = document.getElementById('gatewayTwilioSid') ? document.getElementById('gatewayTwilioSid').value : '';
    const twilio_token = document.getElementById('gatewayTwilioToken') ? document.getElementById('gatewayTwilioToken').value : '';
    const twilio_phone = document.getElementById('gatewayTwilioPhone') ? document.getElementById('gatewayTwilioPhone').value : '';

    try {
        const res = await fetch('/api/settings/sms-gateway', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                fast2sms_key: fast2sms_key,
                twilio_sid: twilio_sid,
                twilio_token: twilio_token,
                twilio_phone: twilio_phone
            })
        });
        const data = await res.json();
        if (data.status === 'success') {
            const modalEl = document.getElementById('smsGatewayModal');
            if (modalEl) {
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) modal.hide();
            }
            showToast('SMS Gateway successfully configured! Real cellular carrier texts will now be dispatched on SOS.', 'success');
        } else {
            showToast(data.message || 'Error saving gateway configuration.', 'error');
        }
    } catch(e) {
        showToast('Server communication error.', 'error');
    }
}

