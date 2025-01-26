import streamlit as st
import requests
from datetime import datetime
import pandas as pd
import pydeck as pdk
import polyline

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


# Fonction pour récupérer les itinéraires
def fetch_computed_routes(api_key, waypoints, bike_details):
    """Envoie une requête à l'API Geovelo pour récupérer des itinéraires."""
    url = "https://prim.iledefrance-mobilites.fr/marketplace/computedroutes?geometry=true"
    data = {
        "waypoints": waypoints,
        "bikeDetails": bike_details,
        "transportModes": ["BIKE"]
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "apikey": api_key
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur lors de la requête API : {e}")
        return None

# Application Streamlit
st.title("Calculateur d'itinéraires vélo - Geovelo")

# Entrée utilisateur
api_key = st.text_input("Clé API Geovelo", type="password")

st.write("### Points de passage")
start_lat = st.number_input("Latitude de départ", value=48.872096, format="%.6f")
start_lon = st.number_input("Longitude de départ", value=2.33261, format="%.6f")
start_title = st.text_input("Titre du point de départ", value="Métro-Opéra, Paris")

end_lat = st.number_input("Latitude d'arrivée", value=48.84059, format="%.6f")
end_lon = st.number_input("Longitude d'arrivée", value=2.32134, format="%.6f")
end_title = st.text_input("Titre du point d'arrivée", value="Gare Montparnasse, Paris")

st.write("### Détails du vélo")
profile = st.selectbox("Profil", ["MEDIAN", "FAST", "SLOW"], index=0)
bike_type = st.selectbox("Type de vélo", ["TRADITIONAL", "ELECTRIC"], index=0)
average_speed = st.number_input("Vitesse moyenne (km/h)", value=16, step=1)
e_bike = st.checkbox("Vélo électrique", value=False)

if st.button("Calculer l'itinéraire"):
    if api_key:
        waypoints = [
            {"latitude": start_lat, "longitude": start_lon, "title": start_title},
            {"latitude": end_lat, "longitude": end_lon, "title": end_title}
        ]

        bike_details = {
            "profile": profile,
            "bikeType": bike_type,
            "averageSpeed": average_speed,
            "eBike": e_bike
        }

        result = fetch_computed_routes(api_key, waypoints, bike_details)
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
                    st.write(f"### Détails de l'itinéraire")
                    st.write(f"- **Distance totale :** {total_distance / 1000:.1f} km")

                    # Visualisation de l'itinéraire sur une carte
                    st.write("#### Carte de l'itinéraire")
                    sections = journey.get("sections", [])
                    for section in sections:
                        geometry = section.get("geometry")
                        if geometry:  # Si une géométrie est fournie
                            path = decode_polyline(geometry)  # Décoder la polyligne
                            st.write("Coordonnées décodées :", path)
                            map_data = pd.DataFrame(path)  # Créer un DataFrame pour pydeck
                            
                            # Vérification des colonnes lat et lon
                            if 'lat' not in map_data.columns or 'lon' not in map_data.columns:
                                st.write("Les coordonnées n'ont pas les bonnes colonnes 'lat' et 'lon'.")
                            else:
                                st.write("Coordonnées décodées (DataFrame) :", map_data)
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
                                        pdk.Layer(
                                            "PathLayer",
                                            data=path_data,
                                            get_path="path",  # Chaque élément "path" est une liste de [lon, lat]
                                            get_width=4,
                                            get_color=[0, 0, 255],
                                            pickable=True,
                                        )
                                    ]
                                ))
                        else:
                            st.write("Aucune géométrie disponible pour cette section.")

            st.markdown("---")
        else:
            st.error("Aucun itinéraire disponible.")
    else:
        st.error("Veuillez fournir une clé API valide.")
