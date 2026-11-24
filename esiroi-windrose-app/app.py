import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Générateur de Rose des Vents - ESIROI", layout="centered")
st.title("🧭 Générateur de Rose des Vents Interactif")
st.markdown(
    "Importez un fichier météorologique (`.epw`, `.csv`, `.xlsx`, `.txt`) pour analyser "
    "la distribution des vents. **Survolez les pétales du graphique** pour afficher le détail."
)

# 1. Dépôt du fichier
uploaded_file = st.file_uploader(
    "Choisissez un fichier météo", type=["csv", "txt", "xlsx", "epw"]
)

if uploaded_file is not None:
    try:
        file_name = uploaded_file.name.lower()
        has_time = False

        # 2. Lecture selon le format du fichier
        if file_name.endswith(".epw"):
            df = pd.read_csv(uploaded_file, skiprows=8, header=None)
            annees = pd.to_numeric(df[0], errors="coerce")
            mois = pd.to_numeric(df[1], errors="coerce")
            jours = pd.to_numeric(df[2], errors="coerce")
            heures = pd.to_numeric(df[3], errors="coerce") - 1

            dates = pd.to_datetime(
                {"year": annees, "month": mois, "day": jours}, errors="coerce"
            )

            df_wind = pd.DataFrame({
                "Date": dates,
                "Annee": annees,
                "Mois": mois,
                "Jour": jours,
                "Heure": heures,
                "Direction": pd.to_numeric(df[20], errors="coerce"),
                "Vitesse": pd.to_numeric(df[21], errors="coerce"),
            }).dropna()
            has_time = True
            st.success("Fichier EPW détecté : années, mois, jours, heures, directions et vitesses extraits.")

        else:
            if file_name.endswith(".xlsx"):
                df = pd.read_excel(uploaded_file)
            else:
                sep = st.radio(
                    "Séparateur du fichier texte/CSV :", [",", ";", "\t"], horizontal=True
                )
                df = pd.read_csv(uploaded_file, sep=sep)

            with st.expander("Aperçu des données brutes"):
                st.dataframe(df.head())

            cols = df.columns.tolist()
            col1, col2, col3 = st.columns(3)
            with col1:
                dir_col = st.selectbox("Colonne Direction (0-360°)", cols)
            with col2:
                speed_col = st.selectbox("Colonne Vitesse (m/s)", cols)
            with col3:
                date_col = st.selectbox("Colonne Date/Heure", ["Aucune"] + cols)

            data_dict = {
                "Direction": pd.to_numeric(df[dir_col], errors="coerce"),
                "Vitesse": pd.to_numeric(df[speed_col], errors="coerce"),
            }

            if date_col != "Aucune":
                dt_series = pd.to_datetime(df[date_col], errors="coerce")
                data_dict["Date"] = dt_series.dt.normalize()
                data_dict["Annee"] = dt_series.dt.year
                data_dict["Mois"] = dt_series.dt.month
                data_dict["Jour"] = dt_series.dt.day
                data_dict["Heure"] = dt_series.dt.hour
                has_time = True

            df_wind = pd.DataFrame(data_dict).dropna()

        # Filtrage des valeurs aberrantes
        df_wind = df_wind[
            (df_wind["Direction"] >= 0)
            & (df_wind["Direction"] <= 360)
            & (df_wind["Vitesse"] >= 0)
            & (df_wind["Vitesse"] < 150)
        ]

        # 3. Filtrage temporel complet (Années, Mois, Jours, Heures)
        if has_time and not df_wind.empty:
            st.subheader("📅 Sélection de la période et de la plage horaire")

            mode_periode = st.radio(
                "Mode de sélection de la période :",
                ["Par Années / Mois / Jours", "Par plage de dates précise (Calendrier)"],
                horizontal=True,
            )

            if mode_periode == "Par plage de dates précise (Calendrier)":
                date_min = df_wind["Date"].min().date()
                date_max = df_wind["Date"].max().date()
                plage_dates = st.date_input(
                    "Choisissez la date de début et la date de fin :",
                    value=(date_min, date_max),
                    min_value=date_min,
                    max_value=date_max,
                )
                if isinstance(plage_dates, tuple) and len(plage_dates) == 2:
                    d_debut, d_fin = pd.to_datetime(plage_dates[0]), pd.to_datetime(plage_dates[1])
                    df_wind = df_wind[(df_wind["Date"] >= d_debut) & (df_wind["Date"] <= d_fin)]

            else:
                col_p1, col_p2, col_p3 = st.columns(3)
                with col_p1:
                    annees_dispos = sorted(df_wind["Annee"].astype(int).unique().tolist())
                    annees_sel = st.multiselect(
                        "Année(s) :", options=annees_dispos, default=annees_dispos
                    )
                with col_p2:
                    noms_mois = {
                        1: "01 - Janvier", 2: "02 - Février", 3: "03 - Mars", 4: "04 - Avril",
                        5: "05 - Mai", 6: "06 - Juin", 7: "07 - Juillet", 8: "08 - Août",
                        9: "09 - Septembre", 10: "10 - Octobre", 11: "11 - Novembre", 12: "12 - Décembre"
                    }
                    mois_dispos = sorted(df_wind["Mois"].astype(int).unique().tolist())
                    mois_sel = st.multiselect(
                        "Mois :",
                        options=mois_dispos,
                        default=mois_dispos,
                        format_func=lambda m: noms_mois.get(m, str(m))
                    )
                with col_p3:
                    jour_debut, jour_fin = st.slider(
                        "Jours du mois :", min_value=1, max_value=31, value=(1, 31)
                    )

                df_wind = df_wind[
                    (df_wind["Annee"].isin(annees_sel))
                    & (df_wind["Mois"].isin(mois_sel))
                    & (df_wind["Jour"] >= jour_debut)
                    & (df_wind["Jour"] <= jour_fin)
                ]

            col_h1, col_h2 = st.columns(2)
            with col_h1:
                heure_debut = st.selectbox(
                    "Heure de début :", options=list(range(24)), index=0, format_func=lambda h: f"{h:02d}h00"
                )
            with col_h2:
                heure_fin = st.selectbox(
                    "Heure de fin :", options=list(range(24)), index=23, format_func=lambda h: f"{h:02d}h00"
                )

            if heure_debut <= heure_fin:
                df_wind = df_wind[
                    (df_wind["Heure"] >= heure_debut) & (df_wind["Heure"] <= heure_fin)
                ]
            else:
                df_wind = df_wind[
                    (df_wind["Heure"] >= heure_debut) | (df_wind["Heure"] <= heure_fin)
                ]

        if df_wind.empty:
            st.warning("Aucune donnée valide pour cette combinaison de dates et d'heures.")
            st.stop()

        # 4. Indicateurs clés sur la période sélectionnée
        total_releves = len(df_wind)
        df_calmes = df_wind[df_wind["Vitesse"] < 1.5]
        df_actifs = df_wind[df_wind["Vitesse"] >= 1.5].copy()
        taux_calmes = (len(df_calmes) / total_releves) * 100

        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Relevés valides", f"{total_releves}")
        kpi2.metric("Vitesse moyenne", f"{df_wind['Vitesse'].mean():.2f} m/s")
        kpi3.metric("Vents calmes (< 1.5 m/s)", f"{taux_calmes:.1f} %")

        # 5. Paramètres visuels
        st.subheader("🎨 Paramètres du graphique")
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            n_sectors = st.slider(
                "Nombre de secteurs (directions)", min_value=8, max_value=36, value=16, step=4
            )
        with col_opt2:
            cmap_choice = st.selectbox(
                "Palette de couleurs", ["Viridis", "Plasma", "YlGnBu", "Turbo", "Cividis"]
            )

        # 6. Calcul des statistiques par secteur et tranche de vitesse (1.5 à 8 m/s)
        sector_width = 360.0 / n_sectors
        # Centrage du secteur Nord autour de 0° (ex: [-11.25°, +11.25°] pour 16 secteurs)
        df_actifs["Secteur_Idx"] = (
            ((df_actifs["Direction"] + sector_width / 2) % 360) // sector_width
        ).astype(int)
        df_actifs["Angle_Centre"] = df_actifs["Secteur_Idx"] * sector_width

        # Labels cardinaux pour le survol
        cardinaux_16 = [
            "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"
        ]
        def get_dir_label(angle):
            idx = int(round((angle % 360) / 22.5)) % 16
            return f"{cardinaux_16[idx]} ({angle:.1f}°)"

        # Découpage des vitesses de 1.5 à 8 m/s
        bins = [1.5, 3.0, 4.5, 6.0, 8.0, 150.0]
        labels_vitesse = [
            "1.5 - 3.0 m/s",
            "3.0 - 4.5 m/s",
            "4.5 - 6.0 m/s",
            "6.0 - 8.0 m/s",
            "> 8.0 m/s",
        ]
        df_actifs["Gamme_Vitesse"] = pd.cut(
            df_actifs["Vitesse"], bins=bins, labels=labels_vitesse, right=False
        )

        # Grille complète (tous les secteurs x toutes les gammes) pour un rendu homogène
        angles_grid = [i * sector_width for i in range(n_sectors)]
        grid = pd.MultiIndex.from_product(
            [angles_grid, labels_vitesse], names=["Angle_Centre", "Gamme_Vitesse"]
        ).to_frame(index=False)

        counts = (
            df_actifs.groupby(["Angle_Centre", "Gamme_Vitesse"], observed=False)
            .size()
            .reset_index(name="Nombre")
        )
        df_plot = pd.merge(grid, counts, on=["Angle_Centre", "Gamme_Vitesse"], how="left").fillna(0)
        df_plot["Frequence"] = (df_plot["Nombre"] / total_releves) * 100
        df_plot["Direction_Label"] = df_plot["Angle_Centre"].apply(get_dir_label)

        # 7. Création de la rose des vents interactive Plotly
        palette = getattr(px.colors.sequential, cmap_choice)
        couleurs = px.colors.sample_colorscale(palette, np.linspace(0.15, 0.95, len(labels_vitesse)))

        fig = go.Figure()

        for i, gamme in enumerate(labels_vitesse):
            sub = df_plot[df_plot["Gamme_Vitesse"] == gamme]
            fig.add_trace(
                go.Barpolar(
                    r=sub["Frequence"],
                    theta=sub["Angle_Centre"],
                    width=[sector_width * 0.85] * len(sub),
                    name=gamme,
                    marker_color=couleurs[i],
                    marker_line_color="white",
                    marker_line_width=1,
                    customdata=np.stack((sub["Direction_Label"], sub["Nombre"]), axis=-1),
                    hovertemplate=(
                        "<b>Direction :</b> %{customdata[0]}<br>"
                        f"<b>Vitesse :</b> {gamme}<br>"
                        "<b>Fréquence :</b> %{r:.2f} %<br>"
                        "<b>Relevés :</b> %{customdata[1]:.0f}"
                        "<extra></extra>"
                    ),
                )
            )

        fig.update_layout(
            title=dict(
                text=f"Rose des vents interactive ({total_releves} relevés | Vents calmes : {taux_calmes:.1f} %)",
                x=0.5,
                xanchor="center",
            ),
            barmode="stack",
            polar=dict(
                hole=0.12,  # Zone centrale à 0% (vents calmes < 1.5 m/s)
                angularaxis=dict(
                    direction="clockwise",
                    rotation=90,  # Nord (0°) en haut
                    tickmode="array",
                    tickvals=[0, 45, 90, 135, 180, 225, 270, 315],
                    ticktext=["N", "NE", "E", "SE", "S", "SO", "O", "NO"],
                ),
                radialaxis=dict(
                    ticksuffix=" %",
                    angle=45,
                    showline=True,
                ),
            ),
            legend=dict(title="Vitesse du vent", orientation="v", x=1.05, y=0.5),
            height=650,
            margin=dict(t=80, b=50, l=50, r=120),
        )

        # Affichage interactif dans Streamlit (avec export PNG haute qualité intégré)
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "toImageButtonOptions": {
                    "format": "png",
                    "filename": "rose_des_vents",
                    "height": 900,
                    "width": 900,
                    "scale": 3,
                }
            },
        )

    except Exception as e:
        st.error(f"Erreur lors du traitement du fichier : {e}")