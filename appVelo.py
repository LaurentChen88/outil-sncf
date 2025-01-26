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


# Fonction pour décoder les géométries Google Polyline
def decode_polyline(polyline_str):
    """
    Décoder une chaîne de géométrie Google Polyline en une liste de coordonnées,
    avec correction du décalage de la virgule des latitudes.
    """
    decoded_points = [{"lat": lat, "lon": lon} for lat, lon in polyline.decode(polyline_str)]
    
    # Vérification et ajustement des latitudes aberrantes
    for point in decoded_points:
        point["lat"] /= 10  # Décaler la virgule
        point["lon"] /= 10  # Décaler la virgule
    
    return decoded_points

def separate_coordinates(coord_str):
    """
    Sépare une chaîne de coordonnées au format 'longitude;latitude' en deux valeurs
    flottantes représentant la longitude et la latitude.
    
    Args:
    - coord_str (str): La chaîne contenant la longitude et la latitude séparées par ';'.
    
    Returns:
    - tuple: Un tuple contenant la longitude et la latitude en tant que nombres flottants.
    """
    longitude, latitude = map(float, coord_str.split(";"))
    return longitude, latitude



# Fonction pour récupérer les itinéraires
def fetch_computed_routes(waypoints, bike_details):
    """Envoie une requête à l'API Geovelo pour récupérer des itinéraires."""
    url =  f'{BASE_URL}/computedroutes?geometry=true'
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

# Fonction pour obtenir les informations sur les stations (localisation, caractéristiques)
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



# Application Streamlit
st.title("🚲 Calculateur d'itinéraires vélo et des stations Vélib")

departure_address = st.text_input("🏳️ Adresse de départ :")
arrival_address = st.text_input("📍 Adresse d'arrivée :")
e_bike = st.checkbox("⚡ Vélo électrique", value=False)

if st.button("Calculer l'itinéraire"):
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



