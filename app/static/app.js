// Autocomplete logic
async function fetchAutocomplete(query) {
    if (query.length < 2) return [];
    try {
        const res = await fetch(`/api/autocomplete?q=${encodeURIComponent(query)}`);
        return await res.json();
    } catch (e) {
        console.error(e);
        return [];
    }
}

function setupAutocomplete(inputId, hiddenId, listId) {
    const input = document.getElementById(inputId);
    const hidden = document.getElementById(hiddenId);
    const list = document.getElementById(listId);
    let debounceTimer;

    input.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        const query = e.target.value;
        
        hidden.value = ''; // Reset ID when user types manually

        if (query.length < 2) {
            list.classList.remove('active');
            return;
        }

        debounceTimer = setTimeout(async () => {
            const results = await fetchAutocomplete(query);
            list.innerHTML = '';
            
            if (results.length > 0) {
                results.forEach(item => {
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
        }, 300);
    });

    // Close list when clicking outside
    document.addEventListener('click', (e) => {
        if (!input.contains(e.target) && !list.contains(e.target)) {
            list.classList.remove('active');
        }
    });
}

setupAutocomplete('depart', 'id_depart', 'depart-list');

// Form submission
document.getElementById('search-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const depart = document.getElementById('depart').value;
    const id_depart = document.getElementById('id_depart').value;
    const max_duration = document.getElementById('max_duration').value;

    const resultsDiv = document.getElementById('results');
    const loader = document.getElementById('loader');
    const journeysGrid = document.getElementById('journeys-grid');

    resultsDiv.classList.add('hidden');
    loader.classList.remove('hidden');

    try {
        let url = `/api/search?max_duration=${max_duration}`;
        url += `&depart=${encodeURIComponent(depart)}`;
        if (id_depart) url += `&id_depart=${encodeURIComponent(id_depart)}`;

        const response = await fetch(url);
        const data = await response.json();

        if (!response.ok) {
            alert(data.error || "Erreur de serveur.");
            loader.classList.add('hidden');
            return;
        }

        document.getElementById('route-title').innerHTML = `Depuis <strong>${data.info.depart}</strong> : Destinations culturelles aléatoires`;

        vegaEmbed('#vis', data.chart_json, {actions: false}).catch(console.error);

        journeysGrid.innerHTML = '';
        data.journeys.forEach((j, index) => {
            const ecoClass = j['CO2 (g)'] < 1500 ? 'eco' : 'warn';
            const ecoText = j['CO2 (g)'] < 1500 ? 'Faible CO2' : 'CO2 Élevé';
            
            const trajetsHtml = j['Trajets'].map(t => `
                <div class="trajet-item" style="border-top: 1px solid #eee; margin-top: 8px; padding-top: 8px;">
                    <p style="margin: 0; font-size: 0.95rem;">🕒 <strong>${t['Départ']}</strong> ➡️ <strong>${t['Arrivée']}</strong></p>
                    <p style="margin: 0; font-size: 0.85rem; color: #555;">Durée : ${t['Durée (min)']} min | CO2 : ${t['CO2 (g)']} g</p>
                </div>
            `).join('');

            const cycleText = j['Aménagements Cyclables'] > 0 
                ? `🚲 ${j['Aménagements Cyclables']} pistes cyclables` 
                : '🚲 Pas de pistes cyclables';
            const cycleStyle = j['Aménagements Cyclables'] > 0 ? "background: #4caf50; color: white;" : "background: #9e9e9e; color: white;";

            const card = document.createElement('div');
            card.className = 'journey-card';
            card.innerHTML = `
                <div style="display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 10px;">
                    <span class="badge ${ecoClass}">${ecoText}</span>
                    <span class="badge" style="background:var(--sncf-blue); color:white;">🏛️ ${j['Points Culturels']} lieux culturels</span>
                    <span class="badge" style="${cycleStyle}">${cycleText}</span>
                </div>
                <h3 style="margin-bottom: 10px; font-size: 1.1rem;">Vers : ${j['Gare Destination']}</h3>
                <div class="journey-meta">
                    <p>Trajet le plus rapide : <strong>${j['Durée (min)']} min</strong></p>
                </div>
            `;
            
            const btn = document.createElement('button');
            btn.style = "margin-top: 15px; width: 100%; padding: 10px; background: var(--sncf-blue, #0088ce); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 1rem; font-weight: 600; transition: background 0.2s;";
            btn.textContent = "Découvrir la destination";
            btn.onmouseover = () => btn.style.background = "#006b9e";
            btn.onmouseout = () => btn.style.background = "var(--sncf-blue, #0088ce)";
            btn.onclick = () => showDestination(j, ecoClass, ecoText, cycleStyle, cycleText, trajetsHtml);
            
            card.appendChild(btn);
            journeysGrid.appendChild(card);
        });

        loader.classList.add('hidden');
        resultsDiv.classList.remove('hidden');

    } catch (err) {
        console.error(err);
        alert("Erreur réseau ou API SNCF.");
        loader.classList.add('hidden');
    }
});

function showDestination(j, ecoClass, ecoText, cycleStyle, cycleText, trajetsHtml) {
    document.querySelector('.hero-section').classList.add('hidden');
    document.getElementById('results').classList.add('hidden');
    document.getElementById('destination-view').classList.remove('hidden');
    
    document.getElementById('dest-title').textContent = j['Ville'];
    document.getElementById('dest-schedules').innerHTML = trajetsHtml;
    
    document.getElementById('dest-badges').innerHTML = `
        <span class="badge ${ecoClass}">${ecoText}</span>
        <span class="badge" style="background:var(--sncf-blue); color:white;">🏛️ ${j['Points Culturels']} lieux culturels</span>
        <span class="badge" style="${cycleStyle}">${cycleText}</span>
    `;
    
    document.getElementById('dest-img').style.display = 'none';
    document.getElementById('dest-summary').textContent = "Recherche d'informations sur la ville...";
    
    // Fetch info from Wikipedia API
    fetch(`https://fr.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(j['Ville'])}`)
        .then(res => res.json())
        .then(data => {
            if (data.extract) {
                document.getElementById('dest-summary').textContent = data.extract;
            } else {
                document.getElementById('dest-summary').textContent = "Aucune description trouvée pour cette ville.";
            }
            if (data.originalimage && data.originalimage.source) {
                const img = document.getElementById('dest-img');
                img.src = data.originalimage.source;
                img.style.display = 'block';
            } else if (data.thumbnail && data.thumbnail.source) {
                const img = document.getElementById('dest-img');
                img.src = data.thumbnail.source;
                img.style.display = 'block';
            }
        })
        .catch(err => {
            document.getElementById('dest-summary').textContent = "Impossible de charger les informations depuis Wikipedia.";
        });
}

document.getElementById('back-btn').addEventListener('click', () => {
    document.getElementById('destination-view').classList.add('hidden');
    document.querySelector('.hero-section').classList.remove('hidden');
    document.getElementById('results').classList.remove('hidden');
});
