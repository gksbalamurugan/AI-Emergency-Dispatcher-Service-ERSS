import requests
import json
from gpt_parser_v5 import extract_fields_from_text, classify_emergency_type
from firebase_utils import init_firebase, save_dispatch_data
from vehicle_dispatcher import load_vehicle_data, find_nearest_vehicle
from location_cleaning import clean_location


API_KEY = "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"  # your real OpenRouter API key
MODEL = "mistralai/mistral-7b-instruct"

EMERGENCY_CATEGORIES = {
    "fire": {"cause": None, "trapped": None, "injuries": None, "flammables": None, "severity": None},
    "crash": {"vehicles": None, "victims": None, "trapped": None, "injuries": None, "fuel_leak": None, "traffic_block": None},
    "medical": {"conscious": None, "known_person": None, "medical_history": None, "cpr_possible": None, "bleeding": None},
    "assault": {"attackers": None, "injuries": None, "weapon": None, "description": None, "attacker_location": None},
    "harassment": {"people_involved": None, "safe_now": None, "can_go_police": None},
    "wildlife": {"animal_type": None, "inside_home": None, "injured": None, "still_visible": None, "safety_status": None},
    "other": {"situation": None, "injuries": None, "danger": None}
}

case_info = {
    "emergency_type": None,
    "location": None,
    "category_fields": {}
}

def geocode_location(location_str):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": location_str,
        "format": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": "AI-Dispatcher/1.0 (avglifemy@gmail.com)"  # Optional but recommended
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        if data:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            return {"latitude": lat, "longitude": lon}
        else:
            return None
    except Exception as e:
        print("🌐 Geocoding error:", e)
        return None

def ask_ai_question(filled_fields, missing_key, category):
    filled_text = "\n".join([f"- {k}: {v}" for k, v in filled_fields.items() if v])
    prompt = (
        f"You are a calm, professional emergency dispatcher.\n"
        f"Emergency Type: {category}\n"
        f"Info collected so far:\n{filled_text}\n"
        f"Please phrase a clear and concise dispatcher question to collect: '{missing_key}' only.\n"
        f"Ask only one question at a time."
    )
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {"model": MODEL, "messages": [{"role": "system", "content": prompt}]}

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        return response.json()['choices'][0]['message']['content']
    except:
        return "Could you clarify that?"

def generate_first_aid_from_ai(emergency_type, fields):
    # Convert dict injuries to string if needed
    if isinstance(fields.get("injuries"), dict):
        fields["injuries"] = ", ".join([f"{k}: {v}" for k, v in fields["injuries"].items()])

    prompt = (
        f"You are a professional emergency medical assistant AI.\n"
        f"A dispatcher received a report of a '{emergency_type}' emergency.\n"
        f"The following details were shared:\n"
        f"{json.dumps(fields, indent=2)}\n\n"
        f"Based on this, give short and clear first aid instructions the caller can follow until responders arrive. "
        f"Respond in 4–5 bullet points. Be direct. Do not mention calling emergency services, it's already done."
    )

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {"model": MODEL, "messages": [{"role": "user", "content": prompt}]}

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        return response.json()['choices'][0]['message']['content']
    except:
        return "⚠️ Unable to fetch AI tips right now."

def save_dispatch_data(case_info, dispatch_services, first_aid, transcript_lines, vehicle_ids):
    from firebase_admin import firestore
    db = firestore.client()

    doc = {
        "emergency_type": case_info["emergency_type"],
        "location": case_info["location"],
        "fields": case_info["category_fields"],
        "services_dispatched": dispatch_services,
        "vehicles_dispatched": vehicle_ids,  # 🚨 NEW LINE
        "first_aid": first_aid,
        "conversation": transcript_lines,
        "timestamp": firestore.SERVER_TIMESTAMP
    }

    db.collection("dispatch_logs").add(doc)
    print("✅ Emergency record saved to Firebase.")


def run_dispatcher():
    conversation_log = []
    initial_greeting = "🚨 1-1-2 Emergency Services. How can I help you?\n"
    print(initial_greeting)
    conversation_log.append(initial_greeting.strip())
    first_input = input("Caller: ").lower()
    conversation_log.append(f"Caller: {first_input}")
    # Detect emergency type via GPT
    case_info["emergency_type"] = classify_emergency_type(first_input)
    category_fields = EMERGENCY_CATEGORIES[case_info["emergency_type"]].copy()
    case_info["category_fields"] = category_fields

    # Parse initial input
    parsed_initial = extract_fields_from_text(first_input, list(category_fields.keys()) + ["location"])
    for key in category_fields:
        if parsed_initial.get(key):
            category_fields[key] = parsed_initial[key]

    # Parse location
    if parsed_initial.get("location"):
        case_info["location"] = parsed_initial["location"]
    else:
        case_info["location"] = input("911 Operator: Please confirm the full location or nearest landmark.\nCaller: ")
        conversation_log.append(f"911 Operator: Please confirm the full location or nearest landmark.\nCaller: ")
        conversation_log.append(f"Caller: {case_info['location']}")
 
    # Begin structured questioning
    while True:
        fields = case_info["category_fields"]
        missing = [k for k, v in fields.items() if v is None or str(v).strip().lower() in ["", "unknown", "null", "none"]]
        if not missing:
            break

        next_field = missing[0]
        question = ask_ai_question(fields, next_field, case_info["emergency_type"])
        conversation_log.append(f"911 Operator: {question}")
        user_response = input(f"911 Operator: {question}\nCaller: ")
        conversation_log.append(f"Caller: {user_response}")
        parsed = extract_fields_from_text(user_response, [next_field])
        fields[next_field] = parsed.get(next_field, user_response.strip())

    # ✅ Dispatch Summary
    print("\n✅ Dispatching Emergency Services:")
    conversation_log.append("✅ Dispatching Emergency Services:")
    print(f"- 📍 Location: {case_info['location']}")
    conversation_log.append(f"- 📍 Location: {case_info['location']}")
    print(f"- 🚨 Emergency Type: {case_info['emergency_type'].capitalize()}")
    conversation_log.append(f"- 🚨 Emergency Type: {case_info['emergency_type'].capitalize()}")
    
    for key, val in case_info['category_fields'].items():
       line = f"  • {key.replace('_', ' ').capitalize()}: {val}"
       print(line)
       conversation_log.append(line)


    # Step: Get Lat/Lon from location
    raw_location=case_info["location"]
    cleaned_location = clean_location(raw_location)
    case_info["location"] = cleaned_location
    location_coords = geocode_location(case_info["location"])
    if location_coords:
        lat = location_coords['latitude']
        lon = location_coords['longitude']
        print(f"📍 Parsed Coordinates: {lat}, {lon}")
        conversation_log.append(f"📍 Parsed Coordinates: {lat}, {lon}")
        case_info["coordinates"] = location_coords
    else:
        print("⚠️ Unable to geocode location. Proceeding without coordinates.")
        conversation_log.append("⚠️ Unable to geocode location. Proceeding without coordinates.")
        case_info["coordinates"] = None


    # 🚨 Service assignment
    etype = case_info["emergency_type"]
    dispatch_services = []
    if etype == "fire":
        dispatch_services = ["firetruck", "ambulance"]
    elif etype == "crash":
        dispatch_services = ["ambulance", "police"]
    elif etype == "medical":
        dispatch_services = ["ambulance"]
    elif etype in ["assault", "harassment"]:
        dispatch_services = ["police"]
    elif etype == "wildlife":
        dispatch_services = ["animal control", "firetruck"]
  
    if not case_info["coordinates"]:
      print("⚠️ Cannot assign vehicles without coordinates.")
      conversation_log.append("⚠️ Cannot assign vehicles without coordinates.")
      assigned_units = []
    else:
        caller_coords = [case_info["coordinates"]["latitude"], case_info["coordinates"]["longitude"]]
        vehicle_data = load_vehicle_data()
        assigned_units = []
        for service in dispatch_services:
          vehicle_id = find_nearest_vehicle(service, caller_coords, vehicle_data)
          if vehicle_id:
            assigned_units.append(vehicle_id)
        if assigned_units:
          print(f"🚓 Assigned Units: {', '.join(assigned_units)}")
          conversation_log.append(f"🚓 Assigned Units: {', '.join(assigned_units)}")
        else:
          print("⚠️ No suitable units found in proximity.")
          conversation_log.append("⚠️ No suitable units found in proximity.")

    print(f"- 🚑 Services Dispatched: {', '.join(dispatch_services).capitalize()}")
    conversation_log.append(f"- 🚑 Services Dispatched: {', '.join(dispatch_services).capitalize()}")
    print("🕊️ Stay calm. Help is on the way. We'll stay with you until responders arrive.\n")
    conversation_log.append("🕊️ Stay calm. Help is on the way. We'll stay with you until responders arrive.")

    # 🤖 First Aid Suggestion
    print("🤖 AI-Based First Aid Suggestions:\n")
    first_aid = generate_first_aid_from_ai(etype, category_fields)
    print(first_aid)
    conversation_log.append("🤖 AI-Based First Aid Suggestions:")
    conversation_log.append(f"911 Operator: {first_aid}")
    
    #Firebase integration
    save_dispatch_data(case_info, dispatch_services, first_aid, conversation_log, assigned_units)


if __name__ == "__main__":
     init_firebase()  # 👈 Initialize Firebase
     run_dispatcher()
