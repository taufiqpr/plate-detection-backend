from app import create_app

app = create_app()

if __name__ == "__main__":
    print("[INFO] Starting server...")
    config = app.config
    app.run(host=config.get("FLASK_HOST", "0.0.0.0"), port=config.get("FLASK_PORT", 5000), debug=config.get("FLASK_DEBUG", False), threaded=True)