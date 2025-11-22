# src/config/env.py
import os

# Simple env flag: "dev" for local testing defaults, defaulting to "prod"
APP_ENV = os.getenv("APP_ENV", "prod").lower()
