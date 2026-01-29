from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client.startup_platform

users_collection = db.users
ideas_collection = db.ideas
roles_collection = db.roles
funding_collection = db.funding
