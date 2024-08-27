import streamlit as st
from openai import OpenAI
import openai
import os
from dotenv import load_dotenv
import time
import random
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

# Load environment variables
load_dotenv()
client = OpenAI()
# Set up OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

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


def add_name_to_image(image_url, name=None):
    # Download the image
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))

    if name:
        # Create a drawing object
        draw = ImageDraw.Draw(img)

        font_path = os.path.join(
            os.path.dirname(__file__), "fonts", "DejaVuSans-Bold.ttf"
        )
        font = ImageFont.truetype(font_path, 40)
        # Get the size of the text
        left, top, right, bottom = font.getbbox(name)
        text_width = right - left
        text_height = bottom - top

        # Calculate the position to center the text
        position = ((img.width - text_width) / 2, 10)  # 10 pixels from the top

        # Add the text to the image
        draw.text(position, name, font=font, fill=(255, 255, 255))  # White text

    return img


# Streamlit app
def main():
    st.title("חלום בתמונה")
    st.write("מלאו את הפרטים הבאים כדי ליצור תמונה מהחלום שלכם:")

    # Input fields
    name = st.text_input("שם המשתמש:")
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

                    # Add name to the image if provided
                    img_with_name = add_name_to_image(image_url, name)

                    # Display the image with or without the name overlay
                    st.image(img_with_name, caption="התמונה שנוצרה מהחלום שלך")
                except Exception as e:
                    st.error(f"An error occurred while generating the image: {str(e)}")
        else:
            st.warning("אנא מלאו את כל השדות לפני יצירת התמונה.")


if __name__ == "__main__":
    main()
