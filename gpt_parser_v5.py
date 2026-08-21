import requests
import json

API_KEY = ""
API_URL = ""
MODEL = ""

def extract_fields_from_text(text, expected_fields):
    prompt = (
        "You are an AI emergency dispatcher assistant. Extract the following fields in JSON format:\n"
        f"{', '.join(expected_fields)}\n\n"
        "Rules:\n"
        "- Use 'yes' or 'no' for boolean fields.\n"
        "- Use brief descriptions for others.\n"
        "- If location is unclear like my house or my room, any generic word, use null\n"
        "- if yourn't able to fetch exact location leave it has null *do not parse anything like callers house any other unclear location\n"
        "- If unclear, use null.\n"
        "- Return only a valid JSON dictionary.\n\n"
        f"Caller message: \"{text}\""
    )

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data)
        content = response.json()['choices'][0]['message']['content'].strip()

        # Remove markdown formatting if present
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()

        # Safe JSON extraction
        if "{" in content:
            content = content[:content.rindex("}")+1]

        parsed = json.loads(content)

        # Normalize fields
        for key in parsed:
            val = str(parsed[key]).strip().lower()
            if val in ["unknown", "null", "none", ""]:
                parsed[key] = None
            elif val in ["no", "false"]:
                parsed[key] = "no"
            elif val in ["yes", "true"]:
                parsed[key] = "yes"
            else:
                parsed[key] = parsed[key]
        return parsed

    except Exception as e:
        print("❌ Parsing error or invalid JSON:\n")
        print(content)
        return {}

def classify_emergency_type(text):
    text_lower = text.lower()

    # ✅ Quick keyword-based pre-check for known categories
    crash_keywords = ["collision", "collided", "crash", "accident", "hit by car", "car hit", "vehicle hit", "car accident", "vehicle crash", "vehicles collided", "head-on crash", "road accident", "bike accident", "truck hit"]
    fire_keywords = ["fire", "burning", "explosion", "blast"]
    assault_keywords = ["attacked", "beaten", "assault", "hit by person", "stabbed", "shot"]
    harassment_keywords = ["stalked", "followed", "harassed", "threatened"]
    wildlife_keywords = ["animal", "snake", "leopard", "wild boar", "monkey", "dog attack"]

    # Check for clear crash
    if any(keyword in text_lower for keyword in crash_keywords):
        return "crash"
    elif any(keyword in text_lower for keyword in fire_keywords):
        return "fire"
    elif any(keyword in text_lower for keyword in assault_keywords):
        return "assault"
    elif any(keyword in text_lower for keyword in harassment_keywords):
        return "harassment"
    elif any(keyword in text_lower for keyword in wildlife_keywords):
        return "wildlife"

    # ✅ Fallback to GPT model classification
    prompt = (
        "You are a highly accurate emergency classification system for a 1-1-2 dispatcher in India.\n"
        "Select ONE emergency type from the list below based on the given message:\n"
        "- fire\n"
        "- crash\n"
        "- medical\n"
        "- assault\n"
        "- harassment\n"
        "- wildlife\n"
        "- other\n\n"
        "Guidelines:\n"
        "- If there's any mention of vehicle collision, cars collided, road accident, or car crash, choose 'crash'.\n"
        "- If it involves a medical issue AND a crash together, still choose 'crash'.\n"
        "- If someone is unconscious or fainted WITHOUT any crash, choose 'medical'.\n"
        "- If fire or explosion, choose 'fire'.\n"
        "- If someone is attacked or physically harmed by another person, choose 'assault'.\n"
        "- If being stalked, followed, or threatened, choose 'harassment'.\n"
        "- If the emergency involves an animal causing harm or fear, choose 'wildlife'.\n"
        "- Otherwise, only after careful consideration, choose 'other'.\n\n"
        f"Emergency message: \"{text}\"\n"
        "Category:"
    )

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data)
        category = response.json()['choices'][0]['message']['content'].strip().lower()
        if category in ["fire", "crash", "medical", "assault", "harassment", "wildlife", "other"]:
            print(f"📝 GPT classified as '{category}' for: {text}")  # ✅ Optional for debugging
            return category
        print(f"⚠️ GPT gave unknown category '{category}', defaulting to 'other'")
        return "other"
    except Exception as e:
        print(f"⚠️ GPT classification failed ({e}), defaulting to 'other'")
        return "other"

