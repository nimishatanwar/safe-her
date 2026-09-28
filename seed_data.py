"""
SafeHer Seed Data Script
Initializes sample users, emergency contacts, safe havens, and sample alerts.
Run: python seed_data.py
"""

from database import db
from models import User, EmergencyContact, EmergencyAlert, AlertNotificationLog, SafeLocation

def seed():
    print("Seeding SafeHer database...")

    # 1. Seed Users if not present
    admin = User.find_by_email('admin@safeher.com')
    if not admin:
        admin = User.create(
            name="SafeHer Central Admin",
            email="admin@safeher.com",
            phone="+91 9876543210",
            password="admin123",
            blood_group="B+",
            address="SafeHer Emergency Response Center, Headquarters",
            medical_notes="Lead Dispatcher & System Admin",
            role="admin"
        )
        print("-> Created Admin: admin@safeher.com / admin123")
    else:
        print("-> Admin already exists.")

    priya = User.find_by_email('priya@safeher.com')
    if not priya:
        priya = User.create(
            name="Priya Sharma",
            email="priya@safeher.com",
            phone="+91 9811223344",
            password="user123",
            blood_group="O+",
            address="Flat 402, Lotus Greens, Sector 62, Noida",
            medical_notes="Mild asthma, carries inhaler. Emergency contact is father.",
            role="user"
        )
        print("-> Created Demo User: priya@safeher.com / user123")
    else:
        print("-> Demo user already exists.")

    # 2. Seed Emergency Contacts for Priya
    contacts = priya.get_contacts()
    if not contacts:
        EmergencyContact.create(
            user_id=priya.id,
            name="Rajesh Sharma (Father)",
            phone="+91 9876500001",
            email="rajesh.sharma@example.com",
            relationship="Father",
            is_primary=True
        )
        EmergencyContact.create(
            user_id=priya.id,
            name="Ananya Sharma (Sister)",
            phone="+91 9876500002",
            email="ananya.s@example.com",
            relationship="Sister",
            is_primary=False
        )
        EmergencyContact.create(
            user_id=priya.id,
            name="Neha Verma (Best Friend)",
            phone="+91 9876500003",
            email="neha.verma@example.com",
            relationship="Friend",
            is_primary=False
        )
        print("-> Added 3 trusted emergency contacts for Priya.")

    # 3. Seed Designated Safe Locations
    existing_locations = SafeLocation.all()
    if not existing_locations:
        safe_places = [
            {
                "name": "Connaught Place Central Police Station",
                "category": "police",
                "latitude": 28.6315,
                "longitude": 77.2167,
                "address": "B-Block, Inner Circle, Connaught Place, New Delhi",
                "contact_number": "011-23743322",
                "is_24x7": True,
                "description": "24/7 Police Patrol & Women Help Desk Unit"
            },
            {
                "name": "AIIMS Emergency & Trauma Center",
                "category": "hospital",
                "latitude": 28.5672,
                "longitude": 77.2100,
                "address": "Sri Aurobindo Marg, Ansari Nagar, New Delhi",
                "contact_number": "011-26588500",
                "is_24x7": True,
                "description": "Level-1 Trauma & Emergency Critical Care Center"
            },
            {
                "name": "Apollo 24/7 Pharmacy & Urgent Care",
                "category": "pharmacy",
                "latitude": 28.6250,
                "longitude": 77.2210,
                "address": "Barakhamba Road, Near Metro Gate 4, New Delhi",
                "contact_number": "1860-500-0101",
                "is_24x7": True,
                "description": "Round-the-clock open pharmacy, CCTV monitored and safe"
            },
            {
                "name": "Delhi Commission for Women - Pink Booth #12",
                "category": "safe_haven",
                "latitude": 28.6180,
                "longitude": 77.2110,
                "address": "Janpath Road, Near Tourist Information Bureau, New Delhi",
                "contact_number": "181",
                "is_24x7": True,
                "description": "Dedicated Women Safety Pink Booth staffed by female officers"
            },
            {
                "name": "Rajiv Chowk Metro Station - Security Post",
                "category": "metro",
                "latitude": 28.6328,
                "longitude": 77.2195,
                "address": "Concourse Level, Gate No. 2, Rajiv Chowk Metro",
                "contact_number": "011-23417910",
                "is_24x7": True,
                "description": "CISF Guard Post, High Security Transit Zone"
            },
            {
                "name": "Safdarjung Hospital Emergency Care Unit",
                "category": "hospital",
                "latitude": 28.5700,
                "longitude": 77.2065,
                "address": "Ring Road, Opposite AIIMS, New Delhi",
                "contact_number": "011-26165060",
                "is_24x7": True,
                "description": "Government multi-specialty emergency wing"
            },
            {
                "name": "Parliament Street Police Station",
                "category": "police",
                "latitude": 28.6245,
                "longitude": 77.2135,
                "address": "Parliament Street, Near Patel Chowk, New Delhi",
                "contact_number": "011-23744444",
                "is_24x7": True,
                "description": "Rapid Response Police Outpost"
            },
            {
                "name": "MedPlus 24-Hour Emergency Pharmacy",
                "category": "pharmacy",
                "latitude": 28.6380,
                "longitude": 77.2280,
                "address": "Paharganj Main Market, New Delhi",
                "contact_number": "011-45678901",
                "is_24x7": True,
                "description": "24 Hour chemist with well-lit public storefront"
            }
        ]

        for sp in safe_places:
            SafeLocation.create(**sp)
        print(f"-> Seeded {len(safe_places)} designated safe locations.")

    # 4. Seed sample alert for history visualization
    sample_alerts = EmergencyAlert.get_all_recent(limit=5)
    if not sample_alerts:
        alert1 = EmergencyAlert.create(
            user_id=priya.id,
            alert_type="Being Followed / Stalked",
            latitude=28.6280,
            longitude=27.2150,
            accuracy=12.5,
            location_address="Near Janpath Metro Station, New Delhi",
            notes="Suspicious individual following on dark pathway"
        )
        # Mark as resolved
        EmergencyAlert.update_status(
            alert_id=alert1.id,
            status="RESOLVED",
            notes="Police PCR van #12 arrived on scene within 4 mins. Subject escorted safely home.",
            responded_by="Dispatcher Officer Verma (Badge #4092)"
        )

        # Notification logs
        AlertNotificationLog.create(
            alert_id=alert1.id,
            recipient_name="Rajesh Sharma (Father)",
            recipient_phone="+91 9876500001",
            recipient_email="rajesh.sharma@example.com",
            channel="SMS",
            message_body="EMERGENCY ALERT: Priya has activated SOS near Janpath Metro Station. Coordinates: 28.6280, 27.2150",
            delivery_status="DELIVERED"
        )
        AlertNotificationLog.create(
            alert_id=alert1.id,
            recipient_name="Ananya Sharma (Sister)",
            recipient_phone="+91 9876500002",
            recipient_email="ananya.s@example.com",
            channel="WHATSAPP",
            message_body="EMERGENCY ALERT: Priya activated SOS near Janpath Metro Station. Live Google Map: https://maps.google.com/?q=28.6280,27.2150",
            delivery_status="DELIVERED"
        )
        print("-> Seeded historical resolved emergency incident.")

    print("\n[SUCCESS] SafeHer Database Seeding Completed!")
    print("Login Credentials:")
    print("  * Admin: admin@safeher.com / admin123")
    print("  * Demo User: priya@safeher.com / user123\n")

if __name__ == '__main__':
    seed()
