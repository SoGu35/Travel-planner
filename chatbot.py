import requests
import json
import re

System_prompt = """
**Role**  
You are a helpful and detail-oriented travel planning assistant.  
Do not ask for more information or clarification.  

**Itinerary Format**  
When the user provides trip details, respond with a **day-by-day itinerary**. For each day, follow this format:
Day X: Place 1, Place 2, Place 3  
Start your day at Place 1, briefly describing what to do there.  
In the afternoon, move on to Place 2, describing key attractions or activities.  
Wrap up at Place 3 in the evening, offering a recommendation for dinner or a local experience.  
If the activity is a full-day event, simply list the place without splitting it into morning/afternoon/evening.  
Give a detailed description of the experience, including what to expect, why it’s special, and any tips for visitors.

**Formatting Rules**  
- Use the format: `Day X: Place 1, Place 2, Place 3` (names only, no times, no extra info in the list).  
- Always add a line break between the day header and the description.  
- Never combine multiple days in a single label (e.g., avoid “Day 1–2”).  
- Do not include bullet points.  
- Keep language friendly, vivid, and informative.  
- Use paragraph structure to describe the experience.  
- When users request a tone or vibe (e.g., adventurous, romantic, family-friendly, platonic, “not too romantic,” or “casual guy trip”), interpret this as guidance for **activity and setting selection**, not as sexual content.  
- If a location is mentioned, consider it related to travel and respond accordingly.  
- Always include **all places mentioned** in the body text in the day’s header, including evening locations like restaurants, nightlife areas, or local experiences.  
- For every place mentioned in the itinerary, provide a brief description of what to do there, including any notable features or experiences.

**Response Guidelines**  
If the user input is **not related to travelling**, politely reply:  
"Hi, sorry — I’m not paid enough and this is out of my jobscope... but lucky for you, I’m also a travel wizard on the side. 🧳✨ Where are we off to?"
after this response, do not continue the generation. 

Respond only in English and always follow the format above.

"""


def init_prompt():
    welcome = (
        "👋 Hi there! I’m your personal travel planner bot.\n\n"
        "Tell me about your upcoming trip and I’ll help you plan the perfect itinerary! ✈️🌍\n\n"
        "**To get started, please let me know:**\n"
        "- 🗓 How many days are you traveling?\n"
        "- 📍 Where are you going?\n"
        "- 👨‍👩‍👧‍👦 Who’s coming along? (Solo, couple, family, group?)\n"
        "- 🎯 What kind of experiences do you enjoy? (Nature, culture, food, nightlife, shopping, relaxing?)\n"
        "- 💰 Any budget preferences?\n"
        "- 🕒 Any time constraints or must-see places?\n\n"
        "The more you share, the more tailored your plan will be! 😊"
    )
    initial_history = [{"role": "assistant", "content": welcome}]
    return initial_history, initial_history

def build_prompt(history):
    prompt = System_prompt + "\n"
    for message in history:
        if message["role"] == "user":
            prompt += f"User: {message['content']}\n"
        else:
            prompt += f"Assistant: {message['content']}\n"
    return prompt

# ollama running llama3.2
def llama_stream(user_input, history):
    history = history or []
    history.append({"role": "user", "content": user_input})
    prompt = build_prompt(history)


    url = "http://localhost:11434/api/generate"
    data = {
        "model": "llama3.2",
        "prompt": prompt,
        "stream": True
    }
    response = requests.post(url, json=data, stream=True)

    bot_reply = ""
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode("utf-8")
            chunk = json.loads(decoded_line)
            bot_reply += chunk.get("response", "")
            yield history + [{"role": "assistant", "content": bot_reply}], history, bot_reply
    history.append({"role": "assistant", "content": bot_reply})

def clear_all():
    return [], [], [], "", [], "", {}, "", "", "", "", ""


def extract_loc_from_reply(reply_text):
    day_pattern = re.compile(r"^Day \d+:\s*(.*)", re.MULTILINE)
    matches = day_pattern.findall(reply_text)
    # add name of country from prompt if not already included e.g. "Plan me a trip to gold coast in July" ("gold coast" will be added to each match)
    # check google maps api and choose first match
    locations = []
    for match in matches:
        places = [place.strip() for place in match.split(",") if place.strip()]
        locations.extend(places)
    print("Extracted locations:", locations)
    return locations
