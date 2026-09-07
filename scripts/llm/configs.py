# This file contains all the constants for AA's OPEN AI account
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Fallback to parse .env without third-party dotenv
    env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key not in os.environ:
                        os.environ[key] = val

# Google Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

# HF models deployed on TGI
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "")
IP = os.environ.get("IP", "")

# Azure Cloud
TENANT_ID = os.environ.get("TENANT_ID", "")
INTERACTIVE_CLIENT_ID = os.environ.get("INTERACTIVE_CLIENT_ID", "")
AZURE_LOGIN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
SCOPE_INTERACTIVE_CLI = f"api://{INTERACTIVE_CLIENT_ID}/.default"
SCOPE_INTERACTIVE_BROWSER = f"api://{INTERACTIVE_CLIENT_ID}/token"

# Client secrets
NON_INTERACTIVE_CLIENT_ID = os.environ.get("NON_INTERACTIVE_CLIENT_ID", "")
SERVICE_PRINCIPAL = os.environ.get("SERVICE_PRINCIPAL", "")
SERVICE_PRINCIPAL_SECRET = os.environ.get("SERVICE_PRINCIPAL_SECRET", "")
SCOPE_NON_INTERACTIVE = f"api://{NON_INTERACTIVE_CLIENT_ID}/.default"

# OpenAI
OPENAI_LOG = os.environ.get("OPENAI_LOG", "info")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_API_TYPE = os.environ.get("OPENAI_API_TYPE", "")
OPENAI_API_VERSION = os.environ.get("OPENAI_API_VERSION", "")
OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE", "")

# Global AA
AZURE_SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID", "")
OPENAI_ACCOUNT_NAME = os.environ.get("OPENAI_ACCOUNT_NAME", "")
AZURE_RG_NAME = os.environ.get("AZURE_RG_NAME", "")
