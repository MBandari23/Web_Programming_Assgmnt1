from flask import Flask, render_template, request, make_response, redirect, flash, get_flashed_messages
from mongita import MongitaClientDisk
from bson import ObjectId
import hashlib
import random
import string
from werkzeug.security import check_password_hash, generate_password_hash
from session_db import create_session
from user_db import create_user
import os


app = Flask(__name__)
app.secret_key = os.urandom(24)

# create a mongita client connection
client = MongitaClientDisk()

# open the quotes database
quotes_db = client.quotes_db
session_db = client.session_db
user_db = client.user_db

import uuid

@app.route("/", methods=["GET"])
@app.route("/quotes", methods=["GET"])
def get_quotes():
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        response = redirect("/login")
        return response
    # open the session collection
    session_collection = session_db.session_collection
    # get the data for this session
    session_data = list(session_collection.find({"session_id": session_id}))
    if len(session_data) == 0:
        response = redirect("/logout")
        return response
    assert len(session_data) == 1
    session_data = session_data[0]
    # get some information from the session
    user = session_data.get("user", "unknown user")
    # open the quotes collection
    quotes_collection = quotes_db.quotes_collection
    quote_documents = quotes_collection.find({"owner": user})

    data = [doc for doc in quote_documents]
    for item in data:
        item["_id"] = str(item["_id"])
        item["object"] = ObjectId(item["_id"])
    # display the data
    html = render_template(
        "quotes.html",
        data=data,
        user=user,
    )
    response = make_response(html)
    response.set_cookie("session_id", session_id)
    return response


@app.route("/register", methods=["GET"])
def get_register():
    # Simply render the registration page
    return render_template("register.html")

@app.route("/register", methods=["POST"])
def post_register():
    username = request.form.get("user", "")
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if password != confirm_password:
        # Passwords do not match
        flash("Passwords do not match.")
        return redirect("/register")

    # Open the user collection
    user_collection = user_db.user_collection

    # Check if the user already exists
    if user_collection.find_one({"user": username}):
        flash("Username already exists.")
        return redirect("/register")

    # Hash the user's password
    password_hash = generate_password_hash(password)

    try:
        user_collection.insert_one({'user': username, 'password_hash': password_hash})
        flash("Registration successful! Please log in.")
    except Exception as e:
        flash("Failed to register. Error: " + str(e))
        return redirect("/register")
    print(f"Stored user: {username}, Hash: {password_hash}")  # Debug output
    # Log the user in by creating a new session
    #session_id = create_session(username) 
    #flash("Registration successful! Please log in.")
    # Redirect to quotes page with session_id set
    response = redirect("/login")
    #response.set_cookie("session_id", session_id, secure=True, httponly=True)  # Only set secure=True if using HTTPS
    return response


@app.route("/login", methods=["GET"])
def get_login():
    session_id = request.cookies.get("session_id", None)
    print("Pre-login session id = ", session_id)
    if session_id:
        return redirect("/quotes")
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def post_login():
    user = request.form.get("user", "")
    password= request.form.get("password", "")
    # open the user collection
    user_collection = user_db.user_collection
    #password_hash = generate_password_hash(password)
    # look for the user
    user_data = user_collection.find_one({'user': user})
    
    if user_data and check_password_hash(user_data['password_hash'], password):
            print("DB Hash:", user_data['password_hash'])
            print("Password Correct:", check_password_hash(user_data['password_hash'], password))
            session_id = str(uuid.uuid4())
            # open the session collection
            session_collection = session_db.session_collection
            # insert the user
            session_id = create_session(user)
            session_collection.delete_one({"session_id": session_id})
            session_data = {"session_id": session_id, "user": user}
            session_collection.insert_one(session_data)
            response = redirect("/quotes")
            response.set_cookie("session_id", session_id)
            print("Post-login session id = ", session_id)
            return response
            
    else:
            flash("Invalid username or password.")
            response = redirect("/login")
            response.delete_cookie("session_id")
            
    return response
    
    

@app.route("/logout", methods=["GET"])
def get_logout():
    # get the session id
    session_id = request.cookies.get("session_id", None)
    if session_id:
        # open the session collection
        session_collection = session_db.session_collection
        # delete the session
        session_collection.delete_one({"session_id": session_id})
    response = redirect("/login")
    response.delete_cookie("session_id")
    return response


@app.route("/add", methods=["GET"])
def get_add():
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        response = redirect("/login")
        return response
    return render_template("add_quote.html")


@app.route("/add", methods=["POST"])
def post_add():
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        response = redirect("/login")
        return response
    # open the session collection
    session_collection = session_db.session_collection
    # get the data for this session
    session_data = list(session_collection.find({"session_id": session_id}))
    if len(session_data) == 0:
        response = redirect("/logout")
        return response
    assert len(session_data) == 1
    session_data = session_data[0]
    # get some information from the session
    user = session_data.get("user", "unknown user")
    text = request.form.get("text", "")
    author = request.form.get("author", "")
    if text != "" and author != "":
        # open the quotes collection
        quotes_collection = quotes_db.quotes_collection
        # insert the quote
        quote_data = {"owner": user, "text": text, "author": author}
        quotes_collection.insert_one(quote_data)
        
    # usually do a redirect('....')
    return redirect("/quotes")


@app.route("/edit/<id>", methods=["GET"])
def get_edit(id=None):
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        response = redirect("/login")
        return response
    if id:
        # open the quotes collection
        quotes_collection = quotes_db.quotes_collection
        # get the item
        data = quotes_collection.find_one({"_id": ObjectId(id)})
        data["id"] = str(data["_id"])
        return render_template("edit.html", data=data)
    # return to the quotes page
    return redirect("/quotes")


@app.route("/edit", methods=["POST"])
def post_edit():
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        response = redirect("/login")
        return response
    _id = request.form.get("_id", None)
    text = request.form.get("text", "")
    author = request.form.get("author", "")
    if _id:
        # open the quotes collection
        quotes_collection = quotes_db.quotes_collection
        # update the values in this particular record
        values = {"$set": {"text": text, "author": author}}
        data = quotes_collection.update_one({"_id": ObjectId(_id)}, values)
    # do a redirect('....')
    return redirect("/quotes")


@app.route("/delete", methods=["GET"])
@app.route("/delete/<id>", methods=["GET"])
def get_delete(id=None):
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        response = redirect("/login")
        return response
    if id:
        # open the quotes collection
        quotes_collection = quotes_db.quotes_collection
        # delete the item
        quotes_collection.delete_one({"_id": ObjectId(id)})
    # return to the quotes page
    return redirect("/quotes")

#if __name__ == '__main__':
   # app.run(host='127.0.0.1', port=5000)