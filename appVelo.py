import streamlit as st
import requests
from datetime import datetime

# Fonction pour récupérer les itinéraires
def fetch_computed_routes(api_key, waypoints, bike_details):
    """Envoie une requête à l'API Geovelo pour récupérer des itinéraires."""
    url = "https://prim.iledefrance-mobilites.fr/marketplace/computedroutes"
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
                recommended_roads = distances.get("recommendedRoads", 0)
                discouraged_roads = distances.get("discouragedRoads", 0)

                # Titre de l'expander
                expander_title = (
                    f"{title} | Départ : {departure_time} | Arrivée : {arrival_time} | Durée : {duration_str} | Distance : {total_distance / 1000:.1f} km"
                )

                with st.expander(expander_title):
                    st.write(f"### Détails de l'itinéraire")
                    st.write(f"- **Distance totale :** {total_distance / 1000:.1f} km")
                    st.write(f"- **Routes recommandées :** {recommended_roads / 1000:.1f} km")
                    st.write(f"- **Routes déconseillées :** {discouraged_roads / 1000:.1f} km")

                    section = journey.get("sections", [])[0]
                    details = section.get("details", {})
                    direction = details.get("direction", "N/A")
                    vertical_gain = details.get("verticalGain", 0)
                    vertical_loss = details.get("verticalLoss", 0)

                    st.write(f"- **Direction principale :** {direction}")
                    st.write(f"- **Gain d'altitude :** {vertical_gain} m")
                    st.write(f"- **Perte d'altitude :** {vertical_loss} m")

                    st.write("#### Points de passage")
                    for wp in section.get("waypoints", []):
                        st.write(f"- {wp.get('title', 'Point inconnu')} ({wp.get('latitude')}, {wp.get('longitude')})")

            st.markdown("---")
        else:
            st.error("Aucun itinéraire disponible.")
    else:
        st.error("Veuillez fournir une clé API valide.")
