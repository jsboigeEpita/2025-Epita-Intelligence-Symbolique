import sys
from pathlib import Path
from uvicorn.middleware.wsgi import WSGIMiddleware

# Add project root to path
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Import the Flask app
from argumentation_analysis.services.web_api.app import app as flask_app

# Create the ASGI wrapper
app = WSGIMiddleware(flask_app)