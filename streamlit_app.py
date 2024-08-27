import streamlit as st
from openai import OpenAI
import openai
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

# Load environment variables
load_dotenv()
client = OpenAI()
# Set up OpenAI API key
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Email configuration
EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]
RECIPIENT_EMAIL = st.secrets["RECIPIENT_EMAIL"]

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

def send_email(subject, body, image_data):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = Header(subject, 'utf-8')

    # Encode the body as UTF-8
    body_utf8 = body.encode('utf-8')
    msg.attach(MIMEText(body_utf8.decode('utf-8'), 'plain', 'utf-8'))

    image = MIMEImage(image_data, name="dream_image.png")
    msg.attach(image)

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"An error occurred while sending the email: {str(e)}")
        return False

# Streamlit app
def main():
    st.title("חלום בתמונה")
    st.write("מלאו את הפרטים הבאים כדי ליצור תמונה מהחלום שלכם:")

    # Input fields
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
        if character and clothing and vehicle and companion and background:
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

                # Generate image using OpenAI API
                try:
                    response = client.images.generate(
                        model="dall-e-3",
                        prompt=complete_text + "Try to make it fun and interesting!",
                        size="1792x1024",
                        quality="hd",
                        style="vivid",
                        n=1,
                    )
                    image_url = response.data[0].url

                    # Download the image
                    response = requests.get(image_url)
                    img = Image.open(BytesIO(response.content))

                    # Convert the image to a format that can be downloaded
                    img_byte_arr = BytesIO()
                    img.save(img_byte_arr, format='PNG')
                    img_byte_arr = img_byte_arr.getvalue()

                    # Display the image without any overlay
                    st.image(img, caption="התמונה שנוצרה מהחלום שלך")

                    # Add a download button
                    st.download_button(
                        label="הורד את התמונה",
                        data=img_byte_arr,
                        file_name="dream_image.png",
                        mime="image/png"
                    )

                    # Send email
                    email_subject = "New Dream Image Generated"
                    email_body = f"A new dream image has been generated with the following prompt:\n\n{complete_text}"
                    if send_email(email_subject, email_body, img_byte_arr):
                        st.success("התמונה והפרומפט נשלחו בהצלחה למייל")
                    else:
                        st.warning("לא הצלחנו לשלוח את התמונה והפרומפט למייל")

                except Exception as e:
                    st.error(f"An error occurred while generating the image: {str(e)}")
        else:
            st.warning("אנא מלאו את כל השדות לפני יצירת התמונה.")

if __name__ == "__main__":
    main()