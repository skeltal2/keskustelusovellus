from flask import Flask
from flask import redirect, render_template, request, session, abort
from werkzeug.security import check_password_hash, generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from os import getenv

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = getenv("DATABASE_URL")
app.secret_key = getenv("SECRET_KEY")

db = SQLAlchemy(app)

failed_login = False
user_name_taken = False

@app.route("/")
def index():
    return render_template("index.html", failedlogin = failed_login, usernametaken = user_name_taken)

# LOGIN AND USER CREATION

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    session["username"] = username

    sql = "SELECT password FROM users WHERE username=:username"
    result = db.session.execute(sql, {"username":username})
    user = result.fetchone()

    global failed_login
    failed_login = False

    # Is password correct?
    if user == None:
        del session["username"]
        failed_login = True
        return redirect("/")
    else:
        hash_value = user[0]
        if check_password_hash(hash_value, password):
            return redirect("/main")
        else:
            failed_login = True
            del session["username"]
            return redirect("/")

@app.route("/logout")
def logout():
    del session["username"]

    global failed_login
    failed_login = False

    global user_name_taken
    user_name_taken = False

    return redirect("/")

@app.route("/newuser", methods=["POST"])
def newuser():
    username = request.form["new_username"]
    password = request.form["new_password"]

    if password == "":
        return redirect("/")

    session["username"] = username

    global user_name_taken
    user_name_taken = False

    # Is username taken?
    try:
        hash_value = generate_password_hash(password)
        sql = "INSERT INTO users (username, password, admin) VALUES (:username,:password,:admin)"
        db.session.execute(sql, {"username":username, "password":hash_value, "admin":0})
        db.session.commit()
        return redirect("/main")
    except:
        del session["username"]
        user_name_taken = True
        return redirect("/")

# BOARD MANAGEMENT

@app.route("/main")
def main():
    sql = "SELECT * FROM boards"
    result = db.session.execute(sql)
    boards = result.fetchall()

    # Is current user admin?
    if session:
        sql = "SELECT admin FROM users WHERE username =:username"
        result = db.session.execute(sql, {"username":session["username"]})
        if result.fetchone()[0] == 1:
            admin = True
        else:
            admin = False
    else:
        admin = False

    return render_template("main.html", boards = boards, admin = admin)

@app.route("/main/<int:id>")
def board(id):
    # Is current user admin?
    if session:
        sql = "SELECT admin FROM users WHERE username =:username"
        result = db.session.execute(sql, {"username":session["username"]})
        if result.fetchone()[0] == 1:
            admin = True
        else:
            admin = False
    else:
        admin = False

    sql = "SELECT id, title FROM boards WHERE id=:id AND hidden = 0"
    result = db.session.execute(sql, {"id":id}).fetchone()

    try:
        # If board does not exist, return 404 error
        board_id = result[0]
        title = result[1]
    except:
        return abort(404)

    sql = "SELECT * FROM threads WHERE board_id=:board_id AND hidden = 0 ORDER BY id DESC"
    result = db.session.execute(sql, {"board_id":id})
    thread_data = result.fetchall()

    threads = []

    # Get uername and reply count
    for i in thread_data:
        sql = "SELECT COUNT(messages.id) FROM threads LEFT JOIN messages ON threads.id = messages.thread_id WHERE threads.id=:thread_id AND messages.hidden = 0;"
        result = db.session.execute(sql, {"thread_id":i[0]}).fetchone()[0]

        sql = "SELECT username FROM users WHERE id=:user_id"
        username = db.session.execute(sql, {"user_id":i[3]}).fetchone()[0]

        threads.append((i, result, username))

    return render_template(
        "board.html", title = title, threads = threads, id = board_id, admin = admin
        )

@app.route("/newboard", methods=["POST"])
def newboard():
    title = request.form["title"]

    sql = "INSERT INTO boards (title, hidden) VALUES (:title, 0)"
    db.session.execute(sql, {"title":title})
    db.session.commit()

    return redirect("/main")

#@app.route("/deleteboard", methods=["POST"])

# THREAD MANAGEMENT

@app.route("/<int:id>/newthread", methods=["POST"])
def newthread(id):
    title = request.form["title"]
    content = request.form["content"]
    user_id = db.session.execute("SELECT id FROM users WHERE username=:username", {"username":session["username"]}).fetchone()[0]
    board_id = id

    sql = "INSERT INTO threads (title, content, user_id, board_id, created_at, hidden) VALUES (:title, :content, :user_id, :board_id, NOW(), 0)"
    db.session.execute(sql, {"title":title, "content":content, "user_id":user_id, "board_id":board_id})
    db.session.commit()

    return redirect(f"/main/{board_id}")

@app.route("/main/<int:board_id>/<int:thread_id>")
def thread(board_id, thread_id):
    # Is current user admin?
    if session:
        sql = "SELECT admin FROM users WHERE username =:username"
        result = db.session.execute(sql, {"username":session["username"]})
        if result.fetchone()[0] == 1:
            admin = True
        else:
            admin = False
    else:
        admin = False

    sql = "SELECT * FROM threads WHERE id=:thread_id"
    result = db.session.execute(sql, {"thread_id":thread_id}).fetchall()[0]

    # Data for threads
    thread_title = result[1]
    thread_content = result[2]
    thread_time = result[5]

    sql = "SELECT COUNT(messages.id) FROM threads LEFT JOIN messages ON threads.id = messages.thread_id WHERE threads.id=:thread_id AND messages.hidden = 0;"
    reply_count = db.session.execute(sql, {"thread_id":thread_id}).fetchone()[0]

    sql = "SELECT username FROM users WHERE id=:id"
    thread_username = db.session.execute(sql, {"id":result[3]}).fetchone()[0]

    # Data for replies
    sql = "SELECT * FROM messages WHERE thread_id=:thread_id AND hidden = 0"
    result = db.session.execute(sql, {"thread_id":thread_id})
    messages_data = result.fetchall()

    messages = []

    # Get username for replies
    for i in messages_data:
        sql = "SELECT username FROM users WHERE id=:id"
        username = db.session.execute(sql, {"id":i[2]}).fetchone()
        messages.append((i, username))

    return render_template(
        "thread.html", board_id = board_id, thread_id = thread_id, thread_title = thread_title,
        thread_content = thread_content, thread_time = thread_time, thread_username = thread_username,
        messages = messages, reply_count = reply_count, admin = admin
        )

@app.route("/deletethread", methods=["POST"])
def deletethread():
    thread_id = request.form["thread_id"]
    board_id = request.form["board_id"]

    sql = "UPDATE threads SET hidden = 1 WHERE id=:thread_id"
    db.session.execute(sql, {"thread_id":thread_id})
    db.session.commit()

    return redirect("/main/" + str(board_id) )

# MESSAGE MANAGEMENT

@app.route("/reply", methods=["POST"])
def reply():
    board_id = request.form["board_id"]
    thread_id = request.form["thread_id"]

    content = request.form["content"]
    user_id = db.session.execute("SELECT id FROM users WHERE username=:username", {"username":session["username"]}).fetchone()[0]

    sql = "INSERT INTO messages (content, user_id, thread_id, created_at, hidden) VALUES (:content, :user_id, :thread_id, NOW(), 0);"
    db.session.execute(sql, {"content":content, "user_id":user_id, "thread_id":thread_id})
    db.session.commit()

    return redirect(f"/main/{board_id}/{thread_id}")

@app.route("/deletereply", methods=["POST"])
def deletereply():
    message_id = request.form["message_id"]
    board_id = request.form["board_id"]
    thread_id = request.form["thread_id"]

    sql = "UPDATE messages SET hidden = 1 WHERE id=:message_id"
    db.session.execute(sql, {"message_id":message_id})
    db.session.commit()

    return redirect(f"/main/{board_id}/{thread_id}")