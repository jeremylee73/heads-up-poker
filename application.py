import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required, render_hand, compare_hands, bot_strength, bot_action, next_street, showdown, reset, all_in, win, points

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///poker.db")


@app.route("/")
@login_required
def index():
    # Sends in list of users ordered by points to be displayed on leaderboard
    users = db.execute("SELECT * FROM users")
    users.sort(reverse=True, key=points)
    return render_template("index.html", users=users)


@app.route("/play")
@login_required
def play():
    # Checks for an active game. Shows start game button if no active game and resume game button if active
    active_game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session["user_id"])
    active = False
    if len(active_game) > 0:
        active = True
    return render_template("play.html", active=active)


@app.route("/profile", methods=["GET","POST"])
@login_required
def profile():

    user = db.execute("SELECT * FROM users WHERE id = ?", session['user_id'])[0]

    if request.method == "GET":

        return render_template("profile.html", user=user)

    if request.method == "POST":

        # Checks that user inputted old and new passwords
        if not request.form.get("old_password"):
            flash("Must input old password")
            return redirect("/profile")
        if not request.form.get("new_password"):
            flash("Must input new password")
            return redirect("/profile")

        old = request.form.get("old_password")

        # Checks that old password matches password in database
        if not check_password_hash(user['password'], old):
            flash("Old password does not match")
            return redirect("/profile")

        new = request.form.get("new_password")
        new_hash = generate_password_hash(new)

        # Updates to new password
        db.execute("UPDATE users SET password = ? WHERE id = ?", new_hash, session["user_id"])
        flash("Successfully changed password!")

        return redirect("/profile")


@app.route("/game", methods=["GET", "POST"])
@login_required
def game():

    if request.method == "GET":

        game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session["user_id"])
        entries = db.execute("SELECT * FROM entries WHERE log_id = (SELECT id FROM logs WHERE game_id = (SELECT id FROM games WHERE player_id = ? AND active = 1))", session["user_id"])
        username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])[0]['username']

        # Checks if user is in active game
        if len(game) > 0:

            game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session["user_id"])[0]
            log_id = db.execute("SELECT id FROM logs WHERE game_id = (SELECT id FROM games WHERE player_id = ? AND active = 1)", session["user_id"])[0]['id']

            # Checks if user just came from showdown
            if game['displayed'] == 1:

                # If user or bot won, end game and redirect to play
                win_status = win(session["user_id"])
                if win_status == 1:
                    flash("You Won!")
                    return redirect("/play")
                if win_status == 2:
                    flash("You Lost!")
                    return redirect("/play")

                # Reset hands, board, and position
                reset(session["user_id"])

                # Calculates bot's new hand strength
                hand_strength = bot_strength(session["user_id"])

                # Updates game to represent new hands, board, and position
                game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session["user_id"])[0]

                # If in the big blind, let the bot make the first move
                if game['position'] == "bb":
                    bot_move = bot_action(hand_strength, session["user_id"])
                    db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", bot_move, log_id)
                    # If bot folds, reset the board again
                    if bot_move == "Opponent folds":
                        db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", username + " wins pot of 3", log_id)
                        reset(session["user_id"])

                # Set displayed to 0
                db.execute("UPDATE games SET displayed = 0 WHERE player_id = ? AND active = 1", session["user_id"])

                # Updates game to represent new hands, board, and position
                game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session["user_id"])[0]
                entries = db.execute("SELECT * FROM entries WHERE log_id = ?", log_id)

            return render_template("game.html", hand=game['hand'], opp_hand=game['opp_hand'], board=game['board'], street=game['street'], position=game['position'], chips=game['chips'], opp_chips=game['opp_chips'], pot=game['pot'], bet=game['bet'], opp_bet=game['opp_bet'], entries=entries)

        # Renders hand
        hand_info = render_hand()

        # Creates new game
        db.execute("INSERT INTO games (player_id, active, chips, opp_chips, pot, position, street, hand, opp_hand, board, bet, opp_bet, displayed) VALUES (?, 1, 99, 98, 0, 'sb', 'preflop', ?, ?, ?, 1, 2, 0)", session["user_id"], hand_info['hand'], hand_info['opp_hand'], hand_info['board'])

        # Create new log
        db.execute("INSERT INTO logs (game_id) SELECT id FROM games WHERE player_id = ? AND active = 1", session["user_id"])

        # Adds Preflop: as the first entry of the log
        log_id = db.execute("SELECT id FROM logs WHERE game_id = (SELECT id FROM games WHERE player_id = ? AND active = 1)", session["user_id"])[0]['id']
        db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", "Preflop:", log_id)

        entries = db.execute("SELECT * FROM entries WHERE log_id = ?", log_id)

        return render_template("game.html", hand=hand_info['hand'], opp_hand=hand_info['opp_hand'], board=hand_info['board'], street="preflop", position="sb", chips=99, opp_chips=98, pot=0, bet=1, opp_bet=2, entries=entries)

    if request.method == "POST":

        game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session["user_id"])[0]
        username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])[0]['username']
        log_id = db.execute("SELECT id FROM logs WHERE game_id = (SELECT id FROM games WHERE player_id = ? AND active = 1)", session["user_id"])[0]['id']
        hand_strength = bot_strength(session["user_id"])

        """PLAYER CALLS"""
        if "call" in request.form.to_dict():

            # Checks for invalid calls
            if game['bet'] >= game['opp_bet']:
                flash("Invalid Call")
                return redirect("/game")

            # Updates user's chips
            db.execute("UPDATE games SET chips = ? WHERE player_id = ? AND active = 1", game['chips'] - game['opp_bet'] + game['bet'], session["user_id"])

            # Updates user's bet
            db.execute("UPDATE games SET bet = ? WHERE player_id = ? AND active = 1", game['opp_bet'], session["user_id"])

            # Logs user's call
            db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", username + " calls", log_id)

            # If the call puts the user all in, go to showdown
            if all_in(session["user_id"]) == 1:
                while game['street'] != "river":
                    next_street(session["user_id"])
                    game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session["user_id"])[0]
                showdown(session["user_id"])
                db.execute("UPDATE games SET displayed = 1 WHERE player_id = ? AND active = 1", session["user_id"])
                return redirect("/display")

            # If it is preflop and player is calling the big blind, the bot can still move
            elif game['street'] == "preflop" and game['opp_bet'] == 2:
                bot_move = bot_action(hand_strength, session["user_id"])
                db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", bot_move, log_id)
                # If bot checks, ends action and goes to next street, where if player is in the small blind, the bot acts again.
                if bot_move == "Opponent checks":
                    next_street(session["user_id"])
                    if game['position'] == "sb":
                        bot_move2 = bot_action(hand_strength, session["user_id"])
                        db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", bot_move2, log_id)

            # When the call ends action, go to the next street. If the player is in the small blind, the bot acts first.
            elif game['street'] != "river":
                next_street(session["user_id"])
                if game['position'] == "sb":
                    bot_move = bot_action(hand_strength, session["user_id"])
                    db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", bot_move, log_id)

            # When the call ends action on the river, go to showdown
            else:
                showdown(session["user_id"])
                db.execute("UPDATE games SET displayed = 1 WHERE player_id = ? AND active = 1", session["user_id"])
                return redirect("/display")

            return redirect("/game")

        """PLAYER RAISES"""
        if "raise" in request.form.to_dict():

            # Checks for invalid raises
            if not request.form.get("raise_size"):
                flash("Must enter raise size")
                return redirect("/game")
            raise_size = int(request.form.get("raise_size"))
            if (game['bet'] < game['opp_bet'] and raise_size < game['opp_bet'] + 2 and raise_size != game['chips']) or raise_size < 2 or raise_size <= game['bet']:
                flash("Invalid raise size (must min raise)")
                return redirect("/game")
            if raise_size > game['chips'] + game['bet']:
                flash("Not enough chips")
                return redirect("/game")

            # If raise size is larger than bot's stack, adjust so it is exactly all in
            if raise_size > game['opp_chips'] + game['opp_bet']:
                raise_size = game['opp_chips'] + game['opp_bet']

            # Updates bet size
            db.execute("UPDATE games SET bet = ? WHERE player_id = ? AND active = 1", raise_size, session["user_id"])

            # Updates user's stack
            db.execute("UPDATE games SET chips = ? WHERE player_id = ? AND active = 1", game['chips'] - raise_size + game['bet'], session["user_id"])

            # Logs user's raise
            db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", username + " raises to " + str(raise_size), log_id)

            # Saves board state for log entry later
            game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session["user_id"])[0]

            # Bot moves and logs it
            bot_move = bot_action(hand_strength, session["user_id"])
            db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", bot_move, log_id)

            if bot_move == "Opponent folds":

                # Logs user winning pot
                username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])[0]['username']
                db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", username + " wins pot of " + str(game['bet'] + game['opp_bet'] + game['pot']), log_id)

                # Resets hands, board, and position and updates game
                reset(session["user_id"])
                game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session["user_id"])[0]

                # If new position is big blind, let bot move
                if game['position'] == "bb":

                    # Updates hand strength
                    hand_strength = bot_strength(session["user_id"])

                    # Bot moves and logs it
                    bot_move2 = bot_action(hand_strength, session["user_id"])
                    db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", bot_move2, log_id)

                    # If the bot folds, logs user winning the pot and resets the board
                    if bot_move2 == "Opponent folds":
                        db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", username + " wins pot of 3", log_id)
                        reset(session["user_id"])

            if bot_move == "Opponent calls":

                # If bot calls all in, go to showdown
                if all_in(session["user_id"]) == 1:
                    while game['street'] != "river":
                        next_street(session["user_id"])
                        game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session["user_id"])[0]
                    showdown(session["user_id"])
                    db.execute("UPDATE games SET displayed = 1 WHERE player_id = ? AND active = 1", session["user_id"])
                    return redirect("/display")

                # If bot calls and it's not the river, advance to next street
                elif game['street'] != "river":
                    next_street(session["user_id"])
                    # If user is in the small blind, let the bot act first
                    if game['position'] == "sb":
                        bot_move2 = bot_action(hand_strength, session["user_id"])
                        db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", bot_move2, log_id)

                # Otherwise, bot call ends action on the river and goes to showdown
                else:
                    showdown(session["user_id"])
                    db.execute("UPDATE games SET displayed = 1 WHERE player_id = ? AND active = 1", session["user_id"])
                    return redirect("/display")

            return redirect("/game")

        """PLAYER CHECKS"""
        if "check" in request.form.to_dict():

            # Checks for invalid checks
            if game['bet'] != game['opp_bet']:
                flash("Invalid check")
                return redirect("/game")

            # Logs user's check
            db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", username + " checks", log_id)

            # If the user is in the small blind, check ends action
            if game['position'] == "sb":
                if game['street'] != "river":
                    next_street(session["user_id"])
                    bot_move = bot_action(hand_strength, session["user_id"])
                    db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", bot_move, log_id)
                else:
                    showdown(session["user_id"])
                    db.execute("UPDATE games SET displayed = 1 WHERE player_id = ? AND active = 1", session["user_id"])
                    return redirect("/display")

            # If not preflop and in the big blind, check gives next move to the bot
            elif game['street'] != "preflop":

                # Bot moves and logs it
                bot_move = bot_action(hand_strength, session["user_id"])
                db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", bot_move, log_id)

                # If bot checks, ends action
                if bot_move == "Opponent checks":
                    if game['street'] != "river":
                        next_street(session["user_id"])
                    else:
                        showdown(session["user_id"])
                        db.execute("UPDATE games SET displayed = 1 WHERE player_id = ? AND active = 1", session["user_id"])
                        return redirect("/display")

            # If preflop and in the big blind, check ends action and goes to next street
            else:
                next_street(session["user_id"])

            return redirect("/game")

        """PLAYER FOLDS"""
        if "fold" in request.form.to_dict():

            # Checks for invalid folds
            if game['bet'] == game['opp_bet']:
                flash("Invalid fold")
                return redirect("/game")

            # Gives pot and bets to opp stack
            db.execute("UPDATE games SET opp_chips = ? WHERE player_id = ? AND active = 1", game['opp_chips'] + game['bet'] + game['opp_bet'] + game['pot'], session["user_id"])

            # Logs fold and opponent winning pot
            db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", username + " folds", log_id)
            db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", "Opponent wins pot of " + str(game['bet'] + game['opp_bet'] + game['pot']), log_id)

            # Clears pot and bets
            db.execute("UPDATE games SET pot = ?, bet = ?, opp_bet = ? WHERE player_id = ? AND active = 1", 0, 0, 0, session["user_id"])

            # Resets hands and board
            reset(session["user_id"])

            # Updating bot's hand strength and game state
            hand_strength = bot_strength(session["user_id"])
            game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session["user_id"])[0]

            # If user is in the big blind next hand, bot acts first
            if game['position'] == "bb":

                bot_move = bot_action(hand_strength, session["user_id"])
                db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", bot_move, log_id)

                # If bot folds next hand, reset and advance
                if bot_move == "Opponent folds":
                    db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", username + " wins pot of 3", log_id)
                    reset(session["user_id"])

            return redirect("/game")

        return redirect("/game")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Must enter username")
            return redirect("/register")
        duplicate = db.execute("SELECT id FROM users WHERE username = ?", request.form.get("username"))
        if len(duplicate) > 0:
            flash("Username already taken")
            return redirect("/register")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Must enter password")
            return redirect("/register")

        elif not request.form.get("confirmation"):
            flash("Must confirm password")
            return redirect("/register")

        elif request.form.get("password") != request.form.get("confirmation"):
            flash("Passwords must match")
            return redirect("/register")

        db.execute("INSERT INTO users (username, password, wins, losses) VALUES (?, ?, 0, 0)", request.form.get(
            "username"), generate_password_hash(request.form.get("password")))

        session["user_id"] = db.execute("SELECT id FROM users WHERE username = ?", request.form.get("username"))[0]["id"]

        flash("Registered!")

        return redirect("/")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Must enter username")
            return redirect("/login")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Must enter password")
            return redirect("/login")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["password"], request.form.get("password")):
            flash("Invalid username or password")
            return redirect("/login")

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


@app.route("/display")
def display():
    """Display showdown"""

    game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session["user_id"])[0]

    return render_template("display.html", hand=game['hand'], opp_hand=game['opp_hand'], board=game['board'])
