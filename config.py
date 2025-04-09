import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

# For OAuth2.0 authentication
CINC_AUTH_URL = os.getenv("CINC_AUTH_URL") or st.secrets["CINC_AUTH_URL"]
CLIENT_ID = os.getenv("CLIENT_ID") or st.secrets["CLIENT_ID"]
CLIENT_SECRET = os.getenv("CLIENT_SECRET") or st.secrets["CLIENT_SECRET"]
REDIRECT_URI = os.getenv("REDIRECT_URI") or st.secrets["REDIRECT_URI"]
CLIENT_DOMAIN = os.getenv("CLIENT_DOMAIN") or st.secrets["CLIENT_DOMAIN"]

# For API requests
CINC_API_URL = os.getenv("CINC_API_URL") or st.secrets["CINC_API_URL"]
