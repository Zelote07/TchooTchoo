/**
 * TchooTchoo — page unique "Partez au calme, en train".
 *
 * Deux vues sur un seul écran, sans défilement :
 *  - Explorer : recherche -> /api/dashboard (liste classée + carte) ; sélection -> /api/station (fiche à onglets).
 *  - Comparer : deux destinations A et B depuis le même départ -> /api/compare (+ /api/journey pour chacune).
 * La route /oral injecte window.TCHOO_DEMO (départ, distance, envie et comparaison préréglés).
 */

// "Mes envies" -> pondérations des quatre critères (culture, calme, ruralité, accessibilité)
const PRESETS = {
    equilibre: { culture: 40, calme: 30, ruralite: 20, accessibilite: 10 },
    culture: { culture: 60, calme: 20, ruralite: 10, accessibilite: 10 },
    calme: { culture: 20, calme: 60, ruralite: 15, accessibilite: 5 },
    acces: { culture: 30, calme: 20, ruralite: 10, accessibilite: 40 },
};
const RURAL_GCD = [5, 6, 7];
const WITH_SMALL_TOWNS_GCD = [3, 4, 5, 6, 7];
const GCD_PLAIN = {
    1: 'grande ville', 2: 'ville moyenne', 3: 'petite ville', 4: 'périphérie de ville',
    5: 'bourg rural', 6: 'campagne', 7: 'campagne très peu peuplée',
};
// Rampe séquentielle à une teinte (bleu ardoise), 5 classes = quintiles nationaux de la note
const SCORE_RAMP = {
    light: ['#c6d4e6', '#91acd0', '#5d85b9', '#2a5f9e', '#163b67'],
    dark: ['#1f3654', '#2c5487', '#4a78b5', '#7aa0d3', '#b3c9e6'],
};
const SCORE_WORDS = ['Faible', 'Excellente'];
const TILES = {
    light: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    dark: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
};
const TILE_ATTRIBUTION = 'Fond © Esri, HERE, Garmin, © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
const RADIUS_KM = 10;

const nf = new Intl.NumberFormat('fr-FR');
const dec1 = (x) => (Math.round(x * 10) / 10).toLocaleString('fr-FR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const note10 = (score) => dec1(score / 10);

const state = {
    meta: null,
    stationByName: new Map(),
    stationById: new Map(),
    stations: [],
    summary: null,
    bins: [],
    page: 0,
    pageSize: 8,
    selected: null,
    detail: null,
    embedded: {},
    views: {},
    markers: new Map(),
    map: null,
    tiles: null,
    layers: {},
    legend: null,
    lastScopeKey: null,
    controller: null,
    view: 'explore',
    compare: { a: null, b: null },
    compareData: null,
    cmap: null,
    ctiles: null,
    clayer: null,
};

/* ========================================================
   Thème
   ======================================================== */
function currentTheme() {
    const forced = document.documentElement.dataset.theme;
    if (forced) return forced;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function toggleTheme() {
    const next = currentTheme() === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('tchoo-theme', next); } catch (e) { /* stockage indisponible */ }
    onThemeChange();
}

function onThemeChange() {
    applyTiles();
    drawContextLayer();
    renderOrigin();
    renderMapPoints(false);
    if (state.selected) loadStation(state.selected);
    if (state.view === 'compare') loadCompare();
}

const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

/* ========================================================
   Initialisation
   ======================================================== */
document.addEventListener('DOMContentLoaded', async () => {
    initMap();
    bindControls();
    try {
        state.meta = await (await fetch('/api/meta')).json();
    } catch (err) {
        document.getElementById('summary').textContent = 'Impossible de charger les données : le serveur est-il lancé ?';
        return;
    }
    const list = document.getElementById('origin-list');
    list.innerHTML = state.meta.stations.map((s) => `<option value="${escapeHtml(s.nom_gare)}"></option>`).join('');
    state.meta.stations.forEach((s) => {
        state.stationByName.set(s.nom_gare.toLowerCase(), s);
        state.stationById.set(s.id_gare, s);
    });

    applyDemoOrSharedLink();
    syncDistanceField();
    drawContextLayer();
    await refresh();

    const hash = window.location.hash;
    if (hash === '#comparaison') activateView('compare');
    const ficheTab = { '#pourquoi': 'tab-why', '#situer': 'tab-place', '#y-aller': 'tab-go' }[hash];
    if (ficheTab) activateTab(document.getElementById(ficheTab));
});

function applyDemoOrSharedLink() {
    const demo = window.TCHOO_DEMO;
    const params = new URLSearchParams(window.location.search);
    const originName = demo?.origin || params.get('origin');
    if (originName && state.stationByName.has(originName.toLowerCase())) {
        document.getElementById('origin').value = state.stationByName.get(originName.toLowerCase()).nom_gare;
    }
    if (!demo) return;
    document.getElementById('max_km').value = String(demo.max_km);
    const preset = document.querySelector(`input[name="preset"][value="${demo.preset}"]`);
    if (preset) preset.checked = true;
    [state.compare.a, state.compare.b] = demo.compare;
    state.selected = demo.compare[0];   // la fiche s'ouvre sur la destination A de la démo
    document.getElementById('demo-origin').textContent = demo.origin;
    document.getElementById('demo-flag').hidden = false;
    updateCompareCount();
}

function initMap() {
    state.map = L.map('map', { zoomControl: true, preferCanvas: true, minZoom: 5 }).setView([46.6, 2.4], 6);
    state.map.attributionControl.setPrefix(false);
    applyTiles();
    state.layers.context = L.layerGroup().addTo(state.map);
    state.layers.points = L.layerGroup().addTo(state.map);
    state.layers.origin = L.layerGroup().addTo(state.map);
    state.legend = L.control({ position: 'bottomleft' });
    state.legend.onAdd = () => L.DomUtil.create('div', 'map-legend');
    state.legend.addTo(state.map);
}

function tileLayer() {
    return L.tileLayer(TILES[currentTheme()], { attribution: TILE_ATTRIBUTION, maxZoom: 16 });
}

function applyTiles() {
    if (state.tiles) state.map.removeLayer(state.tiles);
    state.tiles = tileLayer().addTo(state.map);
    if (state.cmap) {
        state.cmap.removeLayer(state.ctiles);
        state.ctiles = tileLayer().addTo(state.cmap);
    }
}

function bindControls() {
    const form = document.getElementById('search-form');
    form.addEventListener('submit', (e) => e.preventDefault());
    form.addEventListener('change', (e) => {
        if (e.target.id === 'origin') syncDistanceField();
        refresh();
    });
    document.getElementById('theme-btn').addEventListener('click', toggleTheme);
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        if (!document.documentElement.dataset.theme) onThemeChange();
    });

    const guide = document.getElementById('guide');
    document.getElementById('guide-btn').addEventListener('click', () => guide.showModal());
    document.getElementById('guide-close').addEventListener('click', () => guide.close());
    guide.addEventListener('click', (e) => { if (e.target === guide) guide.close(); });

    document.getElementById('prev-page').addEventListener('click', () => showPage(state.page - 1));
    document.getElementById('next-page').addEventListener('click', () => showPage(state.page + 1));
    document.getElementById('add-compare').addEventListener('click', addSelectedToCompare);

    document.getElementById('pick-a').addEventListener('change', (e) => setCompare('a', e.target.value));
    document.getElementById('pick-b').addEventListener('change', (e) => setCompare('b', e.target.value));
    document.getElementById('swap').addEventListener('click', () => {
        [state.compare.a, state.compare.b] = [state.compare.b, state.compare.a];
        loadCompare();
    });

    initTabGroup('.views [role="tab"]', (tab) => activateView(tab.id === 'view-tab-compare' ? 'compare' : 'explore'));
    initTabGroup('.tabs [role="tab"]', activateTab);

    // La hauteur réelle des zones change après le chargement des polices ou un redimensionnement :
    // on recalcule alors combien d'idées et de lieux tiennent, pour ne jamais faire défiler
    let lastListH = 0;
    new ResizeObserver(() => {
        const h = document.getElementById('idea-list').clientHeight;
        if (Math.abs(h - lastListH) > 2 && state.stations.length) {
            lastListH = h;
            renderList();
            jumpToSelected();
        }
    }).observe(document.getElementById('idea-list'));
    new ResizeObserver(() => trimPois()).observe(document.getElementById('poi-list'));
    new ResizeObserver(() => state.map.invalidateSize()).observe(document.getElementById('map'));
    let trendTimer;
    new ResizeObserver(() => {
        clearTimeout(trendTimer);
        trendTimer = setTimeout(() => {
            if (state.compareData?.charts.trend) embedChart('c-trend', state.compareData.charts.trend);
        }, 150);
    }).observe(document.getElementById('chart-c-trend'));
}

function syncDistanceField() {
    document.getElementById('max_km').disabled = !originId();
}

/* ========================================================
   Onglets (motif ARIA tabs, flèches gauche/droite) et vues
   ======================================================== */
function initTabGroup(selector, onActivate) {
    const tabs = [...document.querySelectorAll(selector)];
    tabs.forEach((tab, i) => {
        tab.addEventListener('click', () => onActivate(tab));
        tab.addEventListener('keydown', (e) => {
            const dir = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
            if (!dir) return;
            e.preventDefault();
            const next = tabs[(i + dir + tabs.length) % tabs.length];
            next.focus();
            onActivate(next);
        });
    });
}

function selectTab(selector, tab) {
    document.querySelectorAll(selector).forEach((t) => {
        const on = t === tab;
        t.setAttribute('aria-selected', String(on));
        t.tabIndex = on ? 0 : -1;
        document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
    });
}

function activateView(view) {
    state.view = view;
    selectTab('.views [role="tab"]', document.getElementById(view === 'compare' ? 'view-tab-compare' : 'view-tab-explore'));
    if (view === 'compare') {
        initCompareMap();
        if (!state.compare.a || !state.compare.b) fillCompareDefaults();
        loadCompare();
    } else {
        state.map.invalidateSize();
        renderList();
        trimPois();
    }
}

/* ========================================================
   Recherche
   ======================================================== */
function originId() {
    const name = document.getElementById('origin').value.trim().toLowerCase();
    return state.stationByName.get(name)?.id_gare || null;
}

function searchParams() {
    const p = new URLSearchParams();
    const origin = originId();
    if (origin) {
        p.set('origin', origin);
        const maxKm = document.getElementById('max_km').value;
        if (+maxKm) p.set('max_km', maxKm);
    }
    const smallTowns = document.getElementById('small_towns').checked;
    p.set('gcd', (smallTowns ? WITH_SMALL_TOWNS_GCD : RURAL_GCD).join(','));
    if (document.getElementById('pmr_only').checked) p.set('pmr_only', '1');
    p.set('radius', RADIUS_KM);
    const preset = PRESETS[document.querySelector('input[name="preset"]:checked').value];
    Object.entries(preset).forEach(([k, v]) => p.set(`w_${k}`, v));
    return p;
}

async function refresh() {
    if (!state.meta) return;
    const params = searchParams();
    // Recadrer la carte seulement si le périmètre change (pas pour un simple changement d'envie)
    const scopeKey = [...params].filter(([k]) => !k.startsWith('w_')).map((e) => e.join('=')).join('&');

    state.controller?.abort();
    state.controller = new AbortController();
    let data;
    try {
        data = await (await fetch(`/api/dashboard?${params}`, { signal: state.controller.signal })).json();
    } catch (err) {
        if (err.name !== 'AbortError') document.getElementById('summary').textContent = 'Erreur de chargement, réessayez.';
        return;
    }
    state.stations = data.stations;
    state.summary = data.summary;
    state.bins = data.bins;

    renderSummary();
    renderOrigin();
    renderMapPoints(scopeKey !== state.lastScopeKey);
    state.lastScopeKey = scopeKey;

    if (!state.stations.some((s) => s.id_gare === state.selected)) state.selected = state.stations[0]?.id_gare || null;
    state.page = 0;
    renderList();
    if (state.selected) {
        jumpToSelected();
        highlightSelection();
        loadStation(state.selected);
    } else {
        clearDetail();
    }
    if (state.view === 'compare') loadCompare();
}

function renderSummary() {
    const s = state.summary;
    const el = document.getElementById('summary');
    if (!s.n_gares) {
        el.textContent = 'Aucune gare ne correspond. Élargissez la distance ou décochez une option.';
        return;
    }
    const where = document.getElementById('small_towns').checked ? 'gares de campagne et petites villes' : 'gares de campagne';
    el.innerHTML = `<strong>${nf.format(s.n_gares)}</strong> ${where}, dont <strong>${nf.format(s.n_pepites)}</strong> pépites`;
}

/* ========================================================
   Liste paginée (s'adapte à la hauteur : pas de défilement)
   ======================================================== */
function computePageSize() {
    const list = document.getElementById('idea-list');
    const probe = list.querySelector('li');
    const itemH = probe ? probe.offsetHeight : 55;
    return Math.max(3, Math.floor(list.clientHeight / itemH));
}

function renderList() {
    const list = document.getElementById('idea-list');
    if (!state.stations.length) {
        list.innerHTML = '';
        document.getElementById('page-info').textContent = '';
        return;
    }
    if (!list.children.length) list.innerHTML = ideaHtml(state.stations[0], 0);   // sonde de hauteur
    state.pageSize = computePageSize();
    const pages = Math.max(1, Math.ceil(state.stations.length / state.pageSize));
    state.page = Math.min(Math.max(0, state.page), pages - 1);
    const start = state.page * state.pageSize;
    const slice = state.stations.slice(start, start + state.pageSize);

    list.innerHTML = slice.map((s, i) => ideaHtml(s, start + i)).join('');
    list.querySelectorAll('.idea').forEach((btn) => btn.addEventListener('click', () => selectStation(btn.dataset.id)));

    document.getElementById('page-info').textContent =
        `${start + 1}–${Math.min(start + state.pageSize, state.stations.length)} sur ${nf.format(state.stations.length)}`;
    document.getElementById('prev-page').disabled = state.page === 0;
    document.getElementById('next-page').disabled = state.page >= pages - 1;
}

function compareKey(id) {
    if (id === state.compare.a) return '<span class="key key-a" title="Destination A de la comparaison">A</span>';
    if (id === state.compare.b) return '<span class="key key-b" title="Destination B de la comparaison">B</span>';
    return '';
}

function ideaHtml(s, index) {
    const tags = [
        s.pepite ? '<span class="tag tag-pepite">Pépite</span>' : '',
        s.acces_fauteuil ? '<span class="tag tag-access" title="Gare accessible en fauteuil roulant">Accessible</span>' : '',
    ].join('');
    const where = s.distance_km != null ? `à ${nf.format(Math.round(s.distance_km))} km` : escapeHtml(s.region || '');
    return `<li><button type="button" class="idea" data-id="${escapeHtml(s.id_gare)}" aria-current="${s.id_gare === state.selected}"
        aria-label="${escapeHtml(s.nom_gare)}, note ${note10(s.score)} sur 10${s.pepite ? ', pépite' : ''}">
        <span class="idea-rank" aria-hidden="true">${index + 1}</span>
        <span class="idea-text"><span class="idea-name">${escapeHtml(s.nom_gare)}${compareKey(s.id_gare)}</span>
            <span class="idea-meta">${tags}${where}</span></span>
        <span class="idea-note" aria-hidden="true">${note10(s.score)}<small>/10</small></span>
    </button></li>`;
}

function showPage(page) {
    state.page = page;
    renderList();
}

function jumpToSelected() {
    const idx = state.stations.findIndex((s) => s.id_gare === state.selected);
    if (idx < 0) return;
    const page = Math.floor(idx / state.pageSize);
    if (page !== state.page) showPage(page);
}

/* ========================================================
   Carte (Explorer)
   ======================================================== */
function contextColor() {
    return currentTheme() === 'dark' ? '#3a3832' : '#cdc8bc';
}

function drawContextLayer() {
    if (!state.meta) return;
    state.layers.context.clearLayers();
    state.meta.stations.forEach((s) => {
        L.circleMarker([s.latitude, s.longitude], {
            radius: 1.8, stroke: false, fillColor: contextColor(), fillOpacity: 0.9, interactive: false,
        }).addTo(state.layers.context);
    });
}

function binIndex(score) {
    let i = 0;
    while (i < state.bins.length && score > state.bins[i]) i++;
    return i;
}

function hoverTooltip(s) {
    return `<strong>${escapeHtml(s.nom_gare)}</strong><br>Note ${note10(s.score)}/10`;
}

function originMarker(id) {
    const s = state.stationById.get(id);
    const icon = L.divIcon({
        className: '',
        html: `<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="16" height="16" transform="rotate(45 12 12)" fill="${cssVar('--ink')}" stroke="${cssVar('--surface')}" stroke-width="2.5"/></svg>`,
        iconSize: [22, 22], iconAnchor: [11, 11],
    });
    return L.marker([s.latitude, s.longitude], { icon, keyboard: false, zIndexOffset: 1000 })
        .bindTooltip(`Départ : <strong>${escapeHtml(s.nom_gare)}</strong>`, { direction: 'top' });
}

function renderMapPoints(fit) {
    state.layers.points.clearLayers();
    state.markers.clear();
    const ramp = SCORE_RAMP[currentTheme()];
    const surface = cssVar('--surface');

    // Les meilleures notes sont dessinées en dernier, donc au-dessus
    [...state.stations].reverse().forEach((s) => {
        const m = L.circleMarker([s.latitude, s.longitude], {
            radius: 6.5, weight: 1.2, color: surface, fillColor: ramp[binIndex(s.score)], fillOpacity: 1,
        });
        m.bindTooltip(hoverTooltip(s), { direction: 'top', offset: [0, -6] });
        m.on('click', () => selectStation(s.id_gare));
        m.addTo(state.layers.points);
        state.markers.set(s.id_gare, m);
    });

    state.legend.getContainer().innerHTML = `
        <div class="ttl">Note de la destination</div>
        <div class="scale"><span>${SCORE_WORDS[0]}</span>${ramp.map((c) => `<i style="background:${c}"></i>`).join('')}<span>${SCORE_WORDS[1]}</span></div>
        <div class="row"><span class="dot" style="background:${contextColor()}"></span>Autre gare</div>
        ${originId() ? `<div class="row"><span class="dot" style="background:${cssVar('--ink')};border-radius:1px;transform:rotate(45deg)"></span>Votre départ</div>` : ''}`;

    if (fit && state.stations.length) {
        const pts = state.stations.map((s) => [s.latitude, s.longitude]);
        const o = originId() && state.stationById.get(originId());
        if (o) pts.push([o.latitude, o.longitude]);
        state.map.fitBounds(pts, { padding: [30, 30], maxZoom: 10 });
    }
    highlightSelection();
}

function renderOrigin() {
    state.layers.origin.clearLayers();
    const id = originId();
    if (id) originMarker(id).addTo(state.layers.origin);
}

function highlightSelection() {
    const surface = cssVar('--surface');
    const ink = cssVar('--ink');
    const byId = new Map(state.stations.map((s) => [s.id_gare, s]));
    state.markers.forEach((m, id) => {
        const sel = id === state.selected;
        const wasSel = m.getTooltip()?.options.permanent;
        m.setStyle({ radius: sel ? 10 : 6.5, weight: sel ? 3 : 1.2, color: sel ? ink : surface });
        if (sel && !wasSel) {
            m.bringToFront();
            m.unbindTooltip().bindTooltip(escapeHtml(byId.get(id).nom_gare), {
                permanent: true, direction: 'top', offset: [0, -10], className: 'selected-label',
            });
        } else if (!sel && wasSel) {
            m.unbindTooltip().bindTooltip(hoverTooltip(byId.get(id)), { direction: 'top', offset: [0, -6] });
        }
    });
    document.querySelectorAll('.idea').forEach((btn) => btn.setAttribute('aria-current', String(btn.dataset.id === state.selected)));
}

/* ========================================================
   Sélection & fiche destination (Explorer)
   ======================================================== */
function selectStation(id) {
    if (!id || id === state.selected) return;
    state.selected = id;
    jumpToSelected();
    highlightSelection();
    const m = state.markers.get(id);
    if (m && !state.map.getBounds().pad(-0.1).contains(m.getLatLng())) state.map.panTo(m.getLatLng());
    loadStation(id);
}

let stationController;
async function loadStation(id) {
    const params = searchParams();
    params.set('theme', currentTheme());
    stationController?.abort();
    stationController = new AbortController();
    try {
        state.detail = await (await fetch(`/api/station/${encodeURIComponent(id)}?${params}`, { signal: stationController.signal })).json();
    } catch (err) {
        return;
    }
    state.embedded = {};
    renderDetail();
    embedActiveTab();
}

function renderDetail() {
    const { station: s, pepite, pois } = state.detail;
    document.getElementById('dest-name').textContent = s.nom_gare;
    document.getElementById('dest-place').textContent = [s.commune, s.region].filter(Boolean).join(' · ');
    document.getElementById('dest-badges').innerHTML = [
        pepite ? '<span class="tag tag-pepite">Pépite</span>' : '',
        s.acces_fauteuil ? '<span class="tag tag-access">Accessible en fauteuil</span>' : '',
    ].join('');
    const note = document.getElementById('dest-note');
    note.querySelector('.note-value').textContent = note10(s.score);
    note.setAttribute('aria-label', `Note ${note10(s.score)} sur 10`);
    renderAddFeedback();

    // À visiter
    document.getElementById('visit-title').textContent = `${nf.format(s.lieux)} lieux à visiter à moins de ${RADIUS_KM} km`;
    const ul = document.getElementById('poi-list');
    ul.innerHTML = pois.length ? pois.map((p) => `
        <li><span class="poi-text"><span class="poi-name">${escapeHtml(capitalize(p.nom))}</span>
            <span class="poi-meta">${escapeHtml(p.type)} · ${escapeHtml(p.commune)}${p.label ? ` · <span class="poi-label">${escapeHtml(p.label)}</span>` : ''}</span></span>
            <span class="poi-dist">${dec1(p.dist_km)} km</span></li>`).join('')
        : '<li class="chart-empty">Aucun lieu recensé autour de cette gare.</li>';
    trimPois();

    // Pourquoi ici ?
    document.getElementById('reasons').innerHTML = reasons(s).map((r) => `
        <li class="reason">
            <span class="reason-label">${r.label}</span>
            <span class="reason-score">${dec1(r.value / 10)}<small>/10</small></span>
            <span class="reason-text">${r.text}</span>
            <span class="reason-bar" aria-hidden="true"><span style="width:${r.value}%"></span></span>
        </li>`).join('');

    // Y aller
    renderTrip(s);
}

function calmText(voyageurs) {
    if (voyageurs == null) return 'Fréquentation de la gare inconnue.';
    const ratio = state.meta.medians.voyageurs / Math.max(1, voyageurs);
    const comparison = ratio >= 2 ? `, ${nf.format(Math.round(ratio))} fois moins qu'une gare typique`
        : ratio >= 1 ? ', un peu moins qu\'une gare typique' : ', plus qu\'une gare typique';
    return `${nf.format(Math.round(voyageurs))} voyageurs par an en gare${comparison}.`;
}

function reasons(s) {
    const access = s.acces_fauteuil ? 'Gare accessible en fauteuil roulant.'
        : s.acces_pmr_partiel ? 'Accès partiel pour les personnes à mobilité réduite.'
            : 'Gare sans équipement pour les fauteuils roulants.';
    return [
        { label: 'Culture', value: s.culture, text: `${nf.format(s.lieux)} lieux à moins de ${RADIUS_KM} km, dont ${nf.format(s.remarquables)} labellisés (Unesco, Musée de France…).` },
        { label: 'Calme', value: s.calme, text: calmText(s.voyageurs) },
        { label: 'Campagne', value: s.ruralite, text: `Commune de type « ${GCD_PLAIN[s.gcd] || 'inconnu'} » selon l'INSEE.` },
        { label: 'Accès', value: s.accessibilite, text: access },
    ];
}

function renderTrip(s) {
    const trip = document.getElementById('trip');
    const origin = originId();
    const co2 = state.detail.co2;
    document.getElementById('co2-title').hidden = !co2;
    document.getElementById('co2-note').textContent = '';
    if (!origin) {
        trip.innerHTML = `<div class="trip-empty">
            <p>Indiquez votre gare de départ pour voir la distance, le prochain train et l'empreinte carbone du voyage.</p>
            <button type="button" class="btn-outline" id="focus-origin">Choisir ma gare de départ</button></div>`;
        document.getElementById('focus-origin').addEventListener('click', () => document.getElementById('origin').focus());
        return;
    }
    trip.innerHTML = `<div class="trip">
        <p class="trip-main"><strong>${nf.format(Math.round(s.distance_km))} km</strong> à vol d'oiseau depuis ${escapeHtml(state.stationById.get(origin).nom_gare)}</p>
        <p class="trip-live" id="trip-live">${state.meta.live_journeys ? 'Recherche du prochain train…' : 'Horaires indisponibles (clé API SNCF non configurée).'}</p></div>`;
    if (co2) {
        const ter = co2.find((r) => r.mode.includes('TER')).kg;
        const car = co2.find((r) => r.mode.includes('essence')).kg;
        document.getElementById('co2-note').innerHTML = `En train régional, vous émettez <strong>${nf.format(Math.round(car / ter))} fois moins</strong> de CO₂ qu'en voiture.`;
    }
    if (state.meta.live_journeys) {
        fetchJourney(origin, s.id_gare).then((j) => {
            const el = document.getElementById('trip-live');
            if (s.id_gare !== state.selected || !el) return;
            el.innerHTML = j.error ? escapeHtml(j.error)
                : `Prochain train : <strong>${duration(j.duration_min)}</strong>, ${transfers(j.nb_transfers)} — départ le ${j.date} à ${j.departure}, arrivée ${j.arrival}.`;
        });
    }
}

const journeyCache = new Map();
function fetchJourney(from, to) {
    const key = `${from}|${to}`;
    if (!journeyCache.has(key)) {
        journeyCache.set(key, fetch(`/api/journey?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`)
            .then(async (res) => {
                const j = await res.json();
                return res.ok ? j : { error: j.error || 'Horaires indisponibles.' };
            })
            .catch(() => ({ error: 'Horaires indisponibles pour le moment.' })));
    }
    return journeyCache.get(key);
}

function duration(min) {
    const h = Math.floor(min / 60);
    return h ? `${h} h ${String(min % 60).padStart(2, '0')}` : `${min} min`;
}

function transfers(n) {
    return n ? `${n} correspondance${n > 1 ? 's' : ''}` : 'direct';
}

function trimPois() {
    // Ne garder que les lieux entièrement visibles (pas de ligne coupée, pas de défilement)
    const ul = document.getElementById('poi-list');
    if (ul.closest('[hidden]')) return;
    const items = [...ul.children];
    items.forEach((li) => { li.hidden = false; });
    const bottom = ul.getBoundingClientRect().bottom;
    items.forEach((li) => { if (li.getBoundingClientRect().bottom > bottom + 1) li.hidden = true; });
}

function clearDetail() {
    state.detail = null;
    document.getElementById('dest-name').textContent = 'Aucune destination';
    document.getElementById('dest-place').textContent = 'Élargissez votre recherche.';
    document.getElementById('dest-badges').innerHTML = '';
    document.querySelector('#dest-note .note-value').textContent = '–';
    ['composition', 'position', 'co2'].forEach((k) => {
        state.views[k]?.finalize();
        delete state.views[k];
        document.getElementById(`chart-${k}`).innerHTML = '';
    });
    ['poi-list', 'reasons', 'trip'].forEach((id) => { document.getElementById(id).innerHTML = ''; });
}

const TAB_CHARTS = { 'panel-visit': ['composition'], 'panel-why': [], 'panel-place': ['position'], 'panel-go': ['co2'] };

function activateTab(tab) {
    selectTab('.tabs [role="tab"]', tab);
    embedActiveTab();
    trimPois();
}

function embedActiveTab() {
    if (!state.detail) return;
    const panel = document.querySelector('.tab-panel:not([hidden])');
    TAB_CHARTS[panel.id].forEach((key) => {
        if (!state.embedded[key]) {
            state.embedded[key] = true;
            embedChart(key, state.detail.charts[key]);
        }
    });
}

/* ========================================================
   Comparaison A / B
   ======================================================== */
function updateCompareCount() {
    const n = [state.compare.a, state.compare.b].filter(Boolean).length;
    document.getElementById('compare-count').textContent = n ? `(${n})` : '';
}

function addSelectedToCompare() {
    const id = state.selected;
    if (!id) return;
    if (id === state.compare.a || id === state.compare.b) {
        renderAddFeedback();
        return;
    }
    if (!state.compare.a) state.compare.a = id;
    else state.compare.b = id;
    updateCompareCount();
    renderList();
    renderAddFeedback(true);
}

function renderAddFeedback(justAdded = false) {
    const el = document.getElementById('add-feedback');
    const btn = document.getElementById('add-compare');
    const slot = state.selected === state.compare.a ? 'A' : state.selected === state.compare.b ? 'B' : null;
    btn.hidden = Boolean(slot);
    if (!slot) { el.innerHTML = ''; return; }
    const ready = state.compare.a && state.compare.b;
    el.innerHTML = `${justAdded ? 'Ajoutée' : 'Dans la comparaison'} en <span class="key key-${slot.toLowerCase()}">${slot}</span>.
        ${ready ? '<button type="button" id="open-compare">Voir la comparaison</button>' : 'Choisissez une seconde gare.'}`;
    document.getElementById('open-compare')?.addEventListener('click', () => activateView('compare'));
}

function fillCompareDefaults() {
    const ids = state.stations.map((s) => s.id_gare).filter((id) => id !== state.compare.a && id !== state.compare.b);
    if (!state.compare.a) state.compare.a = ids.shift() || null;
    if (!state.compare.b) state.compare.b = ids.shift() || null;
    updateCompareCount();
}

function setCompare(slot, id) {
    const other = slot === 'a' ? 'b' : 'a';
    if (id === state.compare[other]) state.compare[other] = state.compare[slot];   // éviter A = B : on inverse
    state.compare[slot] = id;
    updateCompareCount();
    renderList();
    loadCompare();
}

function renderPickers() {
    const ids = state.stations.map((s) => s.id_gare);
    [state.compare.a, state.compare.b].forEach((id) => { if (id && !ids.includes(id)) ids.push(id); });
    const byId = new Map(state.stations.map((s) => [s.id_gare, s]));
    const options = ids.map((id) => {
        const s = byId.get(id);
        const label = s ? `${s.nom_gare} — ${note10(s.score)}/10` : `${state.stationById.get(id).nom_gare} (hors sélection)`;
        return `<option value="${escapeHtml(id)}">${escapeHtml(label)}</option>`;
    }).join('');
    ['a', 'b'].forEach((slot) => {
        const sel = document.getElementById(`pick-${slot}`);
        sel.innerHTML = options;
        sel.value = state.compare[slot] || '';
    });
}

function initCompareMap() {
    if (state.cmap) { state.cmap.invalidateSize(); return; }
    state.cmap = L.map('map-compare', { zoomControl: false, attributionControl: true, preferCanvas: true });
    state.cmap.attributionControl.setPrefix(false);
    state.ctiles = tileLayer().addTo(state.cmap);
    state.clayer = L.layerGroup().addTo(state.cmap);
    state.cmap.setView([46.6, 2.4], 5);
}

let compareController;
async function loadCompare() {
    const { a, b } = state.compare;
    renderPickers();
    const origin = originId();
    document.getElementById('compare-from').innerHTML = origin
        ? `Depuis <strong>${escapeHtml(state.stationById.get(origin).nom_gare)}</strong>`
        : 'Sans gare de départ <span class="sr-only">(choisissez-en une en haut)</span>';
    if (!a || !b) {
        document.getElementById('verdict').textContent = 'Choisissez deux destinations à comparer.';
        return;
    }
    const params = searchParams();
    params.set('theme', currentTheme());
    params.set('a', a);
    params.set('b', b);
    compareController?.abort();
    compareController = new AbortController();
    try {
        state.compareData = await (await fetch(`/api/compare?${params}`, { signal: compareController.signal })).json();
    } catch (err) {
        return;
    }
    const d = state.compareData;
    renderVerdict(d);
    renderCompareMap(d);
    renderTripTable(d);
    embedChart('c-profile', d.charts.profile);
    embedChart('c-composition', d.charts.composition);
    embedChart('c-co2', d.charts.co2, 'Choisissez une gare de départ pour comparer le CO₂ du voyage.');
    embedChart('c-trend', d.charts.trend, 'Fréquentation inconnue pour l\'une des deux gares.');
}

function nameSpan(slot, s) {
    return `<span class="v${slot}">${escapeHtml(s.nom_gare)}</span>`;
}

function renderVerdict(d) {
    const A = d.a.station;
    const B = d.b.station;
    const parts = [];
    const calmGap = A.calme - B.calme;
    if (Math.abs(calmGap) >= 10) {
        const [w, l, ws, ls] = calmGap > 0 ? [A, B, 'a', 'b'] : [B, A, 'b', 'a'];
        parts.push(`${nameSpan(ws, w)} est plus calme (${dec1(w.calme / 10)} contre ${dec1(l.calme / 10)})`);
    }
    if (A.lieux !== B.lieux) {
        const [w, l, ws] = A.lieux > B.lieux ? [A, B, 'a'] : [B, A, 'b'];
        parts.push(`${nameSpan(ws, w)} a plus de lieux à visiter (${nf.format(w.lieux)} contre ${nf.format(l.lieux)})`);
    }
    const gap = A.score - B.score;
    const overall = Math.abs(gap) < 1
        ? 'Selon vos envies, les deux se valent.'
        : `Selon vos envies, ${nameSpan(gap > 0 ? 'a' : 'b', gap > 0 ? A : B)} l'emporte : ${note10(Math.max(A.score, B.score))} contre ${note10(Math.min(A.score, B.score))}.`;
    document.getElementById('verdict').innerHTML = `${parts.length ? `${parts.join(' ; ')}. ` : ''}${overall}`;
}

function renderCompareMap(d) {
    state.clayer.clearLayers();
    const pts = [];
    const origin = originId();
    if (origin) {
        const o = state.stationById.get(origin);
        originMarker(origin).addTo(state.clayer);
        pts.push([o.latitude, o.longitude]);
    }
    [['a', d.a.station], ['b', d.b.station]].forEach(([slot, s]) => {
        const color = cssVar(`--${slot}`);
        const ll = [s.latitude, s.longitude];
        if (origin) {
            const o = state.stationById.get(origin);
            L.polyline([[o.latitude, o.longitude], ll], { color, weight: 2, dashArray: '5 6', opacity: 0.9, interactive: false })
                .addTo(state.clayer);
        }
        L.circleMarker(ll, { radius: 8, weight: 2, color: cssVar('--surface'), fillColor: color, fillOpacity: 1 })
            .bindTooltip(`${slot.toUpperCase()} · ${escapeHtml(s.nom_gare)}`, {
                // A à gauche, B à droite : les étiquettes ne se chevauchent pas quand les gares sont proches
                permanent: true, direction: slot === 'a' ? 'left' : 'right', offset: [slot === 'a' ? -8 : 8, 0],
                className: `key-label key-label-${slot}`,
            })
            .addTo(state.clayer);
        pts.push(ll);
    });
    state.cmap.invalidateSize();
    state.cmap.fitBounds(pts, { padding: [40, 40], maxZoom: 9 });
}

function renderTripTable(d) {
    const A = d.a.station;
    const B = d.b.station;
    const origin = originId();
    const best = (va, vb, lowerIsBetter = true) => {
        if (va == null || vb == null || va === vb) return ['', ''];
        return (va < vb) === lowerIsBetter ? ['best', ''] : ['', 'best'];
    };
    const yesNo = (v) => (v ? 'Oui' : 'Non');
    const [dA, dB] = best(A.distance_km, B.distance_km);
    const [fA, fB] = best(A.acces_fauteuil ? 0 : 1, B.acces_fauteuil ? 0 : 1);
    const [pA, pB] = best(d.a.pepite ? 0 : 1, d.b.pepite ? 0 : 1);
    const km = (v) => (v == null ? '—' : `${nf.format(Math.round(v))} km`);
    const table = document.getElementById('trip-table');
    table.innerHTML = `<caption class="sr-only">Comparaison du voyage vers A et B</caption>
        <thead><tr><td></td>
            <th scope="col"><span class="key key-a">A</span> ${escapeHtml(A.nom_gare)}</th>
            <th scope="col"><span class="key key-b">B</span> ${escapeHtml(B.nom_gare)}</th></tr></thead>
        <tbody>
            <tr><th scope="row">Distance</th><td class="${dA}">${km(A.distance_km)}</td><td class="${dB}">${km(B.distance_km)}</td></tr>
            <tr><th scope="row">Prochain train</th><td id="trip-a">${origin ? '…' : '—'}</td><td id="trip-b">${origin ? '…' : '—'}</td></tr>
            <tr><th scope="row">Accès fauteuil</th><td class="${fA}">${yesNo(A.acces_fauteuil)}</td><td class="${fB}">${yesNo(B.acces_fauteuil)}</td></tr>
            <tr><th scope="row">Pépite</th><td class="${pA}">${yesNo(d.a.pepite)}</td><td class="${pB}">${yesNo(d.b.pepite)}</td></tr>
        </tbody>`;
    if (!origin) return;
    if (!state.meta.live_journeys) {
        ['a', 'b'].forEach((slot) => { document.getElementById(`trip-${slot}`).textContent = 'indisponible'; });
        return;
    }
    Promise.all([fetchJourney(origin, A.id_gare), fetchJourney(origin, B.id_gare)]).then(([ja, jb]) => {
        if (state.compareData !== d) return;
        const [bA, bB] = best(ja.duration_min, jb.duration_min);
        [['a', ja, bA], ['b', jb, bB]].forEach(([slot, j, cls]) => {
            const cell = document.getElementById(`trip-${slot}`);
            if (!cell) return;
            cell.className = cls;
            cell.title = j.error ? 'Aucun train trouvé aujourd\'hui ni demain matin' : `Départ le ${j.date} à ${j.departure}, arrivée ${j.arrival}`;
            cell.innerHTML = j.error ? 'aucun train proche'
                : `${duration(j.duration_min)} <small>· ${j.nb_transfers ? `${j.nb_transfers} corresp.` : 'direct'}</small>`;
        });
    });
}

/* ========================================================
   Graphiques Vega-Lite (specs produites par Altair côté serveur)
   ======================================================== */
async function embedChart(key, spec, emptyMessage = '') {
    const el = document.getElementById(`chart-${key}`);
    state.views[key]?.finalize();
    delete state.views[key];
    if (!spec) { el.innerHTML = emptyMessage ? `<p class="chart-empty">${emptyMessage}</p>` : ''; return; }
    if (spec.hconcat) {
        // Petits multiples : Vega-Lite n'accepte pas "container" dans un hconcat, on calcule la taille
        spec = structuredClone(spec);
        const w = (el.clientWidth - 24 - spec.hconcat.length * 46) / spec.hconcat.length;
        spec.hconcat.forEach((p) => { p.width = Math.max(80, w); p.height = Math.max(60, el.clientHeight - 58); });
    }
    const result = await vegaEmbed(el, spec, { actions: false, renderer: 'svg', tooltip: { theme: 'custom' } });
    el.querySelector('svg')?.setAttribute('role', 'img');
    state.views[key] = result.view;
}

/* ========================================================
   Utilitaires
   ======================================================== */
function capitalize(str) {
    return str ? str.charAt(0).toUpperCase() + str.slice(1) : '';
}

function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
