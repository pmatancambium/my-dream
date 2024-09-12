import streamlit as st
import os
from dotenv import load_dotenv
import time
import random
from PIL import Image, ImageDraw
import requests
from io import BytesIO
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.header import Header
from deep_translator import GoogleTranslator
import json
from user_data_storage import user_storage

# if user_data is not in st.session_state, add it with default values
if "user_data" not in st.session_state:
    st.session_state.user_data = {}

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
            st.session_state.username = username  # Store the username in session state
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
    "'The future belongs to those who believe in the beauty of their dreams.'  Eleanor Roosevelt",
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


def send_email(subject, body, image_data, username):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = RECIPIENT_EMAIL
    
    # Get the user's image filename without extension
    user_to_file = st.secrets["user_to_file"]
    user_image_filename = os.path.splitext(user_to_file.get(username, ""))[0]
    
    # Add the user's image filename to the subject
    full_subject = f"{subject} - {user_image_filename}"
    msg["Subject"] = Header(full_subject, "utf-8")

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


def upload_image_to_leonardo(image_file):
    url = "https://cloud.leonardo.ai/api/rest/v1/init-image"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {LEONARDO_API_KEY}"
    }
    
    # Assume all images are JPEGs
    payload = {"extension": "jpg"}
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to get presigned URL: {response.text}")
    
    upload_data = response.json()['uploadInitImage']
    fields = json.loads(upload_data['fields'])
    upload_url = upload_data['url']
    image_id = upload_data['id']
    
    files = {'file': ('image.jpg', image_file, 'image/jpeg')}
    response = requests.post(upload_url, data=fields, files=files)
    if response.status_code != 204:
        raise Exception(f"Failed to upload image: {response.status_code}")
    
    return image_id


def generate_image_leonardo(prompt, init_image_id, preset_style):
    if not init_image_id:
        raise Exception("init_image_id is required")
    
    headers = {
        "Authorization": f"Bearer {LEONARDO_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "modelId": "1e60896f-3c26-4296-8ecc-53e2afecc132",  # Leonardo Diffusion XL
        # "modelId": "aa77f04e-3eec-4034-9c07-d0f619684628",
        # "modelId": "b63f7119-31dc-4540-969b-2a9df997e173",
        "presetStyle": preset_style,
        "photoReal": True,
        "photoRealVersion":"v2",
        "alchemy":True,
        "num_images": 1,
        "enhancePrompt": True,
        "controlnets": [
            {
                "initImageId": init_image_id,
                "initImageType": "UPLOADED",
                "preprocessorId": 133, # Character Reference Id
                "strengthType": "High",
            }
        ] if init_image_id else [],
    }

    response = requests.post(LEONARDO_API_URL, json=payload, headers=headers)

    if response.status_code == 200:
        generation_id = response.json()["sdGenerationJob"]["generationId"]
        # st.write(generation_id)

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


def overlay_thumbnail(main_image, thumbnail, max_size=(300, 300), position=(10, 10)):
    # Calculate the thumbnail size while maintaining aspect ratio
    thumbnail.thumbnail(max_size, Image.LANCZOS)
    
    # Create a new image with an alpha channel for the border
    thumb_w, thumb_h = thumbnail.size
    thumbnail_with_border = Image.new('RGBA', (thumb_w+4, thumb_h+4), (255, 255, 255, 0))
    
    # Draw a white border
    draw = ImageDraw.Draw(thumbnail_with_border)
    draw.rectangle([0, 0, thumb_w+3, thumb_h+3], outline=(255, 255, 255, 255), width=2)
    
    # Paste the resized thumbnail onto the new image
    thumbnail_with_border.paste(thumbnail, (2, 2))
    
    # Paste the thumbnail with border onto the main image
    main_image.paste(thumbnail_with_border, position, thumbnail_with_border)
    return main_image


def load_user_image(username):
    user_to_file = st.secrets["user_to_file"]
    if username in user_to_file:
        image_path = os.path.join("images", user_to_file[username])
        if os.path.exists(image_path):
            return Image.open(image_path)
    return None


def app():
    # 
    st.title("חלום בתמונה")
    st.write("תארו את החלום שלכם בקצרה (עד 200 תווים):")

    # Single input field for dream description
    dream_description = st.text_area("בחלומי אני...", max_chars=200, height=100, placeholder="לדוגמה: במקום מסוים, עם אדם או חיה וכו'...")

    # Load and display the user's profile image
    user_image = load_user_image(st.session_state.username)
    if user_image:
        st.image(user_image, caption="Your profile image", width=300)
    else:
        st.warning("No profile image found for your account.")

    # Set preset style to "UNPROCESSED" without user input
    selected_style = "UNPROCESSED"

    # Generate button
    if st.button("צור תמונה"):
        if user_storage.can_generate_image(st.session_state.username):
            if dream_description:
                # Create the complete text
                complete_text = f"{dream_description}"
                st.write("הטקסט המלא:")
                st.info(complete_text)
                complete_text_english = translate_text(complete_text)
                complete_text_english = "This is a picture of me. Place me according to the description: I am" + complete_text_english

                # Start a spinner while generating the image
                with st.spinner("יוצר את התמונה שלך..."):
                    start_time = time.time()

                    # Display fun facts while waiting
                    while time.time() - start_time < 10:
                        if int(time.time() - start_time) % 5 == 0:
                            random_fact = random.choice(fun_facts)
                            st.markdown(
                                f"<div class='ltr'>{random_fact}</div>",
                                unsafe_allow_html=True,
                            )
                        time.sleep(1)

                    # Generate image using Leonardo AI API
                    try:
                        init_image_id = None
                        thumbnail_image = None
                        if user_image:
                            # Convert PIL Image to bytes
                            img_byte_arr = BytesIO()
                            user_image.save(img_byte_arr, format='JPEG')
                            img_byte_arr.seek(0)  # Reset the buffer position
                            
                            init_image_id = upload_image_to_leonardo(img_byte_arr)
                            thumbnail_image = user_image

                        image_url = generate_image_leonardo(complete_text_english, init_image_id, selected_style)

                        # Download the image
                        response = requests.get(image_url)
                        img = Image.open(BytesIO(response.content))

                        # If a thumbnail image was uploaded, overlay it on the generated image
                        if thumbnail_image:
                            img = overlay_thumbnail(img, thumbnail_image)

                        # Convert the image to a format that can be downloaded
                        img_byte_arr = BytesIO()
                        img.save(img_byte_arr, format="PNG")
                        img_byte_arr = img_byte_arr.getvalue()

                        # Display the image without any overlay
                        st.image(img, caption="התמונה שנוצרה מהחלום שלך")

                        # Create two columns for the buttons
                        col1, col2 = st.columns(2)

                        # Add a download button in the first column
                        with col1:
                            st.download_button(
                                label="הורד את התמונה",
                                data=img_byte_arr,
                                file_name="dream_image.png",
                                mime="image/png",
                            )

                        # Add a form for email sending in the second column
                        with col2:
                            with st.form(key="email_form"):
                                st.form_submit_button("שלח את התמונה למייל", on_click=send_email_callback, args=(complete_text, img_byte_arr))

                        # Add a button to regenerate the image
                        if st.button("צור תמונה חדשה", key="regenerate", type="primary"):
                            st.experimental_rerun()

                        # After successful image generation:
                        user_storage.increment_image_count(st.session_state.username)

                    except Exception as e:
                        st.error(
                            f"An error occurred while generating the image: {str(e)}"
                        )
            else:
                st.warning("אנא תארו את החלום שלכם לפני יצירת התמונה.")
        else:
                st.error("You have reached the maximum number of images you can generate. Please try again later.")

    # Add a logout button
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()


# Add this function outside of the app() function
def send_email_callback(complete_text, img_byte_arr):
    email_subject = "New Dream Image Generated"
    email_body = f"A new dream image has been generated with the following prompt:\n\n{complete_text}"
    
    with st.spinner("שולח את התמונה למייל..."):
        if send_email(email_subject, email_body, img_byte_arr, st.session_state.username):
            st.success("התמונה והפרומפט נשלחו בהצלחה למייל")
            user_storage.set_last_email_sent(st.session_state.username)
        else:
            st.error("לא הצלחנו לשלוח את התמונה והפרומפט למייל")


if __name__ == "__main__":
    main()
