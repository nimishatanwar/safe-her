# 🛡️ SafeHer – Smart Women Safety & Emergency Alert System

**SafeHer** is an emergency assistance platform engineered to minimize the critical steps required for women and vulnerable individuals to communicate distress, acquire help, and escape unsafe situations.

Built with **Python Flask**, a dual-engine relational database (**SQLite** default zero-setup / **MySQL** supported), responsive **HTML5/CSS3/JavaScript**, **OpenStreetMap & Leaflet.js**, and modern browser **Web Audio & Speech APIs**.

---

## 🚀 Key Modules & Capabilities

### 1. 🚨 One-Tap Smart SOS Activation
- **Prominent Pulsing Emergency Button**: Instantly triggers high-priority distress protocol.
- **3-Second Abort Countdown**: Visual countdown ring allows cancelling accidental presses without false alarms.
- **Satellite GPS Pinpoint**: Captures high-accuracy latitude, longitude, and accuracy via the HTML5 Geolocation API.
- **Reverse Geocoding**: Automatically resolves coordinates to human-readable street names and sector landmarks via OpenStreetMap Nominatim.
- **Automated Incident Logging**: Creates immutable emergency incident logs with timestamp, emergency category, and live status.

### 2. 👥 Guardian Contact Management & Speed Dial
- **Priority Emergency Network**: Store trusted contacts (Parents, Siblings, Partners, Guardians) with relationship tags.
- **Primary Guardian Flag**: Designate top-priority primary responder.
- **One-Touch Emergency Calling**: Direct `tel:` links to call guardians or national helplines (`112`, `1091`, `100`, `108`).
- **Instant WhatsApp Distress Links**: Automatically formats and deep-links `https://wa.me/` messages prefilled with live Google Maps coordinate links.
- **Simulated SMS / Notification Dispatcher**: Logs dispatched emergency alerts to each contact in the database audit log.

### 3. 🗺️ Interactive Safe Havens Map (Leaflet.js + OpenStreetMap)
- **Live User Tracking Pin**: Pulsing blue radar pin centered on user coordinates.
- **Categorized Safe Outposts**:
  - 👮 **Police Stations**: 24/7 patrol units and women desk numbers.
  - 🏥 **Emergency Hospitals**: Level-1 trauma centers and urgent care.
  - 💊 **24/7 Pharmacies**: Round-the-clock open chemists.
  - 🛡️ **Women Pink Booths & Safe Havens**: Staffed women protection centers.
  - 🚇 **Metro Stations**: CISF transit security posts.
- **Live Haversine Proximity Calculation**: Automatically computes distance (in KM) to all safe points and sorts nearest havens first.
- **1-Click Navigation**: Direct turn-by-turn directions via Google Maps.

### 4. 🔊 Dual-Frequency Distress Siren (Zero External Files)
- Uses the **HTML5 Web Audio API** to synthesize an oscillating two-tone high-decibel distress alarm (800Hz – 1200Hz).
- Works 100% offline without needing external audio MP3 files or CDN assets.
- Deters attackers and alerts bystanders in crowded or secluded spaces.

### 5. 📱 Discreet Fake Call Escape Simulator
- Provides a natural, airtight excuse to immediately exit menacing situations (suspicious cab rides, being followed, uncomfortable gatherings).
- **Ringtone Synthesizer**: Uses Web Audio API to reproduce authentic dual-frequency telephone cadence (440Hz + 480Hz).
- **Vibration API**: Triggers device haptic vibration patterns.
- **Spoken Voice Escape Script**: Uses Web Speech Synthesis (`SpeechSynthesisUtterance`) to speak an incoming scenario through the phone speaker:
  > *"Hey! Are you outside yet? I'm parked right across the street waiting for you. Come out now!"*

### 6. 🎛️ Administrative Emergency Command Center (`/admin`)
- **Live Incident Queue**: Real-time polling feed of all active emergencies.
- **Audible Emergency Chime**: Plays acoustic alert chime when a new emergency is broadcasted.
- **Interactive Multi-Incident Map**: Plots all active, in-progress, and resolved distress calls with color-coded status pins.
- **Dispatcher Actions**: Update status (`IN_PROGRESS`, `RESOLVED`, `CANCELLED`), assign responding PCR van units, and record officer resolution notes.
- **Citizen Directory**: Inspect registered users, blood groups, emergency medical notes, and guardian counts.
- **Safe Haven Manager**: Add or remove safe points on the live map.

---

## 🗄️ Relational Database Architecture

SafeHer provides an engine supporting both **SQLite** (default zero-configuration for immediate execution) and **MySQL** (via `PyMySQL`):

```
                   ┌──────────────┐
                   │    users     │
                   └──────┬───────┘
                          │ 1:N
        ┌─────────────────┴─────────────────┐
        ▼                                   ▼
┌───────────────────────┐       ┌───────────────────────┐
│  emergency_contacts   │       │   emergency_alerts    │
└───────────────────────┘       └───────────┬───────────┘
                                            │ 1:N
                                            ▼
                                ┌───────────────────────┐
                                │ alert_notification_log│
                                └───────────────────────┘

┌───────────────────────┐
│    safe_locations     │
└───────────────────────┘
```

- **`users`**: `id`, `name`, `email`, `phone`, `password_hash`, `blood_group`, `address`, `medical_notes`, `role`, `created_at`
- **`emergency_contacts`**: `id`, `user_id`, `name`, `phone`, `email`, `relationship`, `is_primary`, `created_at`
- **`emergency_alerts`**: `id`, `user_id`, `alert_type`, `latitude`, `longitude`, `accuracy`, `location_address`, `status`, `notes`, `responded_by`, `resolved_at`, `created_at`
- **`alert_notification_logs`**: `id`, `alert_id`, `recipient_name`, `recipient_phone`, `recipient_email`, `channel`, `delivery_status`, `message_body`, `sent_at`
- **`safe_locations`**: `id`, `name`, `category`, `latitude`, `longitude`, `address`, `contact_number`, `is_24x7`, `description`

---

## 🛠️ Quick Start & Setup

### 1. Requirements
- Python 3.10+ (tested and verified on Python 3.14)
- Packages: `Flask`, `requests`, `pymysql` (already installed)

### 2. Launching the Application
Navigate to the project directory:
```powershell
cd c:\Users\Nimisha\.vscode\safeher
python app.py
```
Access the system in your browser:
👉 **`http://localhost:5000`**

### 3. Pre-Seeded Demo Credentials
| Role | Email | Password | Details |
| :--- | :--- | :--- | :--- |
| **Demo Citizen** | `priya@safeher.com` | `user123` | Pre-configured with 3 trusted contacts & medical profile |
| **Emergency Admin** | `admin@safeher.com` | `admin123` | Full access to Live Monitoring Command Center (`/admin`) |

*New users can also register freely on `/register`!*

### 4. Optional: Switch to MySQL
To connect to an external MySQL server:
```powershell
$env:DATABASE_URL="mysql://username:password@localhost:3306/safeher_db"
python seed_data.py
python app.py
```

### 5. Running Automated Tests
```powershell
python test_app.py
```
*(All 6 unit & integration tests pass with 100% success rate)*

---

## 🔮 Future Enhancements
1. **IoT Wearable & Smartwatch Integration**: Bluetooth trigger bands and wearable panic rings.
2. **Sensor-based Fall & Impact Detection**: Mobile accelerometer and gyroscope threshold monitoring.
3. **Voice-Activated Hotword Recognition**: Hands-free background trigger on phrase detection (e.g. *"SafeHer Help"*).
4. **Live Audio/Video Snapshot Streaming**: Micro-recordings automatically transmitted to dispatchers upon SOS activation.
