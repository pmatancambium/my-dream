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
import asyncio
import traceback

# if user_data is not in st.session_state, add it with default values
if "user_data" not in st.session_state:
    st.session_state.user_data = {}

if "processed_images" not in st.session_state:
    st.session_state.processed_images = None

col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.image("main_logo.png", width=600, use_column_width=True)

# Load environment variables #
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


def send_email(subject, body, image_data, username, additional_recipient=None):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = RECIPIENT_EMAIL
    if additional_recipient:
        msg["Cc"] = additional_recipient
    
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
            recipients = [RECIPIENT_EMAIL]
            if additional_recipient:
                recipients.append(additional_recipient)
            server.sendmail(EMAIL_ADDRESS, recipients, msg.as_string())
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
    headers = {
        "Authorization": f"Bearer {LEONARDO_API_KEY}",
        "Content-Type": "application/json",
    }

    escaped_prompt = prompt.replace("'", "\\'")

    # First, generate an image based on the prompt alone
    initial_payload = {
        "prompt": escaped_prompt,
        "modelId": "1e60896f-3c26-4296-8ecc-53e2afecc132",  # Leonardo Diffusion XL
        "presetStyle": preset_style,
        "photoReal": True,
        "photoRealVersion": "v2",
        "alchemy": True,
        "num_images": 1,
        "enhancePrompt": True,
    }

    initial_response = requests.post(LEONARDO_API_URL, json=initial_payload, headers=headers)

    if initial_response.status_code != 200:
        raise Exception(f"Failed to generate initial image: {initial_response.text}")

    initial_generation_id = initial_response.json()["sdGenerationJob"]["generationId"]

    # Poll for the generated initial image
    while True:
        status_response = requests.get(f"{LEONARDO_API_URL}/{initial_generation_id}", headers=headers)
        if status_response.status_code == 200:
            generation_data = status_response.json()["generations_by_pk"]
            if generation_data["status"] == "COMPLETE":
                generated_image_id = generation_data["generated_images"][0]["id"]
                break
        time.sleep(5)  # Wait for 5 seconds before polling again

    # Now, generate the final images using both the uploaded and generated images as references
    final_payload = {
        "prompt": escaped_prompt,
        "modelId": "1e60896f-3c26-4296-8ecc-53e2afecc132",  # Leonardo Diffusion XL
        "presetStyle": preset_style,
        "photoReal": True,
        "photoRealVersion": "v2",
        "alchemy": True,
        "num_images": 4,
        "enhancePrompt": True,
        "controlnets": [
            {
                "initImageId": init_image_id,
                "initImageType": "UPLOADED",
                "preprocessorId": 133,  # Character Reference Id
                "strengthType": "High",
            },
            {
                "initImageId": generated_image_id,
                "initImageType": "GENERATED",
                "preprocessorId": 67,  # Character Reference Id
                "strengthType": "Mid",
            }
        ] if init_image_id else [],
    }

    final_response = requests.post(LEONARDO_API_URL, json=final_payload, headers=headers)

    if final_response.status_code == 200:
        generation_id = final_response.json()["sdGenerationJob"]["generationId"]

        # Poll for the generated images
        while True:
            status_response = requests.get(f"{LEONARDO_API_URL}/{generation_id}", headers=headers)
            if status_response.status_code == 200:
                generation_data = status_response.json()["generations_by_pk"]
                if generation_data["status"] == "COMPLETE":
                    return [image["url"] for image in generation_data["generated_images"]]
            time.sleep(5)  # Wait for 5 seconds before polling again
    else:
        raise Exception(f"Failed to generate final images: {final_response.text}")


# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


def success_page():
    st.title("Success!")
    st.success("התמונה והפרומפט נשלחו בהצלחה")
    st.write("ניתן לסגור חלון זה עכשיו או להמשיך לאפליקציה הראשית.")

# Streamlit app
def main():
    if "page" not in st.session_state:
        st.session_state.page = "main"

    if not st.session_state.get("authenticated", False):
        login_page()
        return

    # Create a container for the main content
    main_container = st.empty()

    if st.session_state.page == "main":
        with main_container.container():
            if "error_message" in st.session_state:
                st.error(st.session_state.error_message)
                del st.session_state.error_message

            st.title("חלום בתמונה")
            st.write("אנא תארו חלום או דמיון שלכם. למשל, 'אני חולם לשחות עם להקת כרישים מסוכנים באוקיינוס' (עד 200 תוים).")
            st.write("מדובר בערב חברתי. נשמח לחלומות ודמיונות קלילים ומשעשעים.")

            dream_description = st.text_area("בחלומי אני...", max_chars=200, height=100, placeholder="לדוגמה: במקום מסוים, עם אדם או חיה וכו'...")

            if st.button("צור תמונה", type="primary"):
                if user_storage.can_generate_image(st.session_state.username):
                    if dream_description:
                        st.session_state.complete_text = dream_description
                        st.session_state.page = "loading"
                        st.experimental_rerun()
                    else:
                        st.warning("אנא תארו את החלום שלכם לפני יצירת התמונה.")
                else:
                    st.error("הגעת למספר המקסימלי של תמונות שאתה יכול ליצור. אנא נסה שוב מאוחר יותר.")

            if st.button("Logout"):
                st.session_state.authenticated = False
                st.experimental_rerun()

    elif st.session_state.page == "loading":
        with main_container.container():
            st.title("יוצר את התמונה שלך...")
            st.warning("אנא אל תסגור את הדף או תרענן אותו בזמן שאנחנו יוצרים את התמונה שלך.")
            
            with st.spinner("מעבד את החלום שלך..."):
                status_text = st.empty()
                
                # Display random fun facts while processing
                while True:
                    status_text.text(random.choice(fun_facts))
                    time.sleep(5)  # Update fun fact every 5 seconds
                    
                    # Check if images are ready
                    processed_images = asyncio.run(generate_images_async())
                    if processed_images:
                        break

            if processed_images:
                st.session_state.processed_images = processed_images
                st.session_state.page = "show_images"
                st.experimental_rerun()
            else:
                st.session_state.page = "main"
                st.experimental_rerun()

    elif st.session_state.page == "show_images":
        show_generated_images_page()
    
    elif st.session_state.page == "success":
        success_page()

async def generate_images_async():
    try:
        user_image = load_user_image(st.session_state.username)
        init_image_id = None
        thumbnail_image = None
        if user_image:
            img_byte_arr = BytesIO()
            user_image.save(img_byte_arr, format='JPEG')
            img_byte_arr.seek(0)
            
            init_image_id = upload_image_to_leonardo(img_byte_arr)
            thumbnail_image = user_image

        complete_text_english = translate_text(st.session_state.complete_text)
        complete_text_english = "This is a picture of me. Place me according to the description: I am" + complete_text_english

        image_urls = generate_image_leonardo(complete_text_english, init_image_id, "UNPROCESSED")

        processed_images = []
        for url in image_urls:
            response = requests.get(url)
            img = Image.open(BytesIO(response.content))

            if thumbnail_image:
                img = overlay_thumbnail(img, thumbnail_image)

            processed_images.append(img)

        return processed_images
    except Exception as e:
        st.session_state.error_message = f"An error occurred: {str(e)}\n\n{traceback.format_exc()}"
        return None

def login_page():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if authenticate(username, password):
            st.session_state.authenticated = True
            st.session_state.username = username
            st.success(f"Welcome {username}!")
            st.rerun()
        else:
            st.error("Invalid username or password")


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

def show_generated_images_page():
    st.title("התמונות שנוצרו")
    st.write("בחר את התמונה שברצונך לשלוח:")

    cols = st.columns(2)
    for i, img in enumerate(st.session_state.processed_images):
        with cols[i % 2]:
            st.image(img, caption=f"תמונה {i+1}", use_column_width=True)
            if st.button(f"בחר תמונה {i+1}", key=f"select_image_{i}"):
                st.session_state.selected_image = img

                st.write("התמונה הנבחרת:")
                st.image(st.session_state.selected_image, caption="התמונה שנבחרה מהחלום שלך")

                img_byte_arr = BytesIO()
                st.session_state.selected_image.save(img_byte_arr, format="PNG")
                img_byte_arr = img_byte_arr.getvalue()

                email_subject = "New Dream Image Generated"
                email_body = f"A new dream image has been generated with the following prompt:\n\n{st.session_state.complete_text}"
                additional_recipient = st.secrets["ADDITIONAL_RECIPIENT"]
                
                with st.spinner("שולח את התמונה"):
                    if send_email(email_subject, email_body, img_byte_arr, st.session_state.username, additional_recipient=additional_recipient):
                        user_storage.set_last_email_sent(st.session_state.username)
                        st.session_state.page = "success"
                        st.experimental_rerun()
                    else:
                        st.error("לא הצלחנו לשלוח את התמונה והפרומפט")

    # Calculate remaining attempts
    user_data = user_storage.get_user_data(st.session_state.username)
    remaining_attempts = 3 - user_data["image_count"]

    if st.button(f"התחל מחדש (נותרו {remaining_attempts} ניסיונות)", key="regenerate", type="primary"):
        st.session_state.processed_images = None
        st.session_state.selected_image = None
        st.session_state.complete_text = None
        st.session_state.page = "main"
        user_storage.increment_image_count(st.session_state.username)
        st.experimental_rerun()

if __name__ == "__main__":
    main()
