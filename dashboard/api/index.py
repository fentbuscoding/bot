from flask import Flask, Request
import sys
import os

# Add the root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the blueprint
from lastfm_callback import lastfm_callback

app = Flask(__name__)

# Register the blueprint
app.register_blueprint(lastfm_callback)

def handler(request: Request):
    """Handle requests in Vercel serverless function"""
    return app.wsgi_app(request.environ, lambda x, y: y)

if __name__ == "__main__":
    app.run(port=5000)
