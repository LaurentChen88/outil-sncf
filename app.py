import streamlit as st
import requests
from datetime import datetime
import pandas as pd
import pydeck as pdk
import polyline
import time

# Remplace par ton propre jeton d'API
API_KEY = "Nls6MNAOPfShwP9wKokSoEQmqU7XNGuv"

# URL de base de l'API
BASE_URL = 'https://prim.iledefrance-mobilites.fr/marketplace'

# Personnalisation du bouton avec du CSS
st.markdown("""
    <style>
    .stButton > button {
        background-color: #dd1c30;  /* Couleur de fond personnalisée */
        color: white;  /* Couleur du texte */
        border-radius: 8px;  /* Coins arrondis */
        border: none;  /* Supprimer la bordure */
        transition: all 0.3s ease;  /* Transition douce */
    }
    .stButton > button:hover {
        background-color: #e64c50;  /* Couleur de fond éclaircie au survol */
        color: white;  /* Couleur du texte */
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);  /* Ombrage au survol */
        transform: scale(1.05);  /* Légère augmentation de la taille */
    }
    .stButton > button:active {
        background-color: #cc1b2f;  /* Couleur de fond foncée au clic */
        color: white !important;  /* Assure que la couleur du texte reste blanche */
    }
    .stButton > button:focus {
        background-color: #dd1c30;  /* Garder la même couleur au focus */
        color: white !important;  /* Assure que la couleur du texte reste blanche même après clic */
    }
    </style>
    """, unsafe_allow_html=True)

# Ajouter une image logo SNCF avec le titre
st.markdown(
    """
    <div style="display: flex; align-items: center;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/f/f4/Sncf-logo.svg/2560px-Sncf-logo.svg.png" width="100" height="auto" style="margin-right: 10px;">
        <h2>Calculateur d'itinéraire Ile-de-France</h2>
    </div>
    """, unsafe_allow_html=True)

# Fonction pour géocoder une adresse avec Nominatim
def geocode_address_nominatim(address):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
        "countrycodes": "fr"  # Limite les recherches à la France
    }
    headers = {
        "User-Agent": "MonApplication/1.0 (votre@email.com)"  # User-Agent personnalisé obligatoire
    }
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        if data:
            longitude = data[0]["lon"]
            latitude = data[0]["lat"]
            return f"{longitude};{latitude}"
        else:
            st.warning(f"Aucun résultat trouvé pour l'adresse : {address}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur lors du géocodage : {e}")
        return None


# Fonction pour récupérer un itinéraire via l'API Ile-de-France Mobilités
def get_journey(from_coords, to_coords):
    url = f'{BASE_URL}/v2/navitia/journeys'
    headers = {
        "apiKey": API_KEY
    }
    params = {
        "from": from_coords,
        "to": to_coords
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur lors de la récupération de l'itinéraire : {e}")
        return None

def display_journey_choices(journey_data):
    if "journeys" not in journey_data or not journey_data["journeys"]:
        st.warning("Aucun itinéraire trouvé.")
        return

    st.subheader("Choix d'itinéraires disponibles :")
    for idx, journey in enumerate(journey_data["journeys"]):
        departure_time = journey.get("departure_date_time", None)
        arrival_time = journey.get("arrival_date_time", None)
        if departure_time and arrival_time:
            departure_time = datetime.strptime(departure_time, "%Y%m%dT%H%M%S").strftime('%H:%M')
            arrival_time = datetime.strptime(arrival_time, "%Y%m%dT%H%M%S").strftime('%H:%M')
        else:
            departure_time, arrival_time = "Inconnu", "Inconnu"

        total_duration = journey.get("duration", 0)
        if total_duration >= 3600:
            hours = total_duration // 3600
            minutes = (total_duration % 3600) // 60
            duration_str = f"{hours} h {minutes:02d} min"
        else:
            duration_str = f"{total_duration // 60} min"

        co2_emission = journey.get("co2_emission", {}).get("value", None)
        co2_str = f"{round(co2_emission)} g" if co2_emission is not None else "Inconnu"

        fare = journey.get("fare", {}).get("total", {}).get("value", None)
        if fare is None:
            fare = 0
        fare_in_euros = float(fare) / 100
        fare_str = f"{fare_in_euros:.2f} €"

        expander_title = (
            f"🛤️ Itinéraire {idx + 1} | Départ : {departure_time} | Arrivée : {arrival_time} | "
            f"Durée : {duration_str} | CO₂ : {co2_str} | Prix : {fare_str}"
        )

        with st.expander(expander_title):
            for section in journey["sections"]:
                section_type = section["type"]

                if section_type == "street_network":
                    from_name = section.get("from", {}).get("name", "Point inconnu")
                    to_name = section.get("to", {}).get("name", "Point inconnu")
                    duration = section.get("duration", 0)
                    st.write(f"- 🚶‍♂️ Marche ({duration // 60} minutes) : {from_name} -> {to_name}")

                elif section_type == "public_transport":
                    from_name = section.get("from", {}).get("name", "Arrêt inconnu")
                    to_name = section.get("to", {}).get("name", "Arrêt inconnu")
                    mode = section.get("display_informations", {}).get("commercial_mode", "Transport")
                    line = section.get("display_informations", {}).get("label", "Ligne inconnue")
                    duration = section.get("duration", 0)
                    st.write(f"- 🚇 {mode} {line} ({duration // 60} minutes) : {from_name} -> {to_name}")

                elif section_type == "transfer":
                    duration = section.get("duration", 0)
                    st.write(f"- 🔄 Correspondance ({duration // 60} minutes)")

        st.markdown("---")


# Deuxième Programme : Calculateur d'itinéraires vélo et des stations Vélib

# Fonction pour décoder les géométries Google Polyline
def decode_polyline(polyline_str):
    decoded_points = [{"lat": lat, "lon": lon} for lat, lon in polyline.decode(polyline_str)]
    for point in decoded_points:
        point["lat"] /= 10
        point["lon"] /= 10
    return decoded_points

def separate_coordinates(coord_str):
    longitude, latitude = map(float, coord_str.split(";"))
    return longitude, latitude

def fetch_computed_routes(waypoints, bike_details):
    url = f'{BASE_URL}/computedroutes?geometry=true'
    data = {
        "waypoints": waypoints,
        "bikeDetails": bike_details,
        "transportModes": ["BIKE"]
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "apikey": API_KEY
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur lors de la requête API : {e}")
        return None

# Fonction pour obtenir les données de disponibilité des vélos et bornes
def get_station_status():
    url = f'{BASE_URL}/velib/station_status.json'
    headers = {
        'apiKey': API_KEY
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get("data", {}).get("stations", [])
    else:
        st.error(f"Erreur {response.status_code}: Impossible de récupérer les données.")
        return None
    
# Fonction pour obtenir les données vélib
def get_station_information():
    url = f'{BASE_URL}/velib/station_information.json'
    headers = {
        'apiKey': API_KEY
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("data", {}).get("stations", [])
    else:
        st.error(f"Erreur {response.status_code}: Impossible de récupérer les données.")
        return None
    
# Combiner les informations des stations et leurs statuts
def merge_station_data(station_info, station_status):
    info_df = pd.DataFrame(station_info)
    status_df = pd.DataFrame(station_status)
    # Fusionner les deux DataFrames sur "station_id"
    merged_data = pd.merge(info_df, status_df, on="station_id", how="inner")
    return merged_data



# Interface utilisateur avec Streamlit : Sélection de l'onglet
tabs = st.tabs(["🚉 Transport public", "🚲 Vélo"])

with tabs[0]:
    st.header("🚉 Transport public")
    departure_address = st.text_input("🏳️ Adresse de départ :", key="from_public")
    arrival_address = st.text_input("📍 Adresse d'arrivée :", key="to_public")

    if st.button("Calculer l'itinéraire", key="button_public"):
        if departure_address and arrival_address:
            st.info("Géocodage des adresses...")
            from_coords = geocode_address_nominatim(departure_address)
            time.sleep(1)
            to_coords = geocode_address_nominatim(arrival_address)

            if from_coords and to_coords:
                st.info("Récupération de l'itinéraire...")
                journey_data = get_journey(from_coords, to_coords)
                if journey_data:
                    display_journey_choices(journey_data)
        else:
            st.warning("Veuillez entrer les deux adresses.")

with tabs[1]:
    st.header("🚲 Vélo")
    departure_address = st.text_input("🏳️ Adresse de départ :", key="from_bike")
    arrival_address = st.text_input("📍 Adresse d'arrivée :", key="to_bike")
    e_bike = st.checkbox("⚡ Vélo électrique", value=False)

    # Obtenir les données vélib
    station_info = get_station_information()
    station_status = get_station_status()

    if not station_info or not station_status:
        st.warning("Impossible de récupérer les données des stations ou leurs statuts.")
    else:
        # Fusionner les données
        station_data = merge_station_data(station_info, station_status)

        # Ajouter une colonne avec des informations détaillées pour le tooltip
        def extract_bike_types(bike_types):
            """Extraire les vélos mécaniques et électriques depuis `num_bikes_available_types`."""
            mechanical = next((item.get("mechanical", 0) for item in bike_types if "mechanical" in item), 0)
            ebike = next((item.get("ebike", 0) for item in bike_types if "ebike" in item), 0)
            return mechanical, ebike

        station_data["mechanical_bikes"], station_data["ebike_bikes"] = zip(
            *station_data["num_bikes_available_types"].apply(extract_bike_types)
        )

        station_data["tooltip_info"] = (
            "<b>Nom:</b> " + station_data["name"] + "<br/>"
            "<b>Vélos disponibles:</b> " + station_data["num_bikes_available"].astype(str) + "<br/>"
            "<b>Types de vélos:</b> " +
            "Mécaniques: " + station_data["mechanical_bikes"].astype(str) + ", Électriques: " + station_data["ebike_bikes"].astype(str) + "<br/>"
            "<b>Places libres:</b> " + station_data["num_docks_available"].astype(str)
        )

    if st.button("Calculer l'itinéraire", key="button_bike"):
        if departure_address and arrival_address:
            st.info("Géocodage des adresses...")
            from_coords = geocode_address_nominatim(departure_address)
            # Séparer en longitude et latitude
            from_longitude, from_latitude = separate_coordinates(from_coords)
            time.sleep(1)
            to_coords = geocode_address_nominatim(arrival_address)
            # Séparer en longitude et latitude
            to_longitude, to_latitude = separate_coordinates(to_coords)

            waypoints = [
                {"latitude": from_latitude, "longitude": from_longitude, "title": departure_address},
                {"latitude": to_latitude, "longitude": to_longitude, "title": arrival_address}
            ]

            bike_details = {
                "eBike": e_bike
            }

            result = fetch_computed_routes(waypoints, bike_details)
            if result:
                st.success("Itinéraires récupérés avec succès.")

                # Affichage clair des résultats
                st.subheader("Choix d'itinéraires disponibles :")
                for idx, journey in enumerate(result):
                    # Extraction des informations générales
                    title = journey.get("title", "Itinéraire")
                    duration = journey.get("duration", 0)
                    departure_time = journey.get("estimatedDatetimeOfDeparture")
                    arrival_time = journey.get("estimatedDatetimeOfArrival")

                    # Conversion des durées et heures
                    duration_str = f"{duration // 60} min" if duration < 3600 else f"{duration // 3600} h {duration % 3600 // 60} min"
                    departure_time = datetime.fromisoformat(departure_time).strftime('%H:%M') if departure_time else "Inconnu"
                    arrival_time = datetime.fromisoformat(arrival_time).strftime('%H:%M') if arrival_time else "Inconnu"

                    # Détails des distances
                    distances = journey.get("distances", {})
                    total_distance = distances.get("total", 0)

                    # Titre de l'expander
                    expander_title = (
                        f"{title} | Départ : {departure_time} | Arrivée : {arrival_time} | Durée : {duration_str} | Distance : {total_distance / 1000:.1f} km"
                    )

                    with st.expander(expander_title):
                        # Visualisation de l'itinéraire sur une carte
                        st.write("#### Carte de l'itinéraire")
                        
                        sections = journey.get("sections", [])
                        for section in sections:
                            geometry = section.get("geometry")
                            if geometry:  # Si une géométrie est fournie
                                path = decode_polyline(geometry)  # Décoder la polyligne
                                map_data = pd.DataFrame(path)  # Créer un DataFrame pour pydeck
                                
                                # Vérification des colonnes lat et lon
                                if 'lat' not in map_data.columns or 'lon' not in map_data.columns:
                                    st.write("Les coordonnées n'ont pas les bonnes colonnes 'lat' et 'lon'.")
                                else:
                                    midpoint = map_data.mean().to_dict()

                                    # Formatage des données pour PathLayer
                                    path_data = [{'path': list(zip(map_data['lon'], map_data['lat']))}]

                                    st.pydeck_chart(pdk.Deck(
                                        map_style="mapbox://styles/mapbox/streets-v11",
                                        initial_view_state=pdk.ViewState(
                                            latitude=midpoint["lat"],
                                            longitude=midpoint["lon"],
                                            zoom=12
                                        ),
                                        layers=[
                                            # Couche des stations Vélib'
                                            pdk.Layer(
                                                "ScatterplotLayer",
                                                data=station_data,
                                                get_position="[lon, lat]",
                                                get_radius=25,
                                                get_fill_color=[0, 128, 0],  # Couleur des stations
                                                pickable=True,
                                                auto_highlight=True  # Pour mettre en surbrillance au survol
                                                
                                            ),
                                            # Couche des itinéraires
                                            pdk.Layer(
                                                "PathLayer",
                                                data=path_data,
                                                get_path="path",  # Chaque élément "path" est une liste de [lon, lat]
                                                get_width=10,
                                                get_color=[0, 0, 255],
                                                pickable=True
                                            )
                                        ],
                                        tooltip={
                                            "html": "{tooltip_info}",
                                            "style": {"color": "white"}
                                            }
                                    ))
                            else:
                                st.write("Aucune géométrie disponible pour cette section.")

                    st.markdown("---")
            else:
                st.error("Aucun itinéraire disponible.")
        else:
            st.warning("Veuillez entrer les deux adresses.")

