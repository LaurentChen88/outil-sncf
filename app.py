import streamlit as st
import requests
from datetime import datetime
import folium
from streamlit_folium import st_folium
from folium.plugins import FeatureGroupSubGroup

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
    url = "https://prim.iledefrance-mobilites.fr/marketplace/v2/navitia/journeys"
    headers = {
        "apiKey": "YISw3BZQz6Jp328r5JIAerXb8KbftqEc"  # Remplacez par votre clé IDFM valide
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

# Fonction pour afficher les trajets avec une carte et des options détaillées
def display_journey_choices(journey_data):
    if "journeys" not in journey_data or not journey_data["journeys"]:
        st.warning("Aucun itinéraire trouvé.")
        return

    st.subheader("Choix d'itinéraires disponibles :")
    for idx, journey in enumerate(journey_data["journeys"]):
        # Conversion des heures de départ et d'arrivée
        departure_time = journey.get("departure_date_time", None)
        arrival_time = journey.get("arrival_date_time", None)
        if departure_time and arrival_time:
            departure_time = datetime.strptime(departure_time, "%Y%m%dT%H%M%S").strftime('%H:%M')
            arrival_time = datetime.strptime(arrival_time, "%Y%m%dT%H%M%S").strftime('%H:%M')
        else:
            departure_time, arrival_time = "Inconnu", "Inconnu"

        # Durée totale
        total_duration = journey.get("duration", 0)
        if total_duration >= 3600:
            hours = total_duration // 3600
            minutes = (total_duration % 3600) // 60
            duration_str = f"{hours} h {minutes:02d} min"
        else:
            duration_str = f"{total_duration // 60} min"

        # Émissions de CO₂
        co2_emission = journey.get("co2_emission", {}).get("value", None)
        co2_str = f"{round(co2_emission)} g" if co2_emission is not None else "Inconnu"

        # Prix estimé
        fare = journey.get("fare", {}).get("total", {}).get("value", None)
        if fare is None:
            fare = 0
        fare_in_euros = float(fare) / 100  # Conversion de centimes en euros
        fare_str = f"{fare_in_euros:.2f} €"

        # En-tête de l'expander
        expander_title = (
            f"🛤️ Itinéraire {idx + 1} | Départ : {departure_time} | Arrivée : {arrival_time} | "
            f"Durée : {duration_str} | CO₂ : {co2_str} | Prix : {fare_str}"
        )

        # Détails des sections dans un expander
        with st.expander(expander_title):
            st.markdown("### Détails des étapes :")
            map_center = None
            journey_map = folium.Map(zoom_start=12)

            # Liste des coordonnées pour ajuster le zoom
            all_coords = []

            for section in journey["sections"]:
                section_type = section["type"]
                mode = section.get("mode", "Inconnu")
                duration = section.get("duration", 0) // 60  # Convertir en minutes
                description = section.get("display_informations", {}).get("label", "Pas d'information")
                st.write(f"- **{section_type.capitalize()}** : {description} ({duration} min)")

                # Coordonnées pour la carte
                from_coords = section.get("from", {}).get("stop_point", {}).get("coord", None)
                to_coords = section.get("to", {}).get("stop_point", {}).get("coord", None)

                if from_coords and to_coords:
                    from_lat, from_lon = float(from_coords["lat"]), float(from_coords["lon"])
                    to_lat, to_lon = float(to_coords["lat"]), float(to_coords["lon"])

                    # Ajouter les coordonnées pour ajuster le zoom
                    all_coords.extend([(from_lat, from_lon), (to_lat, to_lon)])

                    # Ligne colorée pour chaque section
                    color = "blue" if section_type == "public_transport" else "green"
                    folium.PolyLine(
                        [(from_lat, from_lon), (to_lat, to_lon)],
                        color=color,
                        weight=5,
                        opacity=0.8
                    ).add_to(journey_map)

                    # Points de départ et d'arrivée
                    if not map_center:
                        map_center = [from_lat, from_lon]
                        folium.Marker([from_lat, from_lon], popup="Départ", icon=folium.Icon(color="green")).add_to(journey_map)
                    folium.Marker([to_lat, to_lon], popup="Arrivée", icon=folium.Icon(color="red")).add_to(journey_map)

            # Ajustement automatique du zoom
            if all_coords:
                journey_map.fit_bounds(all_coords)

            # Affichage de la carte
            st_folium(journey_map, width=700, height=400)

        st.markdown("---")

# Application Streamlit
st.title("Calculateur d'itinéraire Ile-de-France")
st.write("Entrez une adresse de départ et une adresse d'arrivée pour calculer un itinéraire.")

# Initialisation de l'état
if "journey_data" not in st.session_state:
    st.session_state["journey_data"] = None

# Entrée utilisateur
departure_address = st.text_input("Adresse de départ :")
arrival_address = st.text_input("Adresse d'arrivée :")

if st.button("Calculer l'itinéraire"):
    if departure_address and arrival_address:
        st.info("Géocodage des adresses...")
        from_coords = geocode_address_nominatim(departure_address)
        to_coords = geocode_address_nominatim(arrival_address)

        if from_coords and to_coords:
            st.info("Récupération de l'itinéraire...")
            journey_data = get_journey(from_coords, to_coords)
            st.session_state["journey_data"] = journey_data
        else:
            st.error("Impossible de récupérer les coordonnées. Vérifiez vos adresses.")
    else:
        st.warning("Veuillez entrer les deux adresses.")

# Affichage des résultats
if st.session_state["journey_data"]:
    display_journey_choices(st.session_state["journey_data"])

