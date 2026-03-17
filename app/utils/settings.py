from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database settings
    DB_PATH: str = "emails.db"
    POLL_INTERVAL_MINUTES: int = 5  # Minutes between each poll cycle
    # Agent settings
    FIRST_MONITOR_CAP: int = 10  # Max emails to fetch per run

settings = Settings()