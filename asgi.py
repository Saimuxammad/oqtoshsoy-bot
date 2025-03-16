from app import app
from asgiref.wsgi import WsgiToAsgi

# Export the ASGI application
asgi_app = WsgiToAsgi(app)