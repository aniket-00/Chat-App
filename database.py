# database.py
from pymongo import MongoClient
import os
import urllib.parse
from dotenv import load_dotenv
load_dotenv()

def get_db():
    password = os.getenv('MONGO_PWD')
    username = os.getenv('MONGO_USER')
    encoded_password = urllib.parse.quote_plus(password)
    cluster_name = 'cluster0'
    uri = f"mongodb+srv://{username}:{encoded_password}@{cluster_name}.pzqagzo.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

    client = MongoClient(uri)
    return client.Chat_app  # This returns the database directly

db = get_db()