import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
import requests
import urllib.parse
import random
import string

# Define global variables for column mappings
COLUMN_MAPPINGS = {
    "first_name": "First Name",
    "last_name": "Last Name",
    "email_1": "Email",
    "email_2": "CC Email",
    "phone_1": "Cell Phone",
    "phone_2": "Home Phone",
    "phone_3": "Work Phone",
    "address": "Street Address",
    "city": "City",
    "state": "State",
    "zip_code": "Zip/Postal Code",
}

load_dotenv()

# For OAuth2.0 authentication
CINC_AUTH_URL = os.getenv("CINC_AUTH_URL") or st.secrets["CINC_AUTH_URL"]
CLIENT_ID = os.getenv("CLIENT_ID") or st.secrets["CLIENT_ID"]
CLIENT_SECRET = os.getenv("CLIENT_SECRET") or st.secrets["CLIENT_SECRET"]
REDIRECT_URI = os.getenv("REDIRECT_URI") or st.secrets["REDIRECT_URI"]

# For API requests
CINC_API_URL = os.getenv("CINC_API_URL") or st.secrets["CINC_API_URL"]


def generate_state():
    """Generate a random state parameter."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))


def get_auth_url():
    """Generate the authorization URL for CINCPro."""
    
    state = generate_state()
    st.session_state["state"] = state 
    
    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'state': state,
        'redirect_uri': REDIRECT_URI,
        'scope': 'api:create api:read api:update api:event', 
    }

    auth_url = f"{CINC_AUTH_URL}/authorize?{urllib.parse.urlencode(params)}"
    
    return auth_url


def exchange_code_for_token(code):
    """Exchange the authorization code for an access token."""
    data = {
        'grant_type': 'authorization_code',
        'code': code, 
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }
    
    response = requests.post(f"{CINC_AUTH_URL}/token", data=data)
    
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data['access_token']
        return access_token
    else:
        st.error(f"Error exchanging code for token: {response.status_code}")
        return None


def get_user_info(access_token):
    """Fetch the user info using the access token."""
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"{access_token}"
    }
    
    response = requests.get(f"{CINC_API_URL}/me", headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error fetching user info: {response.status_code}")
        return None


def send_to_cincpro(df_cincpro, access_token):
    """Send converted data to CINCPro CRM."""

    # temporary 
    st.info("Sending data to CINCPro...")
    st.success("Data sent successfully!")
    return
    
    
def main():
    st.title('Real Intent to CINCPro Converter')

    st.info("""Upload a CSV file. The app will convert your Real Intent CSV into a format that can be imported into CINCPro or will send it directly to CINCPro if authenticated.""")

    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    
    agent_assigned = st.text_input("(Optional) Enter an assigned agent.")
    st.write("This will assign the lead to the selected agent.")
    
    listing_agent = st.text_input("(Optional) Enter a listing agent.")
    st.write("This will assign the lead to the selected listing agent.")

    partner = st.text_input("(Optional) Enter a partner.")
    st.write("This will assign the lead to the selected partner.")
    
    pipeline = st.text_input("(Optional) Enter a pipeline.")
    st.write("This will set the lead’s pipeline stage. Note: this will not trigger any actions.")

    # Authentication section
    if "code" in st.query_params:
        
        # validate the state parameter
        if st.session_state.get("state") != st.query_params["state"]:
            st.error("Invalid state parameter??? Could not authenticate.")
            return
        
        code = st.query_params["code"]
        access_token = exchange_code_for_token(code)
        
        if access_token:
            user_info = get_user_info(access_token)
            if user_info:
                st.session_state["username"] = user_info["body"]['username']
                st.session_state["authenticated"] = True
                st.success(f"Logged in as {user_info["body"]['username']}")
    
    if not st.session_state.get("authenticated"):
        st.warning("You need to authenticate to send data directly to CINCPro. You can still download the CSV to upload manually.")
        st.markdown(f"[Authenticate with CINCPro]({get_auth_url()})")

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        
        # Check if required columns are in the dataframe
        missing_columns = [col for col in COLUMN_MAPPINGS.keys() if col not in df.columns]
        
        if not missing_columns:

            df_cincpro = df[list(COLUMN_MAPPINGS.keys())].rename(columns=COLUMN_MAPPINGS)
            
            # Add validation columns
            df_cincpro["Valid Email"] = df_cincpro["Email"].apply(lambda x: "YES" if pd.notna(x) and x != '' else "")
            df_cincpro["Valid Cell Phone"] = df_cincpro[["Cell Phone", "Home Phone", "Work Phone"]].apply(lambda x: "YES" if x.notna().any() else "", axis=1)

            if 'insight' in df.columns:
                df_cincpro['Custom Note'] = df['insight'].apply(lambda x: f"Insight: {x}")
                
            if agent_assigned:
                df_cincpro['Agent Assigned'] = agent_assigned
            if listing_agent:
                df_cincpro['Listing Agent'] = listing_agent
            if partner:
                df_cincpro['Partner'] = partner
            if pipeline:
                df_cincpro['Pipeline'] = pipeline

            df_cincpro['Source'] = 'Real Intent'

            # Display the resulting dataframe
            st.write("Converted DataFrame:")
            st.write(df_cincpro)

            # Allow the user to either download the CSV or send it directly to CINCPro
            option = st.radio("Choose an action", ["Download CSV", "Send to CINCPro"])

            if option == "Download CSV":
                csv = df_cincpro.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download converted CSV",
                    data=csv,
                    file_name='converted_file.csv',
                    mime='text/csv',
                )
                
            elif option == "Send to CINCPro" and st.session_state.get("authenticated"):
                send_to_cincpro(df_cincpro, access_token)
                
            elif option == "Send to CINCPro":
                st.warning("Please authenticate first to send data to CINCPro.")
                
        else:
            st.write(f"The uploaded file does not contain the required columns: {', '.join(missing_columns)}.")


if __name__ == "__main__":
    main()
