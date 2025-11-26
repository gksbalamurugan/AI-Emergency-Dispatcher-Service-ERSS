import math
import json

def haversine(lat1, lon1, lat2, lon2):
    """Calculate Haversine distance (in km) between two coordinates."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_vehicle_data(filepath="vehicles.geojson"):
    """Load vehicles from a GeoJSON file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("features", [])
    except Exception as e:
        print(f"❌ Error loading vehicle data: {e}")
        return []


def find_nearest_vehicle(service_type, caller_coords, vehicle_data):
    """Find the nearest vehicle of a specific type to the caller."""
    nearest_vehicle = None
    min_distance = float("inf")

    for vehicle in vehicle_data:
        props = vehicle.get("properties", {})
        coords = vehicle.get("geometry", {}).get("coordinates", [])
        if not coords or props.get("type", "").lower() != service_type.lower():
            continue
        try:
            distance = haversine(caller_coords[0], caller_coords[1], coords[1], coords[0])
            if distance < min_distance:
                min_distance = distance
                nearest_vehicle = props.get("id")
        except Exception:
            continue

    return nearest_vehicle
