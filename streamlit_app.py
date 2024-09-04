import streamlit as st
import os
from dotenv import load_dotenv
import time
import random
from PIL import Image
import requests
from io import BytesIO
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.header import Header
from deep_translator import GoogleTranslator

# Load environment variables
load_dotenv()

# Leonardo AI API configuration
LEONARDO_API_KEY = st.secrets["LEONARDO_API_KEY"]
LEONARDO_API_URL = "https://cloud.leonardo.ai/api/rest/v1/generations"

# Email configuration
EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]
RECIPIENT_EMAIL = st.secrets["RECIPIENT_EMAIL"]


# Function to authenticate users
def authenticate(username, password):
    usernames = st.secrets["credentials"]["usernames"]
    passwords = st.secrets["credentials"]["passwords"]

    if username in usernames:
        index = usernames.index(username)
        if passwords[index] == password:
            return True
    return False


# Custom CSS to enable RTL for the entire app, except for the fun fact section
st.markdown(
    """
    <style>
    body {
        direction: rtl;
        text-align: right;
    }
    .ltr {
        direction: ltr;
        text-align: left;
        font-style: italic;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# List of fun facts or motivational quotes related to dreams or imagination
fun_facts = [
    "Did you know? The word 'dream' comes from the Middle English word 'dreme,' which means joy and music.",
    "'Imagination is the only weapon in the war against reality.' – Lewis Carroll",
    "'The future belongs to those who believe in the beauty of their dreams.' – Eleanor Roosevelt",
    "Dreams can sometimes predict the future—it's called precognitive dreaming.",
    "'All men who have achieved great things have been great dreamers.' – Orison Swett Marden",
    "'Dreams are today's answers to tomorrow's questions.' – Edgar Cayce",
    "'You are never too old to set another goal or to dream a new dream.' – C.S. Lewis",
    "'Hold fast to dreams, for if dreams die, life is a broken-winged bird that cannot fly.' – Langston Hughes",
    "Lucid dreaming is the practice of becoming aware of and controlling your dreams.",
    "'A dream you dream alone is only a dream. A dream you dream together is reality.' – John Lennon",
]


def translate_text(text):
    translator = GoogleTranslator(source="iw", target="en")
    return translator.translate(text)


def send_email(subject, body, image_data):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = Header(subject, "utf-8")

    # Encode the body as UTF-8
    body_utf8 = body.encode("utf-8")
    msg.attach(MIMEText(body_utf8.decode("utf-8"), "plain", "utf-8"))

    image = MIMEImage(image_data, name="dream_image.png")
    msg.attach(image)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"An error occurred while sending the email: {str(e)}")
        return False


# Function to generate image using Leonardo AI API
def generate_image_leonardo(prompt):
    headers = {
        "Authorization": f"Bearer {LEONARDO_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "modelId": "6b645e3a-d64f-4341-a6d8-7a3690fbf042",  # Leonardo Phoneix model
        # "modelId": "aa77f04e-3eec-4034-9c07-d0f619684628",
        # "width": 1024,
        # "height": 576,
        "num_images": 1,
        "alchemy": True,
        # "presetStyle": "",
        # "photoReal": True,
        # "photoRealVersion": "v2",
        "enhancePrompt": True,
        # "styleUUID": "111dc692-d470-4eec-b791-3475abac4c46",
        "styleUUID": "556c1ee5-ec38-42e8-955a-1e82dad0ffa1",
    }

    # payload = {
    #     "prompt": prompt,
    #     # "modelId": "6b645e3a-d64f-4341-a6d8-7a3690fbf042",  # Leonardo Phoneix model
    #     "modelId": "aa77f04e-3eec-4034-9c07-d0f619684628",
    #     # "width": 1024,
    #     # "height": 576,
    #     "num_images": 1,
    #     "alchemy": True,
    #     "presetStyle": "CREATIVE",
    #     "photoReal": True,
    #     "photoRealVersion": "v2",
    #     # "enhancePrompt": False,
    #     "styleUUID": "111dc692-d470-4eec-b791-3475abac4c46",
    # }

    response = requests.post(LEONARDO_API_URL, json=payload, headers=headers)

    if response.status_code == 200:
        generation_id = response.json()["sdGenerationJob"]["generationId"]

        # Poll for the generated image
        while True:
            status_response = requests.get(
                f"{LEONARDO_API_URL}/{generation_id}", headers=headers
            )
            if status_response.status_code == 200:
                generation_data = status_response.json()["generations_by_pk"]
                if generation_data["status"] == "COMPLETE":
                    return generation_data["generated_images"][0]["url"]
            time.sleep(5)  # Wait for 5 seconds before polling again
    else:
        raise Exception(f"Failed to generate image: {response.text}")


# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


# Streamlit app
def main():
    if not st.session_state.authenticated:
        # Login form
        st.title("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if authenticate(username, password):
                st.session_state.authenticated = True
                st.success(f"Welcome {username}!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    else:
        app()


def app():
    st.title("חלום בתמונה")
    st.write("מלאו את הפרטים הבאים כדי ליצור תמונה מהחלום שלכם:")

    # Input fields
    name = st.text_input("שם:")
    character = st.text_input(
        "1. בחלומי אני (דמות או חיה. למשל, דמות היסטורית או דמות מספר/סרט):"
    )
    clothing = st.text_input("2. לבוש ב:")
    vehicle = st.text_input(
        "3. אני נוסע ב (כלי רכב, כרכרה, יאכטה, חללית וכל מה שעולה בדעתכם):"
    )
    companion = st.text_input("4. ביחד עם:")
    background = st.text_input("5. המקום, הזמן והרקע שאני מדמיין:")

    # Generate button
    if st.button("צור תמונה"):
        if (
            name
            and character
            and clothing
            and vehicle
            and companion
            and background
        ):
            # Create the complete text
            complete_text = f"""
            בחלומי אני {character},
            לבוש ב{clothing}.
            אני נוסע ב{vehicle}
            ביחד עם {companion}.
            המקום, הזמן והרקע שאני מדמיין: {background}.
            """
            st.write("הטקסט המלא:")
            st.info(complete_text)
            complete_text_english = translate_text(complete_text)
            # st.write("הטקסט המלא באנגלית:")
            # st.info(complete_text_english)

            # Create an empty container for the fun fact
            fun_fact_container = st.empty()

            # Start a spinner while generating the image
            with st.spinner("יוצר את התמונה שלך..."):
                start_time = time.time()

                # Display fun facts while waiting
                while time.time() - start_time < 10:
                    if int(time.time() - start_time) % 5 == 0:
                        random_fact = random.choice(fun_facts)
                        fun_fact_container.markdown(
                            f"<div class='ltr'>{random_fact}</div>",
                            unsafe_allow_html=True,
                        )
                    time.sleep(1)

                # Generate image using Leonardo AI API
                try:
                    image_url = generate_image_leonardo(complete_text_english)

                    # Download the image
                    response = requests.get(image_url)
                    img = Image.open(BytesIO(response.content))

                    # Convert the image to a format that can be downloaded
                    img_byte_arr = BytesIO()
                    img.save(img_byte_arr, format="PNG")
                    img_byte_arr = img_byte_arr.getvalue()

                    # Display the image without any overlay
                    st.image(img, caption="התמונה שנוצרה מהחלום שלך")

                    # Add a download button
                    st.download_button(
                        label="הורד את התמונה",
                        data=img_byte_arr,
                        file_name="dream_image.png",
                        mime="image/png",
                    )

                    # Send email
                    email_subject = f"New Dream Image Generated by {name}"
                    email_body = f"A new dream image has been generated by {name} with the following prompt:\n\n{complete_text}"
                    if send_email(email_subject, email_body, img_byte_arr):
                        st.success("התמונה והפרומפט נשלחו בהצלחה למייל")
                    else:
                        st.warning("לא הצלחנו לשלוח את התמונה והפרומפט למייל")

                except Exception as e:
                    st.error(
                        f"An error occurred while generating the image: {str(e)}"
                    )
        else:
            st.warning("אנא מלאו את כל השדות לפני יצירת התמונה.")

    # Add a logout button
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()


if __name__ == "__main__":
    main()
