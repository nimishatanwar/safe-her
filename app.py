"""
SafeHer – Smart Women Safety & Emergency Alert System
Main Flask Application Server
"""

import os
import functools
import requests
from urllib.parse import quote
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from config import Config
from database import db
from models import (
    User, EmergencyContact, EmergencyAlert,
    AlertNotificationLog, SafeLocation
)

app = Flask(__name__)
app.config.from_object(Config)

# -------------------------------------------------------------
# Authentication & Context Helpers
# -------------------------------------------------------------

def get_current_user():
    """Retrieve logged in user from session."""
    user_id = session.get('user_id')
    if user_id:
        return User.find_by_id(user_id)
    return None

@app.context_processor
def inject_current_user():
    """Inject current_user into all template contexts."""
    return {'current_user': get_current_user()}

def login_required(view_func):
    """Ensure user is authenticated."""
    @functools.wraps(view_func)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please sign in to access this feature.', 'warning')
            return redirect(url_for('login', next=request.url))
        return view_func(*args, **kwargs)
    return decorated_function

def admin_required(view_func):
    """Ensure user has admin privileges."""
    @functools.wraps(view_func)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or user.role != 'admin':
            flash('Access restricted to emergency administration personnel.', 'danger')
            return redirect(url_for('dashboard'))
        return view_func(*args, **kwargs)
    return decorated_function

def reverse_geocode(lat, lon):
    """Obtain approximate human-readable address from coordinates."""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
        headers = {'User-Agent': 'SafeHer-WomenSafety-Platform/1.0 (contact: emergency@safeher.org)'}
        res = requests.get(url, headers=headers, timeout=2.5)
        if res.status_code == 200:
            data = res.json()
            display_name = data.get('display_name')
            if display_name:
                return display_name
    except Exception as e:
        # Fallback cleanly without stalling the emergency dispatch
        pass
    return f"Area Coordinates: {lat:.4f}, {lon:.4f}"

def send_carrier_sms(phone, message):
    """
    Attempts to send a real physical SMS via Fast2SMS (India) or Twilio
    if configured via environment variables or app_settings table.
    """
    clean_digits = ''.join(c for c in phone if c.isdigit())

    # 1. Fast2SMS Gateway (India)
    fast2sms_key = db.get_setting('FAST2SMS_API_KEY') or os.environ.get('FAST2SMS_API_KEY')
    if fast2sms_key:
        try:
            ten_digit = clean_digits[-10:] if len(clean_digits) >= 10 else clean_digits
            url = "https://www.fast2sms.com/dev/bulkV2"
            headers = {
                'authorization': fast2sms_key.strip(),
                'Content-Type': 'application/json'
            }
            payload = {
                "route": "q",
                "message": message[:155],
                "language": "english",
                "flash": 0,
                "numbers": ten_digit
            }
            res = requests.post(url, json=payload, headers=headers, timeout=5)
            print(f"[Fast2SMS Carrier] Dispatched to {ten_digit}: {res.status_code} - {res.text}")
            return {'gateway': 'Fast2SMS', 'status': res.status_code, 'response': res.text}
        except Exception as e:
            print(f"[Fast2SMS Error] {e}")

    # 2. Twilio Gateway (Global)
    twilio_sid = db.get_setting('TWILIO_ACCOUNT_SID') or os.environ.get('TWILIO_ACCOUNT_SID')
    twilio_token = db.get_setting('TWILIO_AUTH_TOKEN') or os.environ.get('TWILIO_AUTH_TOKEN')
    twilio_phone = db.get_setting('TWILIO_PHONE_NUMBER') or os.environ.get('TWILIO_PHONE_NUMBER')
    if twilio_sid and twilio_token and twilio_phone:
        try:
            dest_phone = phone.strip()
            if not dest_phone.startswith('+'):
                dest_phone = '+' + clean_digits
            url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid.strip()}/Messages.json"
            res = requests.post(
                url,
                data={'To': dest_phone, 'From': twilio_phone.strip(), 'Body': message[:160]},
                auth=(twilio_sid.strip(), twilio_token.strip()),
                timeout=5
            )
            print(f"[Twilio Carrier] Dispatched to {dest_phone}: {res.status_code} - {res.text}")
            return {'gateway': 'Twilio', 'status': res.status_code, 'response': res.text}
        except Exception as e:
            print(f"[Twilio Error] {e}")

    return None


# -------------------------------------------------------------
# Web Page Routes
# -------------------------------------------------------------

@app.route('/')
def index():
    """Landing / Home Page with quick SOS trigger."""
    current_user = get_current_user()
    return render_template('index.html', current_user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User & Admin Sign In."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        user = User.find_by_email(email)
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_role'] = user.role
            flash(f"Welcome back, {user.name}!", "success")
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password. Try demo credentials below.", "danger")

    return render_template('login.html', email=request.args.get('email', ''))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Citizen Registration."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        blood_group = request.form.get('blood_group', '').strip()
        address = request.form.get('address', '').strip()
        medical_notes = request.form.get('medical_notes', '').strip()

        if not name or not email or not phone or not password:
            flash("Please fill in all required fields.", "warning")
            return render_template('register.html')

        existing = User.find_by_email(email)
        if existing:
            flash("An account with this email already exists. Please sign in.", "warning")
            return redirect(url_for('login', email=email))

        new_user = User.create(
            name=name,
            email=email,
            phone=phone,
            password=password,
            blood_group=blood_group,
            address=address,
            medical_notes=medical_notes,
            role='user'
        )

        session['user_id'] = new_user.id
        session['user_role'] = new_user.role
        flash("Registration successful! Now add your primary emergency contacts.", "success")
        return redirect(url_for('contacts_view'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    """Clear session and sign out."""
    session.clear()
    flash("You have safely signed out of SafeHer.", "info")
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main User Safety Hub."""
    user = get_current_user()
    contacts = user.get_contacts()
    return render_template('dashboard.html', contacts=contacts)

@app.route('/contacts')
@login_required
def contacts_view():
    """Manage Emergency Contacts."""
    user = get_current_user()
    contacts = user.get_contacts()
    return render_template('contacts.html', contacts=contacts)

@app.route('/contacts/add', methods=['POST'])
@login_required
def add_contact():
    """Add a new trusted guardian contact."""
    user = get_current_user()
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()
    relationship = request.form.get('relationship', 'Guardian').strip()
    is_primary = request.form.get('is_primary') == '1'

    if not name or not phone:
        flash("Contact name and phone are required.", "warning")
        return redirect(url_for('contacts_view'))

    EmergencyContact.create(
        user_id=user.id,
        name=name,
        phone=phone,
        email=email,
        relationship=relationship,
        is_primary=is_primary
    )
    flash(f"Emergency contact '{name}' added successfully.", "success")
    return redirect(url_for('contacts_view'))

@app.route('/contacts/delete/<int:contact_id>', methods=['POST'])
@login_required
def delete_contact(contact_id):
    """Delete an emergency contact."""
    user = get_current_user()
    EmergencyContact.delete(contact_id, user.id)
    flash("Emergency contact removed.", "info")
    return redirect(url_for('contacts_view'))

@app.route('/map')
def map_view():
    """Interactive Safe Havens Map."""
    return render_template('map_view.html')

@app.route('/fake-call')
def fake_call_view():
    """Discreet Escape Simulator."""
    return render_template('fake_call.html')

@app.route('/history')
@login_required
def alert_history_view():
    """User Incident Logs."""
    user = get_current_user()
    alerts = user.get_alerts()
    return render_template('alert_history.html', alerts=alerts)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile_view():
    """Edit Profile and Emergency Information."""
    user = get_current_user()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        blood_group = request.form.get('blood_group', '').strip()
        address = request.form.get('address', '').strip()
        medical_notes = request.form.get('medical_notes', '').strip()

        User.update_profile(user.id, name, phone, blood_group, address, medical_notes)
        flash("Profile updated successfully.", "success")
        return redirect(url_for('profile_view'))

    return render_template('profile.html')

# -------------------------------------------------------------
# Administrative Command Center Routes
# -------------------------------------------------------------

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Live Emergency Monitoring Command Center."""
    stats = EmergencyAlert.get_stats()
    return render_template('admin_dashboard.html', stats=stats)

@app.route('/admin/users')
@admin_required
def admin_users():
    """Registered Citizen Directory."""
    users = User.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/safe-locations')
@admin_required
def admin_safe_locations():
    """Manage Safe Havens."""
    locations = SafeLocation.all()
    return render_template('admin_safe_locations.html', locations=locations)

@app.route('/admin/safe-locations/add', methods=['POST'])
@admin_required
def add_safe_location_action():
    """Add a new safe haven."""
    name = request.form.get('name', '').strip()
    category = request.form.get('category', 'police').strip()
    latitude = request.form.get('latitude', 0.0)
    longitude = request.form.get('longitude', 0.0)
    address = request.form.get('address', '').strip()
    contact_number = request.form.get('contact_number', '').strip()
    is_24x7 = request.form.get('is_24x7') == '1'
    description = request.form.get('description', '').strip()

    SafeLocation.create(name, category, latitude, longitude, address, contact_number, is_24x7, description)
    flash(f"Safe Haven '{name}' added successfully.", "success")
    return redirect(url_for('admin_safe_locations'))

@app.route('/admin/safe-locations/delete/<int:loc_id>', methods=['POST'])
@admin_required
def delete_safe_location_action(loc_id):
    """Delete a safe haven."""
    SafeLocation.delete(loc_id)
    flash("Safe location removed.", "info")
    return redirect(url_for('admin_safe_locations'))

# -------------------------------------------------------------
# REST APIs for Real-Time Dynamic Frontend
# -------------------------------------------------------------

@app.route('/api/sos/trigger', methods=['POST'])
def api_sos_trigger():
    """
    Trigger emergency SOS alert.
    Dispatches automated notification logs to all emergency contacts.
    """
    user = get_current_user()
    # Allow anonymous guest SOS trigger fallback if user not logged in
    user_id = user.id if user else None

    # If anonymous user presses SOS on landing page without login,
    # link to demo Priya account so contacts can receive it!
    if not user_id:
        demo_user = User.find_by_email('priya@safeher.com')
        if demo_user:
            user_id = demo_user.id
            user = demo_user
        else:
            first_user = User.find_by_id(1)
            user_id = first_user.id if first_user else 1
            user = first_user

    data = request.get_json() or {}
    lat = float(data.get('latitude', 28.6139))
    lon = float(data.get('longitude', 77.2090))
    accuracy = float(data.get('accuracy', 15.0))
    alert_type = data.get('alert_type', 'Immediate Distress')
    notes = data.get('notes', 'Triggered via SafeHer One-Tap SOS.')

    # Reverse geocode street address
    address = reverse_geocode(lat, lon)

    # Record emergency event
    alert = EmergencyAlert.create(
        user_id=user_id,
        alert_type=alert_type,
        latitude=lat,
        longitude=lon,
        accuracy=accuracy,
        location_address=address,
        notes=notes
    )

    # Dispatched notifications and contact links
    contacts = user.get_contacts() if user else []
    notifications_count = 0
    contacts_dispatch = []

    gmaps_url = f"https://maps.google.com/?q={lat},{lon}"
    sos_msg = (
        f"🚨 EMERGENCY SOS ALERT! {user.name if user else 'SafeHer Citizen'} is in immediate danger! "
        f"Nature: {alert_type}. "
        f"GPS Location: {gmaps_url} (Address: {address}). "
        f"Incident #{alert.id}."
    )

    for c in contacts:
        raw_phone = c.phone.strip()
        clean_digits = ''.join(ch for ch in raw_phone if ch.isdigit())
        if len(clean_digits) == 10:
            wa_phone = '91' + clean_digits
        else:
            wa_phone = clean_digits

        wa_url = f"https://api.whatsapp.com/send?phone={wa_phone}&text={quote(sos_msg)}"
        sms_url = f"sms:{raw_phone}?body={quote(sos_msg)}"

        # Attempt real carrier SMS via configured gateway
        carrier_res = send_carrier_sms(raw_phone, sos_msg)
        carrier_sent = bool(carrier_res and carrier_res.get('status') in [200, 201])

        # Record notification logs in audit table
        AlertNotificationLog.create(
            alert_id=alert.id,
            recipient_name=c.name,
            recipient_phone=c.phone,
            recipient_email=c.email,
            channel='SMS',
            message_body=sos_msg,
            delivery_status='SENT (Gateway)' if carrier_sent else 'PENDING_DIRECT'
        )
        AlertNotificationLog.create(
            alert_id=alert.id,
            recipient_name=c.name,
            recipient_phone=c.phone,
            recipient_email=c.email,
            channel='WHATSAPP',
            message_body=sos_msg,
            delivery_status='PENDING_DIRECT'
        )
        notifications_count += 2

        contacts_dispatch.append({
            'id': c.id,
            'name': c.name,
            'phone': c.phone,
            'relationship': c.relationship,
            'is_primary': c.is_primary,
            'whatsapp_url': wa_url,
            'sms_url': sms_url,
            'carrier_sent': carrier_sent
        })

    # Always log system dispatcher notification
    AlertNotificationLog.create(
        alert_id=alert.id,
        recipient_name="SafeHer Central Emergency Dispatch",
        recipient_phone="112",
        channel="SYSTEM",
        message_body=f"High Priority Alert #{alert.id} from {user.name if user else 'Citizen'} at {address}",
        delivery_status="DELIVERED"
    )

    has_gateway = bool(db.get_setting('FAST2SMS_API_KEY') or (db.get_setting('TWILIO_ACCOUNT_SID') and db.get_setting('TWILIO_AUTH_TOKEN')))

    return jsonify({
        'status': 'success',
        'message': 'SOS alert broadcasted successfully.',
        'alert': alert.to_dict(),
        'contacts': contacts_dispatch,
        'notifications_count': notifications_count,
        'has_sms_gateway': has_gateway
    })

@app.route('/api/settings/sms-gateway', methods=['GET', 'POST'])
def api_sms_gateway_settings():
    """Configure or view SMS Gateway credentials (Fast2SMS / Twilio)."""
    if request.method == 'POST':
        data = request.get_json() or {}
        fast2sms_key = data.get('fast2sms_key', '').strip()
        twilio_sid = data.get('twilio_sid', '').strip()
        twilio_token = data.get('twilio_token', '').strip()
        twilio_phone = data.get('twilio_phone', '').strip()

        if fast2sms_key:
            db.set_setting('FAST2SMS_API_KEY', fast2sms_key)
        if twilio_sid:
            db.set_setting('TWILIO_ACCOUNT_SID', twilio_sid)
        if twilio_token:
            db.set_setting('TWILIO_AUTH_TOKEN', twilio_token)
        if twilio_phone:
            db.set_setting('TWILIO_PHONE_NUMBER', twilio_phone)

        return jsonify({'status': 'success', 'message': 'SMS Gateway settings updated!'})

    return jsonify({
        'fast2sms_configured': bool(db.get_setting('FAST2SMS_API_KEY')),
        'twilio_configured': bool(db.get_setting('TWILIO_ACCOUNT_SID') and db.get_setting('TWILIO_AUTH_TOKEN'))
    })


@app.route('/api/sos/active')
def api_sos_active():
    """Check if current logged in user has an active emergency alert."""
    user = get_current_user()
    if not user:
        return jsonify({'has_active': False})

    alert = EmergencyAlert.find_active_by_user(user.id)
    if alert:
        return jsonify({'has_active': True, 'alert': alert.to_dict()})
    return jsonify({'has_active': False})

@app.route('/api/sos/cancel', defaults={'alert_id': None}, methods=['POST'])
@app.route('/api/sos/cancel/<int:alert_id>', methods=['POST'])
@login_required
def api_sos_cancel(alert_id):
    """Mark active emergency alert as resolved or cancelled by user."""
    user = get_current_user()
    if not alert_id:
        active = EmergencyAlert.find_active_by_user(user.id)
        if active:
            alert_id = active.id

    if not alert_id:
        return jsonify({'status': 'error', 'message': 'No active alert found.'}), 404

    EmergencyAlert.update_status(
        alert_id=alert_id,
        status='RESOLVED',
        notes='Citizen marked themselves safe / False alarm resolved.',
        responded_by=f"Citizen ({user.name})"
    )

    return jsonify({'status': 'success', 'message': 'Emergency alert marked as resolved.'})

@app.route('/api/safe-locations')
def api_safe_locations():
    """Return all verified safe locations."""
    category = request.args.get('category')
    locations = SafeLocation.all(category=category)
    return jsonify({
        'status': 'success',
        'locations': [loc.to_dict() for loc in locations]
    })

@app.route('/api/contacts/send-test/<int:contact_id>', methods=['POST'])
@login_required
def api_send_test_contact(contact_id):
    """Send simulated test alert to a specific guardian."""
    user = get_current_user()
    contact = EmergencyContact.find_by_id(contact_id)
    if not contact or contact.user_id != user.id:
        return jsonify({'status': 'error', 'message': 'Contact not found.'}), 404

    return jsonify({
        'status': 'success',
        'message': f"Simulated verification ping dispatched to {contact.name} ({contact.phone})."
    })

@app.route('/api/admin/active-alerts')
@admin_required
def api_admin_active_alerts():
    """Return active/in-progress alerts for administrative monitoring feed."""
    alerts = EmergencyAlert.get_active_alerts()
    stats = EmergencyAlert.get_stats()
    return jsonify({
        'status': 'success',
        'alerts': [a.to_dict() for a in alerts],
        'stats': stats
    })

@app.route('/api/admin/alert/<int:alert_id>/status', methods=['POST'])
@admin_required
def api_admin_update_alert_status(alert_id):
    """Update incident status and add responder audit log."""
    data = request.get_json() or {}
    new_status = data.get('status', 'IN_PROGRESS')
    notes = data.get('notes', '')
    responder = data.get('responded_by', 'Central Dispatch')

    alert = EmergencyAlert.find_by_id(alert_id)
    if not alert:
        return jsonify({'status': 'error', 'message': 'Alert incident not found.'}), 404

    EmergencyAlert.update_status(alert_id, new_status, notes=notes, responded_by=responder)
    return jsonify({'status': 'success', 'message': f"Alert #{alert_id} updated to {new_status}."})

# -------------------------------------------------------------
# Cloud Startup Initializer & Auto-Seed
# -------------------------------------------------------------

try:
    with app.app_context():
        from seed_data import seed
        if not User.find_by_email('admin@safeher.com'):
            print("[Cloud Deploy] Auto-seeding initial database tables...")
            seed()
except Exception as e:
    print(f"[Auto-seed Notice] {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n========================================================")
    print(f"  SafeHer – Smart Women Safety & Emergency System")
    print(f"  Access URL: http://localhost:{port}")
    print(f"  Demo User:  priya@safeher.com / user123")
    print(f"  Admin:      admin@safeher.com / admin123")
    print(f"========================================================\n")
    app.run(host='0.0.0.0', port=port, debug=True)
