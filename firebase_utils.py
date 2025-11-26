# firebase_utils.py

import firebase_admin
from firebase_admin import credentials, firestore
import datetime

# 🔐 Initialize Firebase (ensure the JSON file is in the same directory)
def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate("erss001-firebase-adminsdk-fbsvc-217b1ef597.json")  # Replace with your actual file name
        firebase_admin.initialize_app(cred)

# 🗃️ Save emergency dispatch data
def save_dispatch_data(case_info, dispatch_services, first_aid):
    db = firestore.client()
    collection = db.collection("dispatch_logs")

    doc_data = {
        "timestamp": datetime.datetime.now(),
        "emergency_type": case_info["emergency_type"],
        "location": case_info["location"],
        "fields": case_info["category_fields"],
        "services_dispatched": dispatch_services,
        "first_aid": first_aid
    }

    collection.add(doc_data)
    print("✅ Emergency record saved to Firebase.")
