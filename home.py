import streamlit as st
import requests
from urllib.parse import urlencode
import os
from dotenv import load_dotenv

# --- 0. Environment Setup ---

# Load environment variables from .env file
load_dotenv()

# Retrieve necessary secrets
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
REDIRECT_URI = os.getenv("AUTH0_CALLBACK_URL")
AUDIENCE = os.getenv("AUTH0_AUDIENCE")

# Set Streamlit Page Configuration
st.set_page_config(page_title="Auth0 Login & Logout", layout="centered")


# --- 1. Utility Functions ---

def login_button():
    """Generates the Auth0 authorization URL and displays the login button."""
    
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        # Request openid, profile, and email scopes to get user info
        "scope": "openid profile email",
        # Audience is crucial to ensure the access token is a JWT
        "audience": AUDIENCE
    }

    auth_url = f"https://{AUTH0_DOMAIN}/authorize?{urlencode(params)}"

    st.markdown(
        f"""
        <div style="text-align: center;">
            <a href="{auth_url}">
                <button style="
                    background-color:#0077b6; 
                    color:white;
                    padding:12px 30px;
                    border:none;
                    border-radius:8px;
                    cursor:pointer;
                    font-size: 18px;
                    box-shadow: 0 4px #005580;
                ">Login with Auth0</button>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def exchange_code_for_token(code):
    """Exchanges the authorization code for an Access Token."""
    token_url = f"https://{AUTH0_DOMAIN}/oauth/token"

    body = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    try:
        response = requests.post(token_url, json=body)
        
        # Check for HTTP errors and provide detailed Auth0 error message
        if response.status_code >= 400:
            error_details = response.json()
            st.error(f"Auth0 Token Exchange Failed ({response.status_code}): {error_details.get('error', 'Unknown Error')}")
            if 'error_description' in error_details:
                st.exception(error_details['error_description'])
            return {"error": "token_exchange_failed"}
            
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Network Error exchanging code for token: {e}")
        return {"error": "network_failed"}


def get_user_info(access_token):
    """Uses the Access Token to retrieve user profile information from the /userinfo endpoint."""
    user_url = f"https://{AUTH0_DOMAIN}/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(user_url, headers=headers)
        
        # Check for HTTP errors and provide detailed Auth0 error message
        if response.status_code >= 400:
            # Try to parse JSON for detailed error, otherwise use text content
            try:
                error_details = response.json()
                st.error(f"Auth0 UserInfo Failed ({response.status_code}): {error_details.get('error', 'Unknown Error')}")
            except requests.exceptions.JSONDecodeError:
                 st.error(f"Auth0 UserInfo Failed ({response.status_code}): Could not parse error details.")

            st.warning("HINT: This often means the Access Token is OPAQUE. Ensure AUDIENCE is set to a valid API Identifier.")
            return {"error": "userinfo_failed"}
            
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Network Error retrieving user info: {e}")
        return {"error": "network_failed"}


def logout():
    """Clears the Streamlit session state and triggers a rerun."""
    # Clear both keys used for authentication status and profile data
    if "user_info" in st.session_state:
        del st.session_state["user_info"]
    if "username" in st.session_state:
        del st.session_state["username"]
    st.rerun()


# --- 2. Main Application Flow ---

# Global check for environment configuration
required_env_vars = {
    "AUTH0_DOMAIN": AUTH0_DOMAIN, 
    "CLIENT_ID": CLIENT_ID, 
    "CLIENT_SECRET": CLIENT_SECRET,
    "REDIRECT_URI": REDIRECT_URI,
    "AUDIENCE": AUDIENCE
}

missing_vars = [key for key, value in required_env_vars.items() if not value]

if missing_vars:
    st.error(f"Configuration Error: The following environment variables are missing or empty in your .env file: {', '.join(missing_vars)}")
    st.info("Please ensure all Auth0 credentials are set correctly before running.")
    st.stop()


query_params = st.query_params

# A. Handle the Auth0 redirect (when 'code' is in the URL)
if "code" in query_params:
    code = query_params["code"]
    
    # Check if the session is already authenticated using the 'username' key
    if "username" not in st.session_state:
        
        token_data = exchange_code_for_token(code)

        if "access_token" in token_data:
            access_token = token_data["access_token"]
            user_info = get_user_info(access_token)

            if "error" not in user_info:
                # Store the full user info payload
                st.session_state["user_info"] = user_info
                
                # --- REQUIRED CHANGE: Extract and store the identifier in st.session_state["username"] ---
                # Prioritize email, then nickname, then the unique 'sub' (Auth0 ID)
                user_identifier = user_info.get('email') or user_info.get('nickname') or user_info.get('sub', 'Unknown User')
                st.session_state["username"] = user_identifier
                # ------------------------------------------------------------------------------------------
                
                # Rerun the app to remove the 'code' from the URL and display the dashboard
                st.rerun()
            else:
                st.error("Could not retrieve user details. Please check console for token or user info error details.")

        else:
            # Error handling is done inside exchange_code_for_token
            st.stop()
    
# B. Check login status and render UI

# REQUIRED CHANGE: Check for the desired key "username" to determine login status
if "username" not in st.session_state:
    st.header("🔒 Login to Access the Dashboard")
    login_button()
    st.markdown("<br><p style='text-align: center; color: gray;'>Note: Session is lost when the app reloads or the browser tab closes.</p>", unsafe_allow_html=True)
    st.stop()


# C. Protected Content (Only runs if username is in session_state)

# Get the desired username/identifier
user_id = st.session_state["username"]
# Get the full profile data (for the JSON display)
full_user_profile = st.session_state.get("user_info", {})

st.title("✅ Dashboard")
st.success(f"Welcome, {user_id}!")

st.markdown(f"""
This content is protected and you are authenticated.

**Your desired identifier (stored in `st.session_state["username"]`):** `{user_id}`
""")

st.subheader("Full User Profile Data (stored in `st.session_state['user_info']`)")
st.json(full_user_profile)


# --- 3. Logout Functionality ---
st.markdown("---")
st.button("Logout", on_click=logout, type="primary")