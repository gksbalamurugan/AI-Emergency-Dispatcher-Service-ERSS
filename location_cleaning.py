import re

def clean_location(raw_location):
    # List of vague prefixes or phrases to remove
    stop_words = [
        r"\bnear\b", r"\bat\b", r"\bin\b", r"\baround\b", r"\bbehind\b", r"\bfront of\b", r"\bmy house\b", r"\bmy home\b",
        r"\bjust\b", r"\bon\b", r"\bside of\b", r"\bbeside\b", r"\bnext to\b", r"\bopposite to\b"
    ]

    # Remove stop words
    cleaned = raw_location.lower()
    for phrase in stop_words:
        cleaned = re.sub(phrase, '', cleaned)

    # Remove extra spaces and return
    return cleaned.strip().title()
