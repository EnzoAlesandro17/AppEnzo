import os


class Config:
    SECRET_KEY = os.environ["SECRET_KEY"]
    DATABASE_URL = os.environ["DATABASE_URL"]
