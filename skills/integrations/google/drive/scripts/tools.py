import os.path
from typing import Dict, Any, List, Optional
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import logging

logger = logging.getLogger(__name__)

# Scopes
# Note: If the existing token doesn't have this scope, this will fail or need re-auth.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def _get_integrations_root() -> str:
    """Return path to integrations/google directory.

    Reads OSP_INTEGRATIONS_ROOT env var first; falls back to resolving
    relative to this file's location so the skill works both installed
    and from source without directory-traversal hops.
    """
    env_root = os.environ.get("OSP_INTEGRATIONS_ROOT")
    if env_root:
        return os.path.join(env_root, "google")
    # Source-tree fallback: skills/integrations/google/drive/scripts/ -> integrations/google/
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(current_dir, "..", "..", "..", "..", "..", "integrations", "google"))

def list_profiles():
    """Lists available token profiles."""
    google_integrations_dir = _get_integrations_root()
    
    profiles = []
    if os.path.exists(google_integrations_dir):
        for f in os.listdir(google_integrations_dir):
            if f.startswith("token_") and f.endswith(".json"):
                 profile = f[6:-5] # remove token_ and .json
                 profiles.append(profile)
    return profiles

def get_credentials(profile_name=None):
    """Gets valid user credentials from local file."""
    google_integrations_dir = _get_integrations_root()
    
    # If no profile specified, try to find one or default
    if not profile_name:
        profiles = list_profiles()
        if not profiles:
            logger.error("No token profiles found.")
            return None
        # Default to the first one for now, or 'default' if exists
        if 'default' in profiles:
            profile_name = 'default'
        else:
            profile_name = profiles[0]
            logger.info(f"No profile specified, using first found: {profile_name}")

    token_path = os.path.join(google_integrations_dir, f'token_{profile_name}.json')
    
    creds = None
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception as e:
            logger.error(f"Error loading credentials for {profile_name}: {e}")
            return None
    else:
        logger.error(f"Token file not found: {token_path}")
            
    return creds

def search_files(query: str = None, limit: int = 10, profile_name: str = None) -> List[Dict[str, Any]]:
    """Searches files in Drive."""
    creds = get_credentials(profile_name)
    if not creds:
        return [{"error": f"No credentials found. Available profiles: {list_profiles()}"}]
    
    try:
        service = build('drive', 'v3', credentials=creds)
        
        # Build API query
        # If query is simple text, assume name contains
        api_query = "trashed = false"
        if query:
            if "contains" in query or "=" in query: 
                # Assume user provided valid Drive API query
                api_query += f" and ({query})"
            else:
                # Simple name search
                api_query += f" and name contains '{query}'"
                
        logger.info(f"Executing Drive Search: {api_query}")
        
        results = service.files().list(
            q=api_query, pageSize=limit, fields="nextPageToken, files(id, name, mimeType, webViewLink)"
        ).execute()
        
        items = results.get('files', [])
        return items
        
    except Exception as e:
        logger.error(f"Drive API Error: {e}")
        return [{"error": f"Drive API Error: {str(e)}"}]

def execute(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Entry point.
    """
    query = arguments.get("query")
    limit = arguments.get("limit", 10)
    profile_name = arguments.get("profile_name")
    
    files = search_files(query, limit, profile_name)
    has_error = False
    if isinstance(files, list) and len(files) > 0 and isinstance(files[0], dict):
        if "error" in files[0]:
            has_error = True
            
    return {
        "files_found": len(files) if not has_error else 0,
        "results": files
    }
