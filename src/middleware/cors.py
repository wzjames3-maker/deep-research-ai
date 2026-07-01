from fastapi.middleware.cors import CORSMiddleware

cors_config = {
    "allow_origins": ["http://localhost:5173", "http://localhost", "http://127.0.0.1", "http://127.0.0.1:5173"],
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}


def setup_cors(app):
    app.add_middleware(CORSMiddleware, **cors_config)
