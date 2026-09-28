/**
 * SafeHer Interactive Safe Havens & GPS Map Controller
 * Powered by OpenStreetMap and Leaflet.js
 */

let mapInstance = null;
let userMarker = null;
let userRadiusCircle = null;
let safeLocationMarkers = [];
let allSafeLocations = [];

const categoryIcons = {
    police: { icon: 'fa-shield-halved', color: '#3b82f6', label: 'Police Station' },
    hospital: { icon: 'fa-hospital', color: '#ef4444', label: 'Hospital / Emergency' },
    pharmacy: { icon: 'fa-prescription-bottle-medical', color: '#10b981', label: '24/7 Pharmacy' },
    metro: { icon: 'fa-train-subway', color: '#8b5cf6', label: 'Safe Metro Station' },
    safe_haven: { icon: 'fa-heart-pulse', color: '#ec4899', label: 'Women Help Center' }
};

/**
 * Initialize Fullscreen or standard Map
 */
function initSafeMap(containerId = 'safeMap', interactive = true) {
    const mapEl = document.getElementById(containerId);
    if (!mapEl) return;

    // Default center (New Delhi / India coordinates default, then auto-pan to user's real GPS)
    const defaultCenter = [28.6139, 77.2090];
    const defaultZoom = interactive ? 13 : 12;

    mapInstance = L.map(containerId, {
        center: defaultCenter,
        zoom: defaultZoom,
        zoomControl: interactive,
        attributionControl: true
    });

    // High quality OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | SafeHer'
    }).addTo(mapInstance);

    // Locate user and populate
    locateAndCenterUser(interactive);
    loadSafeLocations();
}

/**
 * Locate user via Geolocation and center map
 */
function locateAndCenterUser(panToUser = true) {
    if (!navigator.geolocation) return;

    navigator.geolocation.getCurrentPosition(
        (pos) => {
            const lat = pos.coords.latitude;
            const lng = pos.coords.longitude;
            const accuracy = pos.coords.accuracy || 20;

            updateUserMarker(lat, lng, accuracy);

            if (panToUser && mapInstance) {
                mapInstance.setView([lat, lng], 14);
            }

            // Recalculate distance to safe locations if loaded
            renderSafePlacesList(lat, lng);
        },
        (err) => {
            console.warn('Geolocation failed in map view:', err.message);
            // Default center fallback
            updateUserMarker(28.6139, 77.2090, 100);
            renderSafePlacesList(28.6139, 77.2090);
        },
        { enableHighAccuracy: true, timeout: 10000 }
    );
}

/**
 * Update or create pulsing User Marker
 */
function updateUserMarker(lat, lng, accuracy) {
    if (!mapInstance) return;

    const userHtml = `
        <div style="position: relative; width: 24px; height: 24px;">
            <div style="position: absolute; width: 24px; height: 24px; border-radius: 50%; background: #3b82f6; border: 3px solid white; box-shadow: 0 0 10px rgba(59,130,246,0.9);"></div>
            <div style="position: absolute; width: 44px; height: 44px; top: -10px; left: -10px; border-radius: 50%; background: rgba(59,130,246,0.3); animation: sosPulse 2s infinite;"></div>
        </div>
    `;

    const userIcon = L.divIcon({
        className: 'custom-user-marker',
        html: userHtml,
        iconSize: [24, 24],
        iconAnchor: [12, 12]
    });

    if (userMarker) {
        userMarker.setLatLng([lat, lng]);
    } else {
        userMarker = L.marker([lat, lng], { icon: userIcon }).addTo(mapInstance);
        userMarker.bindPopup(`
            <div style="color: #111;">
                <strong><i class="fa-solid fa-person-circle-check text-primary"></i> Your Current Location</strong><br>
                <small class="text-muted">Lat: ${lat.toFixed(5)}, Lng: ${lng.toFixed(5)}</small>
            </div>
        `);
    }

    if (userRadiusCircle) {
        userRadiusCircle.setLatLng([lat, lng]);
        userRadiusCircle.setRadius(accuracy);
    } else {
        userRadiusCircle = L.circle([lat, lng], {
            radius: accuracy,
            color: '#3b82f6',
            fillColor: '#60a5fa',
            fillOpacity: 0.15,
            weight: 1
        }).addTo(mapInstance);
    }
}

/**
 * Fetch and display designated safe locations
 */
async function loadSafeLocations() {
    try {
        const res = await fetch('/api/safe-locations');
        const data = await res.json();
        allSafeLocations = data.locations || [];
        displayMarkers(allSafeLocations);
    } catch (e) {
        console.error('Failed to load safe locations:', e);
    }
}

/**
 * Render Leaflet Markers for Safe Locations
 */
function displayMarkers(locations) {
    if (!mapInstance) return;

    // Clear existing
    safeLocationMarkers.forEach(m => mapInstance.removeLayer(m));
    safeLocationMarkers = [];

    locations.forEach(loc => {
        const catInfo = categoryIcons[loc.category] || categoryIcons.safe_haven;

        const customMarkerHtml = `
            <div style="
                width: 34px; height: 34px;
                border-radius: 50%;
                background: ${catInfo.color};
                border: 2px solid #ffffff;
                color: #ffffff;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 15px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.4);
                cursor: pointer;">
                <i class="fa-solid ${catInfo.icon}"></i>
            </div>
        `;

        const icon = L.divIcon({
            html: customMarkerHtml,
            className: 'safe-haven-marker',
            iconSize: [34, 34],
            iconAnchor: [17, 17],
            popupAnchor: [0, -20]
        });

        const gmapsDirectionUrl = `https://www.google.com/maps/dir/?api=1&destination=${loc.latitude},${loc.longitude}`;

        const popupContent = `
            <div style="color: #0f172a; min-width: 220px; font-family: 'Plus Jakarta Sans', sans-serif;">
                <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                    <span style="color: ${catInfo.color}; font-size: 1.1rem;"><i class="fa-solid ${catInfo.icon}"></i></span>
                    <strong style="font-size: 0.95rem;">${loc.name}</strong>
                </div>
                <div style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: ${catInfo.color}; font-weight: 700; margin-bottom: 6px;">
                    ${catInfo.label} ${loc.is_24x7 ? '• 24x7 Open' : ''}
                </div>
                <p style="font-size: 0.8rem; margin: 0 0 8px 0; color: #475569;">
                    <i class="fa-solid fa-location-dot text-danger"></i> ${loc.address}
                </p>
                <div style="display: flex; gap: 6px; margin-top: 6px;">
                    <a href="tel:${loc.contact_number}" style="
                        flex: 1; text-align: center; background: #0f172a; color: white;
                        padding: 5px 8px; border-radius: 6px; font-size: 0.78rem; text-decoration: none; font-weight: 600;">
                        <i class="fa-solid fa-phone"></i> Call
                    </a>
                    <a href="${gmapsDirectionUrl}" target="_blank" style="
                        flex: 1; text-align: center; background: #2563eb; color: white;
                        padding: 5px 8px; border-radius: 6px; font-size: 0.78rem; text-decoration: none; font-weight: 600;">
                        <i class="fa-solid fa-diamond-turn-right"></i> Directions
                    </a>
                </div>
            </div>
        `;

        const marker = L.marker([loc.latitude, loc.longitude], { icon: icon }).addTo(mapInstance);
        marker.bindPopup(popupContent);
        safeLocationMarkers.push(marker);
    });
}

/**
 * Filter safe places by category
 */
function filterCategory(category) {
    // Update active button state
    document.querySelectorAll('.btn-filter').forEach(btn => {
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-outline-secondary');
    });
    const activeBtn = document.getElementById(`filter-${category}`);
    if (activeBtn) {
        activeBtn.classList.remove('btn-outline-secondary');
        activeBtn.classList.add('btn-primary');
    }

    if (category === 'all') {
        displayMarkers(allSafeLocations);
    } else {
        const filtered = allSafeLocations.filter(loc => loc.category === category);
        displayMarkers(filtered);
    }
}

/**
 * Calculate distance between two coordinates in Kilometers (Haversine Formula)
 */
function calculateDistanceKm(lat1, lon1, lat2, lon2) {
    const R = 6371; // Earth radius in km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a =
        Math.sin(dLat/2) * Math.sin(dLat/2) +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
        Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

/**
 * Render cards list of safe places ordered by distance from user
 */
function renderSafePlacesList(userLat, userLng) {
    const listContainer = document.getElementById('safePlacesList');
    if (!listContainer) return;

    if (!allSafeLocations || allSafeLocations.length === 0) {
        listContainer.innerHTML = '<div class="text-white-50 p-3 text-center">Loading safe locations...</div>';
        return;
    }

    // Clone and calculate distance
    const sorted = allSafeLocations.map(loc => {
        const dist = calculateDistanceKm(userLat, userLng, loc.latitude, loc.longitude);
        return { ...loc, distanceKm: dist };
    }).sort((a, b) => a.distanceKm - b.distanceKm);

    let html = '';
    sorted.slice(0, 10).forEach(loc => {
        const catInfo = categoryIcons[loc.category] || categoryIcons.safe_haven;
        const gmapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${loc.latitude},${loc.longitude}`;

        html += `
            <div class="card bg-secondary bg-opacity-25 border-secondary mb-2 p-2 rounded-3 hover-shadow">
                <div class="d-flex align-items-center justify-content-between">
                    <div class="d-flex align-items-center gap-2">
                        <span class="badge" style="background-color: ${catInfo.color}; font-size: 0.9rem;">
                            <i class="fa-solid ${catInfo.icon}"></i>
                        </span>
                        <div>
                            <div class="fw-bold text-white small">${loc.name}</div>
                            <div class="text-white-50" style="font-size: 0.75rem;">${loc.address.substring(0, 45)}...</div>
                        </div>
                    </div>
                    <div class="text-end">
                        <span class="badge bg-dark text-info font-monospace">${loc.distanceKm.toFixed(1)} km</span>
                        <div class="mt-1 d-flex gap-1 justify-content-end">
                            <a href="tel:${loc.contact_number}" class="btn btn-sm btn-outline-light py-0 px-1" title="Call"><i class="fa-solid fa-phone"></i></a>
                            <a href="${gmapsUrl}" target="_blank" class="btn btn-sm btn-outline-primary py-0 px-1" title="Directions"><i class="fa-solid fa-diamond-turn-right"></i></a>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    listContainer.innerHTML = html;
}
