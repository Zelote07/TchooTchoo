/**
 * TchooTchoo - New Dashboard Layout Logic
 */

const state = {
    searchData: null,
    currentCity: null,
    map: null,
    mapLayers: {
        departureMarker: null,
        destinations: []
    },
    charts: {
        radar: null,
        eco: null
    }
};

document.addEventListener('DOMContentLoaded', () => {
    initLeafletMap();
    initDurationControls();
    initAutocomplete();
    initSearchForm();
    
    // Initialize empty charts
    initCharts();

    triggerInitialSearch();
});

/* ========================================================
   Map Initialization
   ======================================================== */
function initLeafletMap() {
    state.map = L.map('leaflet-map', {
        zoomControl: false,
        attributionControl: false
    }).setView([46.603354, 1.888334], 5);

    L.control.zoom({ position: 'bottomright' }).addTo(state.map);

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19
    }).addTo(state.map);
}

/* ========================================================
   Search & Duration Controls
   ======================================================== */
function initDurationControls() {
    const slider = document.getElementById('max_duration');
    const display = document.getElementById('duration-display');

    slider.addEventListener('input', (e) => {
        const val = parseInt(e.target.value, 10);
        const hours = Math.floor(val / 60);
        const mins = val % 60;
        const formatted = mins > 0 ? `${hours}h${mins < 10 ? '0' : ''}${mins}` : `${hours}h00`;
        display.textContent = `${formatted} (${val} min)`;
    });
}

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

function initSearchForm() {
    const form = document.getElementById('search-form');
    form.addEventListener('submit', (e) => {
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
    
    if (!depart) return;
    spinner.classList.remove('hidden');

    try {
        let url = `/api/search?max_duration=${max_duration}&depart=${encodeURIComponent(depart)}`;
        if (id_depart) url += `&id_depart=${encodeURIComponent(id_depart)}`;

        const response = await fetch(url);
        const data = await response.json();

        if (!response.ok) {
            alert(data.error || "Impossible de trouver des destinations sous cette durée.");
            spinner.classList.add('hidden');
            return;
        }

        state.searchData = data;
        displayAllDestinationsOnMap();
        
    } catch (err) {
        console.error("Erreur de recherche:", err);
    } finally {
        spinner.classList.add('hidden');
    }
}

function displayAllDestinationsOnMap() {
    if (!state.searchData || !state.searchData.journeys) return;
    
    // Clear previous markers
    if (state.mapLayers.departureMarker) state.map.removeLayer(state.mapLayers.departureMarker);
    state.mapLayers.destinations.forEach(item => {
        state.map.removeLayer(item.marker);
        if (item.polyline) state.map.removeLayer(item.polyline);
    });
    state.mapLayers.destinations = [];

    const info = state.searchData.info;
    const depCoords = info.dep_coords;
    const bounds = [];

    if (depCoords && !isNaN(depCoords[0])) {
        const depSvg = `<svg viewBox="0 0 24 24" fill="#ef4444" stroke="#fff" stroke-width="2" width="36" height="36"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>`;
        const depIcon = L.divIcon({
            html: depSvg,
            className: 'departure-icon',
            iconSize: [36, 36],
            iconAnchor: [18, 36],
            tooltipAnchor: [0, -36]
        });
        state.mapLayers.departureMarker = L.marker(depCoords, {icon: depIcon, zIndexOffset: 2000}).addTo(state.map).bindTooltip('<b>Gare de Départ</b><br>' + (info.depart || ''), {direction: 'top'});
        bounds.push(depCoords);
    }
    
    const journeys = state.searchData.journeys;
    document.getElementById('map-route-text').textContent = `${journeys.length} destinations trouvées. Cliquez sur une gare pour voir son tracé et ses trains.`;
    
    journeys.forEach(j => {
        const destCoords = j.coords;
        if (!destCoords || isNaN(destCoords[0])) return;

        // Custom destination icon
        const destSvg = `<svg viewBox="0 0 24 24" fill="#0088ce" stroke="#ffffff" stroke-width="2" width="26" height="26"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="3" fill="#ffffff"/></svg>`;
        const destIcon = L.divIcon({
            html: destSvg,
            className: 'destination-marker-icon',
            iconSize: [26, 26],
            iconAnchor: [13, 13],
            tooltipAnchor: [0, -13],
            popupAnchor: [0, -13]
        });

        const marker = L.marker(destCoords, { icon: destIcon }).addTo(state.map);
        marker.bindTooltip(`<b>${escapeHtml(j['Ville'])}</b><br>${j['Durée (min)']} min`);
        
        // Tracé géographique réel issu de l'API SNCF ou ligne directe de repli
        const hasGeojson = j.geojson_coords && Array.isArray(j.geojson_coords) && j.geojson_coords.length > 1;
        const trackPoints = hasGeojson ? j.geojson_coords : (depCoords ? [depCoords, destCoords] : null);

        let polyline = null;
        if (trackPoints) {
            polyline = L.polyline(trackPoints, { 
                color: '#64748b', 
                weight: 2.5, 
                opacity: 0.4,
                lineCap: 'round',
                lineJoin: 'round'
            }).addTo(state.map);
        }

        const onSelect = () => { selectDestination(j); };
        marker.on('click', onSelect);
        if (polyline) polyline.on('click', onSelect);

        state.mapLayers.destinations.push({ j, marker, polyline });
        bounds.push(destCoords);
    });

    if (bounds.length > 0) {
        state.map.fitBounds(bounds, { padding: [30, 30], maxZoom: 12 });
    }

    if (journeys.length > 0) {
        selectDestination(journeys[0]);
    }
}

/* ========================================================
   Helpers pour l'affichage des trains
   ======================================================== */
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function getTrainBadgeClass(mode) {
    const m = (mode || '').toUpperCase();
    if (m.includes('TGV') || m.includes('INOUI')) return 'mode-tgv';
    if (m.includes('OUIGO')) return 'mode-ouigo';
    if (m.includes('TER') || m.includes('MOBIGO') || m.includes('NOMAD') || m.includes('ALEO') || m.includes('REMI')) return 'mode-ter';
    if (m.includes('INTERCIT') || m.includes('IC')) return 'mode-intercites';
    return 'mode-train';
}

function getTrainIcon(mode) {
    const m = (mode || '').toUpperCase();
    if (m.includes('TGV') || m.includes('INOUI')) return '🚄';
    if (m.includes('OUIGO')) return '⚡';
    if (m.includes('INTERCIT') || m.includes('IC')) return '🚅';
    return '🚆';
}

function buildTrainPopupHtml(j) {
    const trains = j.trains || [];
    let trainBadges = '';
    
    if (trains.length > 0) {
        trainBadges = trains.map(t => {
            const badgeClass = getTrainBadgeClass(t.mode);
            const icon = getTrainIcon(t.mode);
            return `
                <div class="popup-train-item">
                    <span class="popup-train-mode ${badgeClass}">${icon} ${escapeHtml(t.mode || 'Train')}</span>
                    ${t.numero ? `<span class="popup-train-num">N° ${escapeHtml(t.numero)}</span>` : ''}
                    ${t.direction ? `<div class="popup-train-dir">➔ Direction ${escapeHtml(t.direction)}</div>` : ''}
                </div>
            `;
        }).join('');
    } else {
        trainBadges = `
            <div class="popup-train-item">
                <span class="popup-train-mode mode-train">🚆 Train direct</span>
            </div>
        `;
    }

    const firstJourney = (j.Trajets && j.Trajets[0]) ? j.Trajets[0] : null;
    const horaires = firstJourney 
        ? `<div class="popup-hours">🕒 Horaires : <b>${firstJourney['Départ']}</b> ➔ <b>${firstJourney['Arrivée']}</b> (${j['Durée (min)']} min)</div>` 
        : `<div class="popup-hours">⏱️ Durée min : <b>${j['Durée (min)']} min</b></div>`;

    return `
        <div class="custom-popup-content">
            <h3 class="popup-city-title">📍 ${escapeHtml(j['Ville'])}</h3>
            <div class="popup-sub-station">${escapeHtml(j['Gare Destination'] || '')}</div>
            <div class="popup-trains-list">
                ${trainBadges}
            </div>
            ${horaires}
            <div class="popup-co2">🌱 Émission carbone : <b>${((j['CO2 (g)'] || 0) / 1000).toFixed(2)} kg CO₂</b></div>
        </div>
    `;
}

function updateTrainDetailsUI(j) {
    const banner = document.getElementById('train-detail-card');
    if (!banner) return;
    banner.classList.remove('hidden');

    const trains = j.trains || [];
    const badgesGroup = document.getElementById('train-badges-group');
    const timesGroup = document.getElementById('train-summary-times');
    const transfersGroup = document.getElementById('train-transfers-info');
    const stepsGroup = document.getElementById('train-steps-breakdown');

    // Badges des trains
    if (trains.length > 0) {
        badgesGroup.innerHTML = trains.map(t => {
            const badgeClass = getTrainBadgeClass(t.mode);
            const icon = getTrainIcon(t.mode);
            return `
                <span class="train-badge ${badgeClass}">
                    ${icon} ${escapeHtml(t.mode || 'Train')}
                    ${t.numero ? `<span class="train-number-tag">N° ${escapeHtml(t.numero)}</span>` : ''}
                </span>
            `;
        }).join('');
    } else {
        badgesGroup.innerHTML = `
            <span class="train-badge mode-train">
                🚆 Train SNCF
            </span>
        `;
    }

    // Horaires & Durée
    const firstJourney = (j.Trajets && j.Trajets[0]) ? j.Trajets[0] : null;
    if (firstJourney) {
        timesGroup.innerHTML = `🕒 <b>${firstJourney['Départ']}</b> ➔ <b>${firstJourney['Arrivée']}</b> <span class="route-time-pill">${j['Durée (min)']} min</span>`;
    } else {
        timesGroup.innerHTML = `⏱️ <span class="route-time-pill">${j['Durée (min)']} min</span>`;
    }

    // Correspondances
    const nbTransfers = j.nb_transfers !== undefined ? j.nb_transfers : Math.max(0, trains.length - 1);
    if (nbTransfers === 0) {
        transfersGroup.innerHTML = `<span class="transfer-pill direct">✓ Trajet Direct</span>`;
    } else {
        transfersGroup.innerHTML = `<span class="transfer-pill transfer">⚡ ${nbTransfers} correspondance${nbTransfers > 1 ? 's' : ''}</span>`;
    }

    // Détail des correspondances si > 1 train
    if (trains.length > 1) {
        stepsGroup.style.display = 'flex';
        stepsGroup.innerHTML = trains.map((t, idx) => {
            const badgeClass = getTrainBadgeClass(t.mode);
            const icon = getTrainIcon(t.mode);
            const timeStr = (t.dep_time && t.arr_time) ? `(${t.dep_time} - ${t.arr_time})` : '';
            return `
                <div class="train-step-row">
                    <span style="font-weight:700; color:var(--sncf-blue-light)">${idx + 1}.</span>
                    <span class="train-badge ${badgeClass}" style="font-size:0.72rem; padding:0.15rem 0.5rem;">
                        ${icon} ${escapeHtml(t.mode || 'Train')} ${t.numero ? 'n° ' + escapeHtml(t.numero) : ''}
                    </span>
                    <span>${escapeHtml(t.from || '')} ➔ ${escapeHtml(t.to || '')}</span>
                    ${timeStr ? `<span style="color:#94a3b8">${timeStr}</span>` : ''}
                </div>
            `;
        }).join('');
    } else {
        stepsGroup.style.display = 'none';
        stepsGroup.innerHTML = '';
    }
}

/* ========================================================
   Update UI for Selected Destination
   ======================================================== */
function selectDestination(j) {
    state.currentCity = j;
    
    highlightSelectedRoute(j);
    updateTrainDetailsUI(j);
    updateCarbonComparisonChart(j);
    updateCharts(j);
    updateAlternatives(j);
}

function highlightSelectedRoute(selectedJ) {
    state.mapLayers.destinations.forEach(item => {
        if (item.j['Ville'] === selectedJ['Ville']) {
            if (item.polyline) {
                item.polyline.setStyle({ color: '#00a8ff', weight: 5, opacity: 0.95 });
                item.polyline.bringToFront();
            }
            item.marker.setZIndexOffset(1000);
            
            // Ouvre le popup détaillé sur le marqueur
            const popupHtml = buildTrainPopupHtml(selectedJ);
            item.marker.bindPopup(popupHtml, { maxWidth: 320, className: 'custom-train-popup' }).openPopup();

            // Met à jour la barre de texte d'en-tête
            const trains = selectedJ.trains || [];
            let trainStr = trains.map(t => `${t.mode || 'Train'}${t.numero ? ' n°' + t.numero : ''}`).join(' + ');
            if (!trainStr) trainStr = 'Train direct';

            const info = state.searchData.info;
            document.getElementById('map-route-text').innerHTML = `
                <b>${escapeHtml(info.depart || 'Départ')} ➔ ${escapeHtml(selectedJ['Ville'])}</b> 
                <span class="route-time-pill">${selectedJ['Durée (min)']} min</span>
                <span class="route-train-pill">🚆 ${escapeHtml(trainStr)}</span>
            `;
        } else {
            if (item.polyline) {
                item.polyline.setStyle({ color: '#64748b', weight: 2.5, opacity: 0.35 });
            }
            item.marker.setZIndexOffset(0);
        }
    });
}

async function updateCarbonComparisonChart(j) {
    const trainKg = ((j['CO2 (g)'] || 800) / 1000);
    const dist = Math.max(1, Math.round(j.distance_km || 100));

    let modes = [
        { mode: "🚆 Train", co2_kg: +(trainKg).toFixed(1), color: "#0088ce" },
        { mode: "⚡ Voiture élec.", co2_kg: +(trainKg * 4).toFixed(1), color: "#10b981" },
        { mode: "👥 Covoiturage", co2_kg: +(trainKg * 7).toFixed(1), color: "#f59e0b" },
        { mode: "🚘 Voiture", co2_kg: +(trainKg * 14.5).toFixed(1), color: "#ef4444" },
        { mode: "✈️ Avion", co2_kg: +(trainKg * 18.0).toFixed(1), color: "#8b5cf6" }
    ];

    try {
        const res = await fetch(`https://impactco2.fr/api/v1/transport?km=${dist}&displayAll=1`);
        const data = await res.json();
        const items = data.data || [];

        const findVal = (nameRegex) => {
            const item = items.find(d => nameRegex.test(d.name));
            return item ? item.value : null;
        };

        const vElec = findVal(/^Voiture électrique/i);
        const covoit = findVal(/^Covoiturage thermique.*4 personnes/i);
        const vTherm = findVal(/^Voiture thermique/i);
        const avion = findVal(/^Avion/i);

        if (vTherm) {
            modes[1].co2_kg = +(vElec || (dist * 0.10)).toFixed(1);
            modes[2].co2_kg = +(covoit || (vTherm / 4)).toFixed(1);
            modes[3].co2_kg = +(vTherm).toFixed(1);
            modes[4].co2_kg = +(avion || (dist * 0.23)).toFixed(1);
        }
    } catch(e) {
        console.error("ImpactCO2 API error", e);
    }

    const labels = modes.map(m => m.mode);
    const dataVals = modes.map(m => m.co2_kg);
    const colors = modes.map(m => m.color);

    const trace = {
        x: labels,
        y: dataVals,
        type: 'bar',
        orientation: 'v',
        marker: {
            color: colors,
            line: { width: 0 }
        },
        text: dataVals.map(val => val + ' kg'),
        textposition: 'outside',
        textangle: 0,
        cliponaxis: false,
        hoverinfo: 'none'
    };

    const layout = {
        margin: { l: 60, r: 20, t: 50, b: 130 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#e4e4e7', family: 'Inter', size: 12 },
        xaxis: {
            tickangle: -45,
            automargin: true,
            gridcolor: 'rgba(255,255,255,0.05)',
            zerolinecolor: 'rgba(255,255,255,0.1)'
        },
        yaxis: {
            title: { text: 'kg CO₂', font: { color: '#a1a1aa', size: 11 } },
            automargin: true,
            gridcolor: 'rgba(255,255,255,0.05)',
            zerolinecolor: 'rgba(255,255,255,0.1)'
        }
    };

    const config = { responsive: true, displayModeBar: false };
    
    Plotly.newPlot('ecoChart', [trace], layout, config);
}

function updateAlternatives(j) {
    const list = document.getElementById('alternatives-list');
    list.innerHTML = '';
    
    let journeys = [...state.searchData.journeys];
    // Exclude current city
    journeys = journeys.filter(x => x['Ville'] !== j['Ville']);
    
    // Sort by "Tranquillité" (we simulate it here by fewer cultural points)
    journeys.sort((a, b) => (a['Points Culturels'] || 0) - (b['Points Culturels'] || 0));
    
    const top3 = journeys.slice(0, 3);
    if (top3.length === 0) {
        list.innerHTML = `<li class="alt-item empty">Aucune alternative trouvée</li>`;
        return;
    }
    
    top3.forEach(altCity => {
        const li = document.createElement('li');
        li.className = 'alt-item';
        li.innerHTML = `<strong>${altCity['Ville']}</strong> - à ${altCity['Durée (min)']} min<br>
        <small style="color:var(--text-sub)">Plus calme (${altCity['Points Culturels']} lieux culturels)</small>`;
        
        li.style.cursor = 'pointer';
        li.addEventListener('click', () => {
            selectDestination(altCity);
        });
        
        list.appendChild(li);
    });
}

/* ========================================================
   Chart.js Initialization & Updates
   ======================================================== */
function initCharts() {
    Chart.defaults.color = '#e4e4e7';
    Chart.defaults.font.family = 'Inter';



    // 2. Radar Chart
    const ctxRadar = document.getElementById('radarChart').getContext('2d');
    state.charts.radar = new Chart(ctxRadar, {
        type: 'radar',
        data: {
            labels: [['Nature &', 'Cyclable'], ['Monuments &', 'Patrimoine'], ['Livre &', 'Musées'], ['Spectacle &', 'Cinéma'], 'Autre'],
            datasets: [{
                label: 'Profil',
                data: [0, 0, 0, 0, 0],
                backgroundColor: 'rgba(139, 92, 246, 0.3)',
                borderColor: '#8b5cf6',
                pointBackgroundColor: '#8b5cf6',
            }]
        },
        options: {
            layout: { padding: 15 },
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                r: {
                    angleLines: { color: 'rgba(255,255,255,0.1)' },
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    pointLabels: { color: '#a1a1aa' },
                    ticks: { display: false, max: 100, min: 0 }
                }
            }
        }
    });
}

function updateCharts(j) {
    if (!state.charts.radar) return;

    // Récupération des comptages depuis le backend
    const types = j.types_counts || {};
    const domaines = j.domaine_counts || {};

    // 1. Nature & Cyclable (Mix of bike paths and protected areas)
    const bikeScore = (j['Aménagements Cyclables'] || 0) * 2;
    const espaceScore = (types['Espace protégé'] || 0) * 10;
    const natureScore = Math.min(100, 30 + bikeScore + espaceScore);

    // 2. Monuments & Patrimoine
    const monumentScore = (types['Monument'] || 0) * 5;
    const patrimoineScore = (domaines['Patrimoine'] || 0) * 5;
    const historyScore = Math.min(100, (monumentScore + patrimoineScore) / 2);

    // 3. Livre & Musées
    const bibliScore = (types['Bibliothèque'] || 0) * 3 + (types['Librairie'] || 0) * 3;
    const museeScore = (types['Musée'] || 0) * 10;
    const cultureScore = Math.min(100, bibliScore + museeScore);

    // 4. Spectacle & Cinéma
    const cineScore = (types['Cinéma'] || 0) * 10;
    const theatreScore = (types['Théâtre'] || 0) * 10;
    const spectacleScore = (domaines['Arts du spectacle'] || 0) * 10;
    const showScore = Math.min(100, cineScore + theatreScore + spectacleScore);

    // 5. Autre (Archives, Arts visuels, etc)
    const archiveScore = (types["Service d'archives"] || 0) * 10;
    const visualScore = (domaines['Arts visuels'] || 0) * 20;
    const otherScore = Math.min(100, archiveScore + visualScore + 10); // Base de 10

    state.charts.radar.data.datasets[0].data = [natureScore, historyScore, cultureScore, showScore, otherScore];
    state.charts.radar.update();
}
