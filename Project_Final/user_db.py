# Create a Mongita database 
import json
from mongita import MongitaClientDisk
from werkzeug.security import generate_password_hash

# create a mongita client connection
client = MongitaClientDisk()

# create a database
user_db = client.user_db

#create a session collection
user_collection = user_db.user_collection



# empty the collection
#user_collection.delete_many({})

def create_user(username, password):
    password_hash = generate_password_hash(password)
    user_collection.insert_one({'user': username, 'password_hash': password_hash})

# make sure the session are there
print(user_collection.count_documents({}))