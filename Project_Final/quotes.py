from flask import Flask, render_template, request, redirect, flash, url_for
from mongita import MongitaClientDisk
from bson import ObjectId
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from session_db import create_session
from user_db import create_user
import os
import uuid
from flask import jsonify


app = Flask(__name__)
app.secret_key = os.urandom(24)

# Create Mongita client connection
client = MongitaClientDisk()

# Open the databases and collections
quotes_db = client.quotes_db
session_db = client.session_db
user_db = client.user_db
comments_db = client.comments_db

quotes_collection = quotes_db.quotes_collection
session_collection = session_db.session_collection
user_collection = user_db.user_collection
comments_collection = comments_db.comments_collection

# Update the get_quotes route to fetch comments for each quote
# Update the get_quotes route to fetch comments for each quote
@app.route("/", methods=["GET"])
@app.route("/quotes", methods=["GET"])
def get_quotes():
    session_id = request.cookies.get("session_id")
    if not session_id:
        return redirect("/login")

    session_data = session_collection.find_one({"session_id": session_id})
    if not session_data:
        return redirect("/logout")

    user = session_data.get("user")
    quotes = list(quotes_collection.find({"owner": user}))

    for quote in quotes:
        quote["_id"] = str(quote["_id"])  # Ensure _id is JSON serializable
        # Fetch comments for each quote
        comments = list(comments_collection.find({"quote_id": quote["_id"]}))
        quote["comments"] = comments

    return render_template("quotes.html", quotes=quotes, user=user)



@app.route("/add_comment/<quote_id>", methods=["POST"])
def add_comment(quote_id):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    session_data = session_collection.find_one({"session_id": session_id})
    if not session_data:
        return jsonify({"success": False, "message": "Invalid session"}), 401

    user = session_data.get("user")
    comment_text = request.form.get("comment_text")

    if not comment_text:
        return jsonify({"success": False, "message": "Comment text cannot be empty"}), 400

    comment = {
        "text": comment_text,
        "user": user,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # MongoDB push operation to add comment
    result = quotes_collection.update_one(
        {"_id": ObjectId(quote_id)},
        {"$push": {"comments": comment}}
    )

    if result.modified_count == 1:
        return jsonify({"success": True, "comment": comment})
    else:
        return jsonify({"success": False, "message": "Failed to add comment"}), 500

    
# # Add a route to handle comment deletion
@app.route("/delete_comment/<comment_id>", methods=["POST"])
def delete_comment(comment_id):
    # Delete the comment from the database
    result = comments_collection.delete_one({"_id": ObjectId(comment_id)})
    if result.deleted_count == 1:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": "Failed to delete comment"}), 400



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
    # session_id = create_session(username)
    # flash("Registration successful! Please log in.")
    # Redirect to quotes page with session_id set
    response = redirect("/login")
    # response.set_cookie("session_id", session_id, secure=True, httponly=True)  # Only set secure=True if using HTTPS
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
    password = request.form.get("password", "")
    # open the user collection
    user_collection = user_db.user_collection
    # password_hash = generate_password_hash(password)
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
    source = request.form.get("source", "")
    date = request.form.get("date", datetime.today())
    is_public = 'is_public' in request.form
    comments_allowed = 'comments_allowed' in request.form
    if text != "" and author != "" and source != "" and date != "" and is_public != "" and comments_allowed != "":
        # open the quotes collection
        quotes_collection = quotes_db.quotes_collection
        # insert the quote
        quote_data = {"owner": user, "text": text, "author": author, "source": source, "date": date,
                      "is_public": is_public, "comments_allowed": comments_allowed}
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
    source = request.form.get("source", "")
    date = request.form.get("date", datetime.today())
    is_public = 'is_public' in request.form
    comments_allowed = 'comments_allowed' in request.form
    if text != "" and author != "" and source != "" and date != "" and is_public != "" and comments_allowed != "" and _id:
        # open the quotes collection
        quotes_collection = quotes_db.quotes_collection
        # update the values in this particular record
        values = {"$set": {"text": text, "author": author, "source": source, "date": date, "is_public": is_public,
                           "comments_allowed": comments_allowed}}
        data = quotes_collection.update_one({"_id": ObjectId(_id)}, values)
    # do a redirect('....')
    return redirect("/quotes")


@app.route("/delete/<quote_id>", methods=["POST"])
def delete_quote(quote_id):
    if request.method == "POST":
        # Delete the quote from the database
        result = quotes_collection.delete_one({"_id": ObjectId(quote_id)})
        if result.deleted_count == 1:
            # Redirect back to the quotes page after successful deletion
            return redirect(url_for("get_quotes"))
        else:
            # Handle the case where deletion fails
            flash("Failed to delete quote")
            return redirect(url_for("get_quotes"))  # Redirect to quotes page even if deletion fails
    else:
        # Handle other HTTP methods
        return jsonify({"error": "Method not allowed"}), 405





# if _name_ == '_main_':
# app.run(host='127.0.0.1', port=5000)