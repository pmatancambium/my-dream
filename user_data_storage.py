import streamlit as st
import json
from datetime import datetime, timedelta

class UserStorage:
    def __init__(self):
        if 'user_data' not in st.session_state:
            st.session_state.user_data = {}

    def load_data(self):
        return st.session_state.user_data

    def save_data(self):
        # No need to save, as we're using session state
        pass

    def get_user_data(self, username):
        data = self.load_data()
        if username not in data:
            data[username] = {"image_count": 0, "last_email_sent": None}
        return data[username]

    def increment_image_count(self, username):
        user_data = self.get_user_data(username)
        user_data["image_count"] += 1
        self.save_data()

    def set_last_email_sent(self, username):
        user_data = self.get_user_data(username)
        user_data["last_email_sent"] = datetime.now().isoformat()
        self.save_data()

    def can_generate_image(self, username):
        user_data = self.get_user_data(username)
        # if user is "דודזלצר" or "אורןפונו" or "דבורהאייפרמן" or "שירייכנר"
        if username == "דודזלצר" or username == "אורןפונו" or username == "דבורהאייפרמן" or username == "שירייכנר":
            return True
        return user_data["image_count"] < 3 # Limit to 3 images per user

    def can_send_email(self, username):
        user_data = self.get_user_data(username)
        if user_data["last_email_sent"] is None:
            return True
        last_sent = datetime.fromisoformat(user_data["last_email_sent"])
        return datetime.now() - last_sent > timedelta(minutes=5)

user_storage = UserStorage()