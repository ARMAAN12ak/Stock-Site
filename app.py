import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    if request.method=="GET":
        un1=db.execute("SELECT username FROM users WHERE id=?",session["user_id"])
        un=un1[0]["username"]
        shares=[]
        n=db.execute("SELECT COUNT(*) FROM net WHERE username = ?",un)
        tot=0.0
        p=0
        curcsh1=db.execute("SELECT cash FROM users WHERE username = ?",un)
        curcsh=curcsh1[0]["cash"]
        curcsh = round(curcsh, 2)
        for i in range(n[0]['COUNT(*)']):
            t=db.execute("SELECT sharename,nos FROM net WHERE username =?",un)
            lk=lookup(t[i]["sharename"])
            tot= tot + float(lk["price"]) * float(t[i]["nos"])
            tot = round(tot, 2)
            ls=[]
            ls.append(t[i]["sharename"])
            ls.append(int(t[i]["nos"]))
            ls.append(round(lk["price"], 2))
            ls.append(round(int(t[i]["nos"])*lk["price"], 2))
            shares.append(ls)
        return render_template("ind.html",un=un,shares=shares,curcsh=curcsh,tot=tot,p=10000)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Blank symbol",403)
        if not request.form.get("shares"):
            return apology("Blank shares",403)
        if int(request.form.get("shares"))<=0:
            return apology("give shares number greater than zero",403)
        lk=lookup(request.form.get("symbol"))
        if lk==None:
            return apology("no such share exists",403)
        un1=db.execute("SELECT username FROM users WHERE id=?",session["user_id"])
        un=un1[0]["username"]
        nos=request.form.get("shares")
        prc=lk["price"]
        csh=db.execute("SELECT cash FROM users WHERE username = ?", un)
        if int(nos)*float(prc)>csh[0]["cash"]:
            return apology("u dont have enough money to purchase this number of shares")
        tm=db.execute("SELECT CURRENT_TIMESTAMP")
        sh=request.form.get("symbol").lower()
        db.execute("INSERT INTO tran (username, tag, sharename, coes, nos, datentime) VALUES(?, ?, ?, ?, ?, ?)",un , 'B', sh, lk["price"], int(request.form.get("shares")), tm[0]["CURRENT_TIMESTAMP"])
        cs=csh[0]["cash"]-int(nos)*float(prc)
        db.execute("UPDATE users SET cash=? WHERE username=?",cs,un)
        if db.execute("SELECT nos FROM net WHERE username = ? AND sharename = ?",un,sh):
            n=db.execute("SELECT nos FROM net WHERE username = ? AND sharename = ?",un,sh)
            db.execute("UPDATE net SET nos=? WHERE username=? AND sharename = ?",n[0]['nos']+int(nos),un,sh)
        else:
            db.execute("INSERT INTO net (username,sharename,nos) VALUES(?,?,?)",un,sh,int(nos))
        return redirect("/")
    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    nm1=db.execute("SELECT username FROM users WHERE id=?",session["user_id"])
    nm=nm1[0]["username"]
    n=db.execute("SELECT COUNT(*) FROM tran WHERE username=?",nm)
    infos=[]
    for i in range(n[0]['COUNT(*)']):
        t=db.execute("SELECT sharename,nos,coes,tag,datentime FROM tran WHERE username =?",nm)
        ls=[]
        ls.append(t[i]["sharename"])
        ls.append(t[i]["nos"])
        ls.append(t[i]["coes"])
        ls.append(t[i]["tag"])
        ls.append(t[i]["datentime"])
        infos.append(ls)
    return render_template("history.html",infos=infos)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("must provide symbol", 403)
        lk=lookup(request.form.get("symbol"))
        if lk==None:
            return apology("not found", 403)
        return render_template("quote.html", lk=lk)
    return render_template("quoted.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 403)
        nm = db.execute("SELECT username FROM users WHERE username = ?", request.form.get("username"))
        if nm==request.form.get("username"):
            return apology("username already exists", 403)
        if not request.form.get("password"):
            return apology("must provide password", 403)
        if not (len(request.form.get("password")) >= 5 and sum(char.isdigit() for char in request.form.get("password")) >= 2 and sum(char in "!@#$%^&*()_+-=[]{}|;:'\",./<>?" for char in request.form.get("password")) >= 1 and sum(char.isalpha() for char in request.form.get("password")) >= 5):
            return apology("password must contain a minimum of 5 letters , 2 numbers and 1 special character")
        if not request.form.get("confirmation"):
            return apology("must provide confirmation password", 403)
        ps = request.form.get("password")
        if ps!=request.form.get("confirmation"):
            return apology("must provide a correct confirmation password", 403)
        db.execute("INSERT INTO users (username, hash , cash) VALUES(?, ?, ?)", request.form.get("username"), generate_password_hash(request.form.get("password")), 10000.00)
        return redirect("/")
    return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    un1=db.execute("SELECT username FROM users WHERE id=?",session["user_id"])
    un=un1[0]["username"]
    stocks=db.execute("SELECT sharename FROM net WHERE username=?",un)
    ls=[]
    n=db.execute("SELECT COUNT(*) FROM net WHERE username=?",un)
    print(n)
    for i in range(n[0]["COUNT(*)"]):
        ls.append(stocks[i]["sharename"])
    stocks=ls
    if request.method=="POST":
        if request.form.get("stockname")==None:
            return apology("select a stockname from drop down menu")
        if not request.form.get("shares"):
            return apology("give some number of shares")
        sh=request.form.get("stockname").lower()
        if int(request.form.get("shares"))<=0:
            return apology("give shares number greater than zero")
        nos1=db.execute("SELECT nos FROM net WHERE username=? AND sharename=?",un,sh)
        nos=nos1[0]["nos"]
        if nos==0:
            return apology("u dont have any shares of this company left please select some other share")
        if nos<int(request.form.get("shares")):
            return apology("u dont have that much shares to sell")
        tm=db.execute("SELECT CURRENT_TIMESTAMP")
        lk=lookup(sh)
        csh=db.execute("SELECT cash FROM users WHERE username = ?", un)
        cs=csh[0]["cash"]+int(request.form.get("shares"))*(float(lk["price"]))
        db.execute("UPDATE users SET cash=? WHERE username=?",cs,un)
        db.execute("INSERT INTO tran (username,tag,sharename,coes,nos,datentime) VALUES(?,?,?,?,?,?)", un, 'S', sh, lk["price"], request.form.get("shares"), tm[0]["CURRENT_TIMESTAMP"])
        db.execute("UPDATE net SET nos=? WHERE username=? AND sharename = ?",nos-int(request.form.get("shares")),un,sh)
        return redirect("/")
    return render_template("sell.html",stocks=stocks)
