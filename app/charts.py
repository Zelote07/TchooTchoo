"""
Spécifications Altair (Vega-Lite) : fiche destination et comparaison de deux destinations.

Principes : une idée par graphique, axes linéaires, valeurs écrites à côté des marques
(l'axe disparaît quand il devient redondant), gris pour le contexte. En comparaison, la
destination A est en bleu ardoise et la B en terre cuite (paire validée pour le daltonisme,
écart CVD >= 18), toujours doublées des lettres A / B ou d'une forme. Les graphiques
remplissent leur conteneur pour que la page tienne sur un seul écran.
"""
import altair as alt
import pandas as pd

from scoring import co2_comparison

THEMES = {
    "light": {
        "ink": "#1d1d1b", "ink2": "#57544c", "grid": "#e4e0d6", "axis": "#cfc9bc", "surface": "#fbfaf7",
        "neutral": "#c9c3b6", "a": "#2a5f9e", "b": "#c4532a",
    },
    "dark": {
        "ink": "#ece9e1", "ink2": "#b9b4a8", "grid": "#2e2c27", "axis": "#45423b", "surface": "#1b1a17",
        "neutral": "#55524a", "a": "#5b8fd1", "b": "#d9703f",
    },
}
FONT = "'Source Sans 3', system-ui, -apple-system, 'Segoe UI', sans-serif"
CRITERIA = [("culture", "Culture"), ("calme", "Calme"), ("ruralite", "Campagne"), ("accessibilite", "Accès")]
FAMILIES = [("patrimoine", "Monuments & patrimoine"), ("musees", "Musées & expositions"),
            ("spectacle", "Spectacles & cinéma"), ("livre", "Bibliothèques & librairies")]
CO2_MODES = {"Train régional (TER)": "Train régional", "Voiture essence ou diesel": "Voiture", "Avion": "Avion"}


def theme_config(theme: str) -> dict:
    t = THEMES.get(theme, THEMES["light"])
    return {
        "background": None,
        "font": FONT,
        "view": {"stroke": None},
        "axis": {
            "labelColor": t["ink2"], "titleColor": t["ink2"], "labelFontSize": 13, "titleFontSize": 13,
            "titleFontWeight": 600, "gridColor": t["grid"], "domainColor": t["axis"], "tickColor": t["axis"],
            "labelFont": FONT, "titleFont": FONT,
        },
        "header": {"labelFont": FONT, "labelFontSize": 13, "labelColor": t["ink"], "labelFontWeight": 600},
        "text": {"color": t["ink2"], "font": FONT, "fontSize": 13},
    }


def _finish(chart, theme: str, description: str) -> dict:
    spec = chart.properties(width="container", height="container", description=description).to_dict()
    spec["config"] = theme_config(theme)
    spec["autosize"] = {"type": "fit", "contains": "padding"}
    return spec


def _ab_color(theme: str) -> alt.Color:
    t = THEMES[theme]
    return alt.Color("dest:N", scale=alt.Scale(domain=["A", "B"], range=[t["a"], t["b"]]), legend=None)


def _fmt(v: float) -> str:
    return f"{v:.1f}".replace(".", ",")


# ---------------------------------------------------------------------------
# Fiche destination (une seule gare)
# ---------------------------------------------------------------------------
def composition_chart(station: dict, radius: int, theme: str) -> dict:
    """Ce qu'on peut visiter autour de la gare, par grande famille."""
    t = THEMES[theme]
    data = pd.DataFrame([{"famille": lab, "n": int(station[f"{key}_{radius}km"])} for key, lab in FAMILIES])
    y = alt.Y("famille:N", sort=None, title=None, axis=alt.Axis(ticks=False, domain=False, labelLimit=220,
                                                                 labelPadding=8))
    x = alt.X("n:Q", title=None, axis=None, scale=alt.Scale(domainMax=max(1, int(data["n"].max() * 1.18))))
    bars = alt.Chart(data).mark_bar(color=t["a"], height={"band": 0.6}).encode(
        y=y, x=x, tooltip=[alt.Tooltip("famille:N", title="Famille"), alt.Tooltip("n:Q", title="Nombre de lieux")])
    text = alt.Chart(data).mark_text(align="left", dx=6, fontWeight=600, color=t["ink"]).encode(
        y=y, x="n:Q", text="n:Q")
    return _finish(bars + text, theme, f"Nombre de lieux culturels à moins de {radius} km de la gare, par famille.")


def position_chart(df: pd.DataFrame, selected: str, theme: str) -> dict:
    """Situe la destination parmi les gares proposées : calme (x) et richesse culturelle (y), sur 100."""
    t = THEMES[theme]
    d = df[["id_gare", "nom_gare", "calme", "culture"]].round(0).rename(columns={"id_gare": "id"})
    sel = d[d["id"] == selected]
    x = alt.X("calme:Q", title="Plus calme →", scale=alt.Scale(domain=[0, 100]),
              axis=alt.Axis(values=[0, 50, 100], grid=False, labels=False, ticks=False))
    y = alt.Y("culture:Q", title="Plus de culture →", scale=alt.Scale(domain=[0, 100]),
              axis=alt.Axis(values=[0, 50, 100], grid=False, labels=False, ticks=False))

    zone = alt.Chart(pd.DataFrame([{"x": 50, "y": 50, "x2": 100, "y2": 100}])).mark_rect(
        color=t["a"], opacity=0.07).encode(x="x:Q", y="y:Q", x2="x2:Q", y2="y2:Q")
    rules = alt.Chart(pd.DataFrame({"v": [50]}))
    rule_x = rules.mark_rule(color=t["axis"]).encode(x="v:Q")
    rule_y = rules.mark_rule(color=t["axis"]).encode(y="v:Q")
    labels = pd.DataFrame([
        {"x": 98, "y": 96, "txt": "Pépites : calme et culture", "a": "right"},
        {"x": 2, "y": 96, "txt": "Culturel mais fréquenté", "a": "left"},
        {"x": 98, "y": 4, "txt": "Calme, peu de culture", "a": "right"},
    ])
    annot = alt.layer(*[
        alt.Chart(labels[labels["a"] == side]).mark_text(fontSize=12, baseline="middle", align=side,
                                                         color=t["ink2"]).encode(x="x:Q", y="y:Q", text="txt:N")
        for side in ("left", "right")
    ])
    others = alt.Chart(d).mark_circle(size=22, color=t["neutral"], opacity=0.6).encode(
        x=x, y=y, tooltip=[alt.Tooltip("nom_gare:N", title="Gare")])
    me = alt.Chart(sel).mark_point(filled=True, size=220, color=t["a"], stroke=t["surface"],
                                   strokeWidth=2.5, opacity=1).encode(x=x, y=y)
    # Nom placé du côté libre du point, pour ne pas chevaucher les étiquettes des coins
    high = not sel.empty and sel["culture"].iat[0] > 80
    right = not sel.empty and sel["calme"].iat[0] > 70
    me_label = alt.Chart(sel).mark_text(dy=20 if high else -18, dx=-12 if right else 12,
                                        align="right" if right else "left", fontSize=13, fontWeight=700,
                                        color=t["ink"]).encode(x=x, y=y, text="nom_gare:N")
    return _finish(zone + rule_x + rule_y + others + annot + me + me_label, theme,
                   "Position de la destination parmi les gares proposées : à droite les plus calmes, "
                   "en haut les plus riches en culture. Le coin en haut à droite regroupe les pépites.")


def co2_chart(rows: list[dict], theme: str) -> dict:
    """Émissions du trajet selon le mode : les trains sont mis en avant, le reste en gris."""
    t = THEMES[theme]
    data = pd.DataFrame(rows).sort_values("kg")
    data["label"] = data["kg"].map(lambda v: f"{_fmt(v)} kg")
    y = alt.Y("mode:N", sort=None, title=None, axis=alt.Axis(ticks=False, domain=False, labelLimit=220,
                                                              labelPadding=8))
    x = alt.X("kg:Q", title=None, axis=None, scale=alt.Scale(domainMax=float(data["kg"].max() * 1.25)))
    bars = alt.Chart(data).mark_bar(height={"band": 0.6}).encode(
        y=y, x=x,
        color=alt.Color("groupe:N", scale=alt.Scale(domain=["train", "autre"], range=[t["a"], t["neutral"]]),
                        legend=None),
        tooltip=[alt.Tooltip("mode:N", title="Mode"), alt.Tooltip("kg:Q", title="kg de CO₂", format=".1f")])
    text = alt.Chart(data).mark_text(align="left", dx=6, fontWeight=600).encode(
        y=y, x="kg:Q", text="label:N",
        color=alt.condition(alt.datum.groupe == "train", alt.value(t["ink"]), alt.value(t["ink2"])))
    return _finish(bars + text, theme,
                   "Émissions de CO2 estimées pour un aller simple selon le mode de transport ; les trains en bleu.")


# ---------------------------------------------------------------------------
# Comparaison de deux destinations (A, B)
# ---------------------------------------------------------------------------
def _grouped_bars(data: pd.DataFrame, category: str, order: list[str] | None, value: str, label: str,
                  theme: str, tooltip: list) -> alt.LayerChart:
    """Barres horizontales groupées A (au-dessus) / B (en dessous), valeur écrite au bout."""
    t = THEMES[theme]
    y = alt.Y(f"{category}:N", sort=order, title=None,
              axis=alt.Axis(ticks=False, domain=False, labelLimit=200, labelPadding=8))
    yo = alt.YOffset("dest:N", scale=alt.Scale(domain=["A", "B"], paddingInner=0.12))
    x = alt.X(f"{value}:Q", title=None, axis=None,
              scale=alt.Scale(domainMax=max(1.0, float(data[value].max()) * 1.28)))
    bars = alt.Chart(data).mark_bar().encode(y=y, yOffset=yo, x=x, color=_ab_color(theme), tooltip=tooltip)
    text = alt.Chart(data).mark_text(align="left", dx=5, fontSize=12, fontWeight=600, color=t["ink"]).encode(
        y=y, yOffset=yo, x=f"{value}:Q", text=f"{label}:N")
    return bars + text


def profile_compare(rows: list[dict], theme: str) -> dict:
    """Haltères : pour chaque critère, la note de A et celle de B sur une même ligne de 0 à 10."""
    t = THEMES[theme]
    recs = []
    for key, lab in [("score", "Note globale")] + CRITERIA:
        va, vb = round(rows[0][key] / 10, 1), round(rows[1][key] / 10, 1)
        recs.append({"critere": lab, "lo": min(va, vb), "hi": max(va, vb), "A": va, "B": vb})
    wide = pd.DataFrame(recs)
    long = wide.melt(id_vars=["critere", "lo", "hi"], value_vars=["A", "B"], var_name="dest", value_name="v")
    long["nom"] = long["dest"].map({"A": rows[0]["nom_gare"], "B": rows[1]["nom_gare"]})
    long["label"] = long["v"].map(_fmt)
    # La valeur haute s'écrit à droite de son point, la basse à gauche ; à égalité, une seule étiquette
    long["side"] = (long["v"] == long["hi"]).map({True: "high", False: "low"})
    # À égalité, les deux points se superposent : une seule étiquette, qui le dit
    tie = long["lo"] == long["hi"]
    labels = long[~(tie & (long["dest"] == "B"))].copy()
    labels.loc[tie, "label"] = labels.loc[tie, "label"] + " (A = B)"

    order = wide["critere"].tolist()
    scale = alt.Scale(domain=[-1.2, 11.2])
    y = alt.Y("critere:N", sort=order, title=None,
              axis=alt.Axis(ticks=False, domain=False, labelPadding=10, labelFontWeight=600))
    x = alt.X("v:Q", title=None, scale=scale,
              axis=alt.Axis(values=[0, 5, 10], grid=True, labelExpr="datum.value + '/10'"))
    link = alt.Chart(wide).mark_rule(color=t["neutral"], strokeWidth=3).encode(
        y=alt.Y("critere:N", sort=order), x=alt.X("lo:Q", scale=scale), x2="hi:Q")
    dots = alt.Chart(long).mark_point(filled=True, size=150, opacity=1, stroke=t["surface"], strokeWidth=2).encode(
        y=y, x=x, color=_ab_color(theme),
        shape=alt.Shape("dest:N", scale=alt.Scale(domain=["A", "B"], range=["circle", "square"]), legend=None),
        tooltip=[alt.Tooltip("nom:N", title="Gare"), alt.Tooltip("critere:N", title="Critère"),
                 alt.Tooltip("label:N", title="Note /10")])
    texts = [
        alt.Chart(labels[labels["side"] == side]).mark_text(
            align="left" if side == "high" else "right", dx=10 if side == "high" else -10,
            fontWeight=700, fontSize=12).encode(
            y=alt.Y("critere:N", sort=order), x=alt.X("v:Q", scale=scale), text="label:N", color=_ab_color(theme))
        for side in ("high", "low")
    ]
    return _finish(alt.layer(link, dots, *texts), theme,
                   "Notes sur 10 des deux destinations pour chaque critère ; A en bleu (rond), B en terre cuite (carré).")


def composition_compare(rows: list[dict], radius: int, theme: str) -> dict:
    """Barres groupées : nombre de lieux par famille pour A et B."""
    recs = [{"famille": lab, "dest": dest, "nom": row["nom_gare"], "n": int(row[f"{key}_{radius}km"]),
             "label": str(int(row[f"{key}_{radius}km"]))}
            for key, lab in FAMILIES for dest, row in zip("AB", rows)]
    data = pd.DataFrame(recs)
    chart = _grouped_bars(data, "famille", None, "n", "label", theme,
                          [alt.Tooltip("nom:N", title="Gare"), alt.Tooltip("famille:N", title="Famille"),
                           alt.Tooltip("n:Q", title="Lieux")])
    return _finish(chart, theme, f"Nombre de lieux à moins de {radius} km par famille, "
                                 "A en bleu au-dessus, B en terre cuite en dessous.")


def co2_compare(rows: list[dict], theme: str) -> dict:
    """Barres groupées : CO2 d'un aller simple en train régional, en voiture et en avion, pour A et B."""
    recs = [{"mode": CO2_MODES[r["mode"]], "dest": dest, "nom": row["nom_gare"], "kg": r["kg"],
             "label": f"{_fmt(r['kg'])} kg"}
            for dest, row in zip("AB", rows) for r in co2_comparison(row["distance_km"]) if r["mode"] in CO2_MODES]
    data = pd.DataFrame(recs)
    chart = _grouped_bars(data, "mode", list(CO2_MODES.values()), "kg", "label", theme,
                          [alt.Tooltip("nom:N", title="Gare"), alt.Tooltip("mode:N", title="Mode"),
                           alt.Tooltip("label:N", title="CO₂")])
    return _finish(chart, theme, "CO2 d'un aller simple depuis la gare de départ, en train régional, en voiture "
                                 "et en avion, A en bleu au-dessus, B en terre cuite en dessous.")


def trend_compare(rows: list[dict], theme: str) -> dict | None:
    """Petits multiples : voyageurs par jour en gare de 2015 à 2024, une vignette par destination.

    Chaque vignette a sa propre échelle (les deux gares peuvent différer d'un facteur 100) ;
    ce n'est pas un double axe : les courbes ne se superposent jamais.
    """
    t = THEMES[theme]
    panels = []
    for dest, row in zip("AB", rows):
        recs = [{"dest": dest, "annee": y, "par_jour": round(row[f"total_voyageurs_{y}"] / 365, 1)}
                for y in range(2015, 2025) if row.get(f"total_voyageurs_{y}") is not None]
        if not recs:
            return None
        data = pd.DataFrame(recs)
        x = alt.X("annee:O", title=None, axis=alt.Axis(labelAngle=0, values=[2015, 2020, 2024], ticks=False))
        y = alt.Y("par_jour:Q", title=None, scale=alt.Scale(zero=True, nice=True),
                  axis=alt.Axis(tickCount=3, grid=True, format="~s"))
        base = alt.Chart(data)
        line = base.mark_line(strokeWidth=2).encode(x=x, y=y, color=_ab_color(theme))
        pts = base.mark_point(filled=True, size=26).encode(
            x=x, y=y, color=_ab_color(theme),
            tooltip=[alt.Tooltip("annee:O", title="Année"),
                     alt.Tooltip("par_jour:Q", title="Voyageurs par jour", format=",.0f")])
        last = base.transform_filter(alt.datum.annee == int(data["annee"].max())).mark_text(
            align="right", dy=-11, fontWeight=700, fontSize=12, color=t["ink"]).encode(
            x=x, y=y, text=alt.Text("par_jour:Q", format=",.0f"))
        # Largeur et hauteur fixées côté client (Vega-Lite n'accepte pas "container" dans un hconcat)
        panels.append(alt.layer(line, pts, last).properties(
            width=200, height=120,
            title=alt.Title(f"{dest} · {row['nom_gare']}", anchor="start", fontSize=13, fontWeight=600,
                            color=t["ink"], font=FONT)))
    spec = alt.hconcat(*panels, spacing=24).resolve_scale(y="independent").properties(
        description="Évolution du nombre de voyageurs par jour en gare de 2015 à 2024, une vignette par "
                    "destination, chacune avec sa propre échelle.").to_dict()
    spec["config"] = theme_config(theme)
    spec["autosize"] = {"type": "pad"}  # "fit" ne s'applique pas aux vues concaténées
    return spec
