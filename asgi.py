from app import app
from asgiref.wsgi import WsgiToAsgi
import uvicorn
# Для прямого запуска через этот файл
if __name__ == "__main__":
    uvicorn.run("asgi:app", host="0.0.0.0", port=8000)
# Export the ASGI application
asgi_app = WsgiToAsgi(app)