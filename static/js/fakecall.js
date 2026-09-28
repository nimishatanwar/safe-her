/**
 * SafeHer Fake Call Escape Simulator
 * Uses Web Audio API for authentic ringtone synthesis, Vibration API,
 * and Web Speech Synthesis for spoken escape dialogue.
 */

let fakeCallTimer = null;
let ringAudioCtx = null;
let ringOsc1 = null;
let ringOsc2 = null;
let ringInterval = null;
let callDurationTimer = null;
let callSeconds = 0;

/**
 * Schedule Fake Call
 */
function scheduleFakeCall() {
    const callerName = document.getElementById('callerNameInput').value || 'Dad';
    const callerNumber = document.getElementById('callerNumberInput').value || '+91 98765 43210';
    const delaySeconds = parseInt(document.getElementById('callDelaySelect').value, 10);

    const statusEl = document.getElementById('fakeCallStatus');
    const scheduleBtn = document.getElementById('scheduleCallBtn');

    if (delaySeconds === 0) {
        triggerIncomingCall(callerName, callerNumber);
        return;
    }

    if (scheduleBtn) scheduleBtn.disabled = true;
    let remaining = delaySeconds;

    if (statusEl) {
        statusEl.innerHTML = `<div class="alert alert-warning py-2 mb-0"><i class="fa-solid fa-hourglass-half fa-spin"></i> Incoming call from <strong>${callerName}</strong> in <span id="fakeTimerCountdown" class="fw-bold">${remaining}</span> seconds... (Lock your screen or put phone on table)</div>`;
    }

    fakeCallTimer = setInterval(() => {
        remaining--;
        const cntEl = document.getElementById('fakeTimerCountdown');
        if (cntEl) cntEl.innerText = remaining;

        if (remaining <= 0) {
            clearInterval(fakeCallTimer);
            if (scheduleBtn) scheduleBtn.disabled = false;
            if (statusEl) statusEl.innerHTML = '';
            triggerIncomingCall(callerName, callerNumber);
        }
    }, 1000);
}

function cancelScheduledFakeCall() {
    if (fakeCallTimer) {
        clearInterval(fakeCallTimer);
        fakeCallTimer = null;
    }
    const statusEl = document.getElementById('fakeCallStatus');
    if (statusEl) statusEl.innerHTML = '<div class="alert alert-info py-2 mb-0">Scheduled call cancelled.</div>';
    const scheduleBtn = document.getElementById('scheduleCallBtn');
    if (scheduleBtn) scheduleBtn.disabled = false;
}

/**
 * Show Incoming Call Fullscreen Screen
 */
function triggerIncomingCall(callerName, callerNumber) {
    document.getElementById('fakeCallerNameDisplay').innerText = callerName;
    document.getElementById('fakeCallerNumberDisplay').innerText = callerNumber;

    const screenEl = document.getElementById('fakeCallOverlay');
    if (screenEl) {
        screenEl.classList.remove('d-none');
        document.getElementById('incomingCallView').classList.remove('d-none');
        document.getElementById('activeCallView').classList.add('d-none');
    }

    // Start Synthesized Ringtone
    startRingtone();

    // Trigger Device Vibration if supported
    if ('vibrate' in navigator) {
        navigator.vibrate([600, 400, 600, 400, 600, 1000]);
    }
}

/**
 * Accept the Fake Call
 */
function answerFakeCall() {
    stopRingtone();
    if ('vibrate' in navigator) navigator.vibrate(0);

    // Switch view
    document.getElementById('incomingCallView').classList.add('d-none');
    document.getElementById('activeCallView').classList.remove('d-none');

    // Start in-call duration timer
    callSeconds = 0;
    const durationEl = document.getElementById('callDurationText');
    callDurationTimer = setInterval(() => {
        callSeconds++;
        const mins = String(Math.floor(callSeconds / 60)).padStart(2, '0');
        const secs = String(callSeconds % 60).padStart(2, '0');
        if (durationEl) durationEl.innerText = `${mins}:${secs}`;
    }, 1000);

    // Speak Escape Scenario Dialogue
    playSpokenEscapeDialogue();
}

/**
 * Decline or End Fake Call
 */
function endFakeCall() {
    stopRingtone();
    if ('vibrate' in navigator) navigator.vibrate(0);
    if (callDurationTimer) {
        clearInterval(callDurationTimer);
        callDurationTimer = null;
    }
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
    }

    const screenEl = document.getElementById('fakeCallOverlay');
    if (screenEl) {
        screenEl.classList.add('d-none');
    }
}

/**
 * Web Audio API Dual-Frequency Telephone Ringtone Generator
 */
function startRingtone() {
    try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        ringAudioCtx = new AudioContext();

        const playRingPulse = () => {
            if (!ringAudioCtx) return;
            ringOsc1 = ringAudioCtx.createOscillator();
            ringOsc2 = ringAudioCtx.createOscillator();
            const gain = ringAudioCtx.createGain();

            // Dual tone frequencies (US/UK telephone standard 440Hz + 480Hz)
            ringOsc1.frequency.setValueAtTime(440, ringAudioCtx.currentTime);
            ringOsc2.frequency.setValueAtTime(480, ringAudioCtx.currentTime);

            gain.gain.setValueAtTime(0.25, ringAudioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ringAudioCtx.currentTime + 1.8);

            ringOsc1.connect(gain);
            ringOsc2.connect(gain);
            gain.connect(ringAudioCtx.destination);

            ringOsc1.start();
            ringOsc2.start();
            ringOsc1.stop(ringAudioCtx.currentTime + 1.8);
            ringOsc2.stop(ringAudioCtx.currentTime + 1.8);
        };

        playRingPulse();
        ringInterval = setInterval(playRingPulse, 3200);
    } catch (e) {
        console.warn('Web Audio error:', e);
    }
}

function stopRingtone() {
    if (ringInterval) {
        clearInterval(ringInterval);
        ringInterval = null;
    }
    if (ringAudioCtx) {
        try { ringAudioCtx.close(); } catch (e) {}
        ringAudioCtx = null;
    }
}

/**
 * Spoken Escape Dialogue via SpeechSynthesis
 */
function playSpokenEscapeDialogue() {
    if (!('speechSynthesis' in window)) return;

    window.speechSynthesis.cancel(); // Stop any pending speech

    const escapeLines = [
        "Hey! Are you outside yet? I'm parked right across the street waiting for you.",
        "Come out right now, I have the car headlights on so you can see me.",
        "Don't worry, take your time, but come right over to the car."
    ];

    let delay = 1200;
    escapeLines.forEach(line => {
        setTimeout(() => {
            if (document.getElementById('activeCallView') && !document.getElementById('activeCallView').classList.contains('d-none')) {
                const utterance = new SpeechSynthesisUtterance(line);
                utterance.rate = 0.95;
                utterance.pitch = 1.0;
                window.speechSynthesis.speak(utterance);
            }
        }, delay);
        delay += 4000;
    });
}
