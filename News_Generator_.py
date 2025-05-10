import streamlit as st
import os
import requests
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from gtts import gTTS
import base64

import firebase_admin
from firebase_admin import credentials, firestore

# environment variables
load_dotenv()
google_api_key = os.getenv("GOOGLE_GEMINI_API")
unsplash_access_key = os.getenv("UNSPLASH_ACCESS_KEY")

# Firebase setup
cred = credentials.Certificate(r"C:\Users\pragy\Downloads\news-generator-e52c5-firebase-adminsdk-fbsvc-b1e2e3c37c.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

llm2 = ChatGoogleGenerativeAI(
    model="models/gemini-1.5-flash-latest",
    google_api_key=google_api_key,
    system_message=(
        "You are an AI news reporter. Provide short, structured news articles "
        "with factual and concise reporting. Avoid templates or placeholders."
    )
)

def is_valid_news_topic(topic):
    invalid_keywords = ["who", "what", "when", "where", "why", "how", "define", "explain", "solve", "meaning"]
    return not any(word in topic.lower() for word in invalid_keywords)

def fetch_unsplash_images(query, count=5):
    urls = []
    for _ in range(count):
        url = f"https://api.unsplash.com/photos/random?query={query}&client_id={unsplash_access_key}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            urls.append(data["urls"]["regular"])
    return urls

def generate_audio(text, filename):
    if not text.strip():
        text = "Sorry, no news details are available at the moment."
    tts = gTTS(text, lang="en")
    tts.save(filename)
    with open(filename, "rb") as f:
        audio_bytes = f.read()
    return base64.b64encode(audio_bytes).decode()

def fetch_news_from_gemini(topic):
    base_prompt = f"""Generate a current, factual news article on the topic: "{topic}". 
Follow this format strictly:
**Title:** <engaging title>
---
**Summary:**
- Bullet 1
- Bullet 2
- Bullet 3
- Bullet 4
- Bullet 5
---
**Details:**
Structured detailed explanation with facts and recent developments. Avoid using placeholders like [insert...]."""

    res = llm2.invoke(base_prompt)
    
    if "[insert" in res.content.lower() or "template" in res.content.lower():
        retry_prompt = f"""You gave a placeholder. Now try again. 
Write a complete, fact-filled, concise, and real news article about "{topic}". 
DO NOT use [insert...] or any placeholders. Provide real information and structure."""
        res = llm2.invoke(retry_prompt)
    
    return res

st.title("📰 NewsForge")
st.write("Get the latest news on any topic, powered by AI and Unsplash images.")

topic = st.text_input("📌 Enter a news topic (e.g., Sports, War, Technology, Politics, etc.):")

if st.button("Generate News"):
    if topic:
        if not is_valid_news_topic(topic):
            st.error("❌ I only provide news updates on current topics. Please enter a valid news topic.")
        else:
            with st.spinner("Generating news... ⏳"):
                res = fetch_news_from_gemini(topic)
            
            split_res = res.content.split('---')
            title = split_res[0].replace("**Title:**", "").strip() if len(split_res) > 0 else "News Title"
            summary = split_res[1].replace("**Summary:**", "").strip() if len(split_res) > 1 else "No summary available."
            details = split_res[2].replace("**Details:**", "").strip() if len(split_res) > 2 else res.content

            st.subheader(f"📰 {title}")
            st.markdown(f"**Summary:**\n{summary}")
            st.write(details)

            with st.spinner("Generating audio... 🎧"):
                details_audio = generate_audio(details, "details_audio.mp3")
                st.audio(f"data:audio/mp3;base64,{details_audio}", format="audio/mp3", start_time=0)

            with st.spinner("Fetching images... 🖼"):
                image_urls = fetch_unsplash_images(topic, count=5)

            if image_urls:
                cols = st.columns(len(image_urls))
                for col, img_url in zip(cols, image_urls):
                    col.image(img_url, caption=f"Related to {topic}", use_column_width=True)
            else:
                st.warning("No images found for this topic.")
            
            db.collection("news_queries").add({
                "topic": topic,
                "title": title,
                "summary": summary,
                "details": details,
                "images": image_urls
            })
    else:
        st.warning("Please enter a topic first.")
