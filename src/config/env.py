# src/config/env.py
import os

# Environment constants to avoid typos in comparisons
ENV_DEV = "dev"
ENV_PROD = "prod"

# Simple env flag: "dev" for local testing defaults, defaulting to "prod"
APP_ENV = os.getenv("APP_ENV", ENV_PROD).lower()
