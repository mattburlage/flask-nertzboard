from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp

import time

from helpers import *

room = "ivins"

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///nertz.db")

@app.route("/")
@login_required
def index():
    # get current username and get that user's stock holdings
    user = db.execute("SELECT username FROM users WHERE id IS :iden",iden=session["user_id"])
    curgame = db.execute("SELECT curgame FROM rooms WHERE room IS :room",room=room)
    players = db.execute("SELECT username FROM users WHERE room IS :room",room=room)
    returndata = []
    newgameloc = False

    # Check if new game
    newgamechk = db.execute("SELECT isnewgame FROM games WHERE game is :curgame",curgame=curgame[0]["curgame"])
    if newgamechk[0]["isnewgame"] == 1:
        db.execute("UPDATE games SET isnewgame = 0 WHERE game IS :curgame",curgame=curgame[0]["curgame"])
        newgameloc = True

    for player in players:

        gamedata = db.execute("SELECT * FROM hands WHERE user IS :user AND game IS :curgame",curgame=curgame[0]["curgame"],user=player["username"])
        rounddata = db.execute("SELECT count(pointswing) FROM hands WHERE user IS :user AND game IS :curgame",curgame=curgame[0]["curgame"],user=player["username"])
        if gamedata != None and rounddata[0]["count(pointswing)"] != 0:
            playerinfo = {}

            playerinfo["name"] = player["username"]
            scoredata = db.execute("SELECT sum(pointswing) FROM hands WHERE user IS :user AND game IS :curgame",curgame=curgame[0]["curgame"],user=player["username"])
            playerinfo["score"] = scoredata[0]["sum(pointswing)"]
            rounddata = db.execute("SELECT count(pointswing) FROM hands WHERE user IS :user AND game IS :curgame",curgame=curgame[0]["curgame"],user=player["username"])
            playerinfo["rounds"] = rounddata[0]["count(pointswing)"]

            returndata.append(playerinfo)

    # sort output by high score
    # sort_on = "score"
    # decorated = [(dict_[sort_on], dict_) for dict_ in returndata]
    # decorated.sort(reverse=1)
    # result = [dict_ for (key, dict_) in decorated]

    return render_template("index.html",user=user[0]["username"],room=room,curgame=curgame[0]["curgame"],players=returndata,newgame=newgameloc)


@app.route("/newgame", methods=["GET", "POST"])
def newgame():
    # create new game ID
    ngnum = db.execute("INSERT INTO games (room) VALUES (:room)",room=room)

    # set current room to new game ID
    db.execute("UPDATE rooms SET curgame = :curgame WHERE room IS :room",curgame=ngnum,room=room)

    # render personal scoreboard
    return redirect(url_for("index"))

@app.route("/submitscore", methods=["GET", "POST"])
@login_required
def submitscore():
    """Submit Nertz score"""
    if request.method == "POST":
        curgame = db.execute("SELECT curgame FROM rooms WHERE room IS :room",room=room)
        user = db.execute("SELECT username FROM users WHERE id IS :iden",iden=session["user_id"])

        pc = int(request.form.get("pointscards"))
        nc = int(request.form.get("nertzcards"))
        pointswing = (pc) - (nc * 2)

        db.execute("INSERT INTO hands (datetime, room, game, round, user, nertzcards, pointscards, pointswing) VALUES (:datetime, :room, :game, :curround, :user, :ncards, :pcards, :pswing)",datetime='soontm',room=room,game=curgame[0]["curgame"], curround=0,user=user[0]['username'],ncards=request.form.get("nertzcards"),pcards=request.form.get("pointscards"),pswing=pointswing)


    return redirect(url_for("index"))



@app.route("/history")
@login_required
def history():
    """Show history of transactions."""
    user = db.execute("SELECT username FROM users WHERE id IS :iden",iden=session["user_id"])
    transactionsdata = db.execute("SELECT * FROM ledger WHERE user IS :iden",iden=user[0]["username"])

    trans = []
    for tran in transactionsdata:
        traninfo = {}
        isbuy = ""
        if tran['qty'] > 0:
            isbuy = "BOUGHT"
        elif tran['qty'] < 0:
            isbuy = "SOLD"
        else:
            isbuy = "VOID"

        traninfo['datetime'] = tran['datetime']
        traninfo['isbuy'] = isbuy
        traninfo['symbol'] = tran['stock']
        traninfo['price'] = tran['price']
        traninfo['qty'] = abs(tran['qty'])

        trans.append(traninfo)


    return render_template("history.html", trans=trans)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]
        #curusers = db.execute("SELECT curusers FROM rooms WHERE room IS :room",room=room)
        #if not curusers[0].contains(request.form.get("username")):
        #    newcurusers = curusers[0] + request.form.get("username") + " "
        #    db.execute("UPDATE rooms SET curusers = :newcurusers WHERE room is :room",newcursuers=newcurusers,room=room)

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # TODO log user out of room
    #user = db.execute("SELECT username FROM users WHERE id IS :iden",iden=session["user_id"])
    #curusers = db.execute("SELECT curusers FROM rooms WHERE room IS :room",room=room)
    #newcurusers = curusers[0].replace(user[0] + " ", "")
    #db.execute("UPDATE rooms SET curusers = :newcurusers WHERE room is :room",newcursuers=newcurusers,room=room)

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        quote = lookup(request.form.get("stock"))
        if not quote:
            return apology("stock not found")

        return render_template("quotedisplay.html",name=quote["name"],symbol=quote["symbol"],price=quote["price"])
    else:
        return render_template("quote.html")
    return apology("TODO")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    if request.method == "POST":
        # ensure username was entered
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # ensure passwords match
        elif request.form.get("password") != request.form.get("passwordconf"):
            return apology("passwords don't match")

        # store entered values
        username = request.form.get("username")
        password = pwd_context.hash(request.form.get("password"))

        # ensure username not used
        result = db.execute("INSERT INTO users (username, hash, room) VALUES(:username, :hash, :room)",username=request.form.get("username"), hash=password, room=room)
        if not result:
            return apology("Username already taken")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))
    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    if request.method == "POST":
        username = db.execute("SELECT username FROM users WHERE id = :iden",iden = session["user_id"])
        quote = lookup(request.form.get("stock"))
        if not quote:
            return apology("stock not found")

        # check for symbol validity and ownership
        result = db.execute("SELECT owned FROM holdings WHERE stock IS :stock AND user IS :iden",iden = username[0]['username'],stock=quote["symbol"])
        if not result:
            return apology("Stock not owned")
        selling = request.form.get("shares")


        # check if user has enough stock to sell
        if result[0]["owned"] >= int(selling):
            # log in ledger
            username = db.execute("SELECT username FROM users WHERE id = :iden",iden = session["user_id"])
            db.execute("INSERT INTO ledger (datetime, user, stock, price, qty) VALUES(:datetime,:user,:stock,:price,:qty)",datetime=time.strftime('%Y-%m-%d %H:%M:%S'),user=username[0]["username"],stock=quote["symbol"],price=usd(quote["price"]),qty=0-int(selling))
            # update holdings
            result = db.execute("UPDATE holdings SET owned = owned - :selling WHERE user IS :user AND stock IS :stock",selling=selling,user=username[0]["username"],stock=quote["symbol"])
            # calculate and assign new cash on hand value
            cashonhand = db.execute("SELECT cash FROM users WHERE id = :iden",iden = session["user_id"])
            newcash = cashonhand[0]["cash"] + quote["price"]*float(selling)
            db.execute("UPDATE users SET cash = :newcash WHERE id IS :iden",newcash=newcash,iden=session["user_id"])
            return index()
        else:
            return apology("not enough stock")
    else:
        return render_template("sell.html")

