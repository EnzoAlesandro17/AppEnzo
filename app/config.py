import os


class Config:
    SECRET_KEY = os.environ["SECRET_KEY"]
    DATABASE_PATH = os.environ["DATABASE_PATH"]
