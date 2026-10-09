/**
 * TchooTchoo - One Page Dashboard Application Logic
 */

// Application Global State
const state = {
    searchData: null,
    currentCity: null,
    currentSort: 'duration', // 'duration' or 'culture'
    showPoisOnMap: true,
    map: null,
    mapLayers: {
        departureMarker: null,
        destinationMarker: null,
        routePolyline: null,
        poiMarkersGroup: null
    }
};

/* ========================================================
   Initialization
   ======================================================== */
document.addEventListener('DOMContentLoaded', () => {
    initLeafletMap();
    initDurationControls();
    initAutocomplete();
    initSearchForm();
    initSortingControls();
    initTabControls();
    initMapControls();

    // Auto-launch initial query to immediately display an active dashboard
    triggerInitialSearch();
});

/* ========================================================
   Leaflet Map Setup
   ======================================================== */
function initLeafletMap() {
    // Default center on France
    state.map = L.map('leaflet-map', {
        zoomControl: false,
        attributionControl: false
    }).setView([46.603354, 1.888334], 6);

    // Zoom control at bottom right
    L.control.zoom({ position: 'bottomright' }).addTo(state.map);

    // Modern clean CartoDB Voyager tile layer
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        subdomains: 'abcd'
    }).addTo(state.map);

    // Feature group for POI markers
    state.mapLayers.poiMarkersGroup = L.featureGroup().addTo(state.map);
}

/* ========================================================
   Duration Slider & Presets
   ======================================================== */
function initDurationControls() {
    const slider = document.getElementById('max_duration');
    const display = document.getElementById('duration-display');
    const presets = document.querySelectorAll('.preset-btn');

    function updateDuration(val) {
        slider.value = val;
        const hours = Math.floor(val / 60);
        const mins = val % 60;
        const formatted = mins > 0 ? `${hours}h${mins < 10 ? '0' : ''}${mins}` : `${hours}h00`;
        display.textContent = `${formatted} (${val} min)`;

        presets.forEach(btn => {
            if (parseInt(btn.dataset.min, 10) === parseInt(val, 10)) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    slider.addEventListener('input', (e) => {
        updateDuration(parseInt(e.target.value, 10));
    });

    presets.forEach(btn => {
        btn.addEventListener('click', () => {
            const min = parseInt(btn.dataset.min, 10);
            updateDuration(min);
        });
    });
}

/* ========================================================
   Autocomplete for Departure Station
   ======================================================== */
function initAutocomplete() {
    const input = document.getElementById('depart');
    const hidden = document.getElementById('id_depart');
    const list = document.getElementById('depart-list');
    let debounceTimer;

    input.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        const query = e.target.value.trim();
        hidden.value = '';

        if (query.length < 2) {
            list.classList.remove('active');
            return;
        }

        debounceTimer = setTimeout(async () => {
            try {
                const res = await fetch(`/api/autocomplete?q=${encodeURIComponent(query)}`);
                const items = await res.json();
                list.innerHTML = '';

                if (items && items.length > 0) {
                    items.forEach(item => {
                        const li = document.createElement('li');
                        li.textContent = item.name;
                        li.addEventListener('click', () => {
                            input.value = item.name;
                            hidden.value = item.id;
                            list.classList.remove('active');
                        });
                        list.appendChild(li);
                    });
                    list.classList.add('active');
                } else {
                    list.classList.remove('active');
                }
            } catch (err) {
                console.error("Erreur autocomplétion:", err);
            }
        }, 250);
    });

    document.addEventListener('click', (e) => {
        if (!input.contains(e.target) && !list.contains(e.target)) {
            list.classList.remove('active');
        }
    });
}

/* ========================================================
   Search Form & API Handling
   ======================================================== */
function initSearchForm() {
    const form = document.getElementById('search-form');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        performSearch();
    });
}

async function triggerInitialSearch() {
    performSearch();
}

async function performSearch() {
    const depart = document.getElementById('depart').value.trim();
    const id_depart = document.getElementById('id_depart').value;
    const max_duration = document.getElementById('max_duration').value;
    const spinner = document.getElementById('search-spinner');
    const statusLabel = document.getElementById('status-label');

    if (!depart) return;

    spinner.classList.remove('hidden');
    statusLabel.textContent = "Recherche des meilleures liaisons...";

    try {
        let url = `/api/search?max_duration=${max_duration}&depart=${encodeURIComponent(depart)}`;
        if (id_depart) url += `&id_depart=${encodeURIComponent(id_depart)}`;

        const response = await fetch(url);
        const data = await response.json();

        if (!response.ok) {
            alert(data.error || "Impossible de trouver des destinations sous cette durée.");
            statusLabel.textContent = "Aucun résultat";
            spinner.classList.add('hidden');
            return;
        }

        state.searchData = data;
        const total = data.journeys ? data.journeys.length : 0;
        statusLabel.textContent = `${total} destinations accessibles`;

        // Populate and select first city
        populateDestinationDropdown();

    } catch (err) {
        console.error("Erreur lors de la recherche:", err);
        statusLabel.textContent = "Erreur de connexion";
    } finally {
        spinner.classList.add('hidden');
    }
}

/* ========================================================
   Destination Selection & Sorting
   ======================================================== */
function initSortingControls() {
    const btnDuration = document.getElementById('sort-duration');
    const btnCulture = document.getElementById('sort-culture');

    btnDuration.addEventListener('click', () => {
        if (state.currentSort === 'duration') return;
        state.currentSort = 'duration';
        btnDuration.classList.add('active');
        btnCulture.classList.remove('active');
        populateDestinationDropdown(true);
    });

    btnCulture.addEventListener('click', () => {
        if (state.currentSort === 'culture') return;
        state.currentSort = 'culture';
        btnCulture.classList.add('active');
        btnDuration.classList.remove('active');
        populateDestinationDropdown(true);
    });

    const select = document.getElementById('destination-select');
    select.addEventListener('change', (e) => {
        const selectedCityName = e.target.value;
        if (!state.searchData || !state.searchData.journeys) return;
        const cityData = state.searchData.journeys.find(j => j['Ville'] === selectedCityName || j['Gare Destination'] === selectedCityName);
        if (cityData) {
            selectDestination(cityData);
        }
    });
}

function populateDestinationDropdown(keepSelected = false) {
    if (!state.searchData || !state.searchData.journeys) return;

    const select = document.getElementById('destination-select');
    let journeys = [...state.searchData.journeys];

    // Apply Sorting
    if (state.currentSort === 'duration') {
        journeys.sort((a, b) => (a['Durée (min)'] || 0) - (b['Durée (min)'] || 0));
    } else {
        journeys.sort((a, b) => (b['Points Culturels'] || 0) - (a['Points Culturels'] || 0));
    }

    const currentCityName = state.currentCity ? state.currentCity['Ville'] : null;

    select.innerHTML = '';
    journeys.forEach(j => {
        const option = document.createElement('option');
        option.value = j['Ville'];
        
        const hrs = Math.floor(j['Durée (min)'] / 60);
        const mins = j['Durée (min)'] % 60;
        const durationStr = `${hrs}h${mins < 10 ? '0' : ''}${mins}`;
        const cultureStr = `${j['Points Culturels']} lieux`;
        
        option.textContent = `${j['Ville']} (${durationStr} • ${cultureStr})`;
        select.appendChild(option);
    });

    if (keepSelected && currentCityName) {
        select.value = currentCityName;
    } else if (journeys.length > 0) {
        select.value = journeys[0]['Ville'];
        selectDestination(journeys[0]);
    }
}

/* ========================================================
   Render Dashboard Components for Selected City
   ======================================================== */
function selectDestination(j) {
    state.currentCity = j;

    // 1. Update Card 4 Header (Active city banner & badges)
    updateDestinationHeader(j);

    // 2. Update Card 2 (Ecology KPI)
    updateEcologyCard(j);

    // 3. Update Card 3 (Carbon Comparison Chart)
    updateCarbonComparisonChart(j);

    // 4. Update Card 5 (POIs and Schedules lists)
    updatePoisList(j);
    updateSchedulesList(j);

    // 5. Update Card 6 (Interactive Leaflet Map)
    updateMapDisplay(j);
}

function updateDestinationHeader(j) {
    document.getElementById('city-title').textContent = j['Ville'] || j['Gare Destination'];
    document.getElementById('station-title').textContent = j['Gare Destination'];

    const hrs = Math.floor(j['Durée (min)'] / 60);
    const mins = j['Durée (min)'] % 60;
    const durationStr = `${hrs}h${mins < 10 ? '0' : ''}${mins}`;

    document.getElementById('badge-duration').textContent = `⏱️ ${durationStr}`;
    document.getElementById('badge-culture').textContent = `🏛️ ${j['Points Culturels'] || 0} lieux culturels`;
    
    const cycleCount = j['Aménagements Cyclables'] || 0;
    document.getElementById('badge-cycle').textContent = cycleCount > 0 
        ? `🚲 ${cycleCount} aménagements vélo` 
        : `🚲 Mobilité douce`;

    const dist = j['distance_km'] ? `${j['distance_km']} km` : 'Train direct / TER';
    document.getElementById('badge-dist').textContent = `📏 ${dist}`;
}

function updateEcologyCard(j) {
    const comp = j['co2_comparison'] || {};
    const savedPct = comp.saved_pct !== undefined ? comp.saved_pct : 92;
    const savedKg = comp.saved_kg !== undefined ? comp.saved_kg : 35.0;
    const trees = comp.trees_equiv !== undefined ? comp.trees_equiv : 1.4;
    const trainKg = comp.train_kg !== undefined ? comp.train_kg : ((j['CO2 (g)'] || 800) / 1000).toFixed(1);

    document.getElementById('eco-saved-pct').textContent = `-${savedPct}%`;
    document.getElementById('eco-saved-kg').textContent = `${savedKg} kg`;
    document.getElementById('eco-trees').textContent = `${trees} 🌳`;
    document.getElementById('eco-train-co2').textContent = `${trainKg} kg`;

    const badge = document.getElementById('eco-score-badge');
    if (savedPct >= 90) {
        badge.textContent = "Éco A+";
        badge.style.background = "rgba(16, 185, 129, 0.2)";
        badge.style.color = "#34d399";
    } else {
        badge.textContent = "Éco A";
        badge.style.background = "rgba(0, 136, 206, 0.2)";
        badge.style.color = "#38bdf8";
    }
}

function updateCarbonComparisonChart(j) {
    const container = document.getElementById('co2-bars-list');
    container.innerHTML = '';

    const comp = j['co2_comparison'] || {};
    let modes = comp.modes;

    if (!modes || modes.length === 0) {
        const trainKg = ((j['CO2 (g)'] || 800) / 1000);
        modes = [
            { mode: "🚆 Train", co2_kg: trainKg, color: "#0088ce" },
            { mode: "⚡ Voiture élec.", co2_kg: +(trainKg * 3.5).toFixed(1), color: "#10b981" },
            { mode: "👥 Covoiturage", co2_kg: +(trainKg * 5.2).toFixed(1), color: "#f59e0b" },
            { mode: "🚘 Voiture thermique", co2_kg: +(trainKg * 14.5).toFixed(1), color: "#ef4444" },
            { mode: "✈️ Avion", co2_kg: +(trainKg * 18.0).toFixed(1), color: "#8b5cf6" }
        ];
    }

    const maxVal = Math.max(...modes.map(m => m.co2_kg), 1);

    modes.forEach(item => {
        const pct = Math.max(4, Math.round((item.co2_kg / maxVal) * 100));

        const row = document.createElement('div');
        row.className = 'co2-bar-row';
        row.innerHTML = `
            <div class="bar-meta">
                <span class="bar-mode-name">${item.mode}</span>
                <span class="bar-val">${item.co2_kg} kg CO₂</span>
            </div>
            <div class="bar-track">
                <div class="bar-fill" style="width: ${pct}%; background-color: ${item.color};"></div>
            </div>
        `;
        container.appendChild(row);
    });
}

function updatePoisList(j) {
    const list = document.getElementById('pois-list');
    list.innerHTML = '';

    const pois = j['pois'] || [];
    document.getElementById('pois-count').textContent = pois.length;

    if (pois.length === 0) {
        list.innerHTML = `<p style="color: var(--text-muted); font-size: 0.85rem; text-align: center; padding: 2rem 0;">Aucun lieu culturel répertorié directement dans la base pour cette commune.</p>`;
        return;
    }

    pois.forEach((poi, index) => {
        const card = document.createElement('div');
        card.className = 'poi-card';
        card.innerHTML = `
            <div class="poi-info">
                <span class="poi-domain-badge">${poi.domaine || 'Patrimoine'}</span>
                <div class="poi-name">${poi.nom}</div>
                ${poi.adresse ? `<div class="poi-address">📍 ${poi.adresse}</div>` : ''}
            </div>
            <button type="button" class="poi-btn-locate" data-index="${index}">
                Voir 📍
            </button>
        `;

        card.addEventListener('click', () => {
            zoomToPoi(poi);
        });

        const btnLocate = card.querySelector('.poi-btn-locate');
        btnLocate.addEventListener('click', (e) => {
            e.stopPropagation();
            zoomToPoi(poi);
        });

        list.appendChild(card);
    });
}

function updateSchedulesList(j) {
    const list = document.getElementById('schedules-list');
    list.innerHTML = '';

    const trajets = j['Trajets'] || [];
    document.getElementById('schedules-count').textContent = trajets.length;

    if (trajets.length === 0) {
        list.innerHTML = `<p style="color: var(--text-muted); font-size: 0.85rem; text-align: center; padding: 2rem 0;">Aucun détail horaire disponible pour ce filtre.</p>`;
        return;
    }

    trajets.forEach(t => {
        const card = document.createElement('div');
        card.className = 'schedule-card';
        card.innerHTML = `
            <div>
                <div class="schedule-times">
                    <span>${t['Départ']}</span>
                    <span class="schedule-arrow">➔</span>
                    <span>${t['Arrivée']}</span>
                </div>
                <div class="schedule-details">
                    Durée : ${t['Durée (min)']} min • CO₂ : ${t['CO2 (g)']} g
                </div>
            </div>
            <a href="https://www.sncf-connect.com" target="_blank" rel="noopener" class="schedule-book-btn">
                SNCF Connect ↗
            </a>
        `;
        list.appendChild(card);
    });
}

/* ========================================================
   Leaflet Map Interactions & Layers
   ======================================================== */
function updateMapDisplay(j) {
    if (!state.map) return;

    // Remove existing markers & lines
    if (state.mapLayers.departureMarker) state.map.removeLayer(state.mapLayers.departureMarker);
    if (state.mapLayers.destinationMarker) state.map.removeLayer(state.mapLayers.destinationMarker);
    if (state.mapLayers.routePolyline) state.map.removeLayer(state.mapLayers.routePolyline);
    state.mapLayers.poiMarkersGroup.clearLayers();

    const info = state.searchData ? state.searchData.info : {};
    const depCoords = info.dep_coords;
    const destCoords = j.coords;

    const bounds = [];

    // Departure Marker
    if (depCoords && depCoords.length === 2 && !isNaN(depCoords[0]) && !isNaN(depCoords[1])) {
        const depIcon = L.divIcon({
            className: 'custom-station-pin',
            html: '🚆',
            iconSize: [32, 32],
            iconAnchor: [16, 16]
        });

        state.mapLayers.departureMarker = L.marker(depCoords, { icon: depIcon })
            .addTo(state.map)
            .bindPopup(`
                <div class="map-popup-card">
                    <span class="popup-tag">Gare de Départ</span>
                    <h4>${info.depart || 'Départ'}</h4>
                </div>
            `);
        bounds.push(depCoords);
    }

    // Destination Marker
    if (destCoords && destCoords.length === 2 && !isNaN(destCoords[0]) && !isNaN(destCoords[1])) {
        const destIcon = L.divIcon({
            className: 'custom-station-pin',
            html: '🎯',
            iconSize: [36, 36],
            iconAnchor: [18, 18]
        });

        state.mapLayers.destinationMarker = L.marker(destCoords, { icon: destIcon })
            .addTo(state.map)
            .bindPopup(`
                <div class="map-popup-card">
                    <span class="popup-tag">Destination</span>
                    <h4>${j['Gare Destination']}</h4>
                    <p>Trajet : ${j['Durée (min)']} min • ${j['Points Culturels']} lieux culturels</p>
                </div>
            `);
        bounds.push(destCoords);
    }

    // Route Polyline
    if (depCoords && destCoords) {
        state.mapLayers.routePolyline = L.polyline([depCoords, destCoords], {
            color: '#0088ce',
            weight: 4,
            opacity: 0.85,
            dashArray: '8, 8'
        }).addTo(state.map);

        document.getElementById('map-route-text').textContent = 
            `Trajet : ${info.depart || 'Départ'} ➔ ${j['Ville']} (${j['Durée (min)']} min)`;
    }

    // Cultural POIs Markers
    const pois = j['pois'] || [];
    pois.forEach(poi => {
        if (poi.lat && poi.lon && !isNaN(poi.lat) && !isNaN(poi.lon)) {
            const poiIcon = L.divIcon({
                className: 'custom-poi-pin',
                html: '🏛️',
                iconSize: [26, 26],
                iconAnchor: [13, 13]
            });

            const marker = L.marker([poi.lat, poi.lon], { icon: poiIcon })
                .bindPopup(`
                    <div class="map-popup-card">
                        <span class="popup-tag">${poi.domaine || 'Lieu culturel'}</span>
                        <h4>${poi.nom}</h4>
                        ${poi.adresse ? `<p>📍 ${poi.adresse}</p>` : ''}
                    </div>
                `);

            poi.marker = marker;
            state.mapLayers.poiMarkersGroup.addLayer(marker);
            bounds.push([poi.lat, poi.lon]);
        }
    });

    // Fit map bounds
    if (bounds.length > 0) {
        state.map.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 });
    }
}

function zoomToPoi(poi) {
    if (!state.map || !poi.lat || !poi.lon) return;

    state.map.flyTo([poi.lat, poi.lon], 16, {
        animate: true,
        duration: 1.2
    });

    if (poi.marker) {
        setTimeout(() => {
            poi.marker.openPopup();
        }, 1200);
    }
}

/* ========================================================
   Tabs and Map Controls
   ======================================================== */
function initTabControls() {
    const tabPois = document.getElementById('tab-pois');
    const tabSchedules = document.getElementById('tab-schedules');
    const panelPois = document.getElementById('panel-pois');
    const panelSchedules = document.getElementById('panel-schedules');

    tabPois.addEventListener('click', () => {
        tabPois.classList.add('active');
        tabSchedules.classList.remove('active');
        panelPois.classList.remove('hidden');
        panelSchedules.classList.add('hidden');
    });

    tabSchedules.addEventListener('click', () => {
        tabSchedules.classList.add('active');
        tabPois.classList.remove('active');
        panelSchedules.classList.remove('hidden');
        panelPois.classList.add('hidden');
    });
}

function initMapControls() {
    // Re-fit Map Button
    document.getElementById('btn-fit-map').addEventListener('click', () => {
        if (!state.currentCity) return;
        updateMapDisplay(state.currentCity);
    });

    // Toggle POIs Button
    const btnTogglePois = document.getElementById('btn-toggle-pois');
    btnTogglePois.addEventListener('click', () => {
        if (!state.map || !state.mapLayers.poiMarkersGroup) return;

        state.showPoisOnMap = !state.showPoisOnMap;
        if (state.showPoisOnMap) {
            state.map.addLayer(state.mapLayers.poiMarkersGroup);
            btnTogglePois.textContent = "🏛️ Masquer POIs";
        } else {
            state.map.removeLayer(state.mapLayers.poiMarkersGroup);
            btnTogglePois.textContent = "🏛️ Afficher POIs";
        }
    });
}
