# Create a Mongita database with movie information
import json
from mongita import MongitaClientDisk
import uuid

# create a mongita client connection
client = MongitaClientDisk()

# create a database
session_db = client.session_db

# create a session collection
session_collection = session_db.session_collection

# empty the collection
session_collection.delete_many({})

def create_session(username):
    session_id = str(uuid.uuid4())
    session_collection.insert_one({'session_id': session_id, 'user': username})
    return session_id

# make sure the session are there
print(session_collection.count_documents({}))
