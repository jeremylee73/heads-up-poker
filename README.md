#### Project Overview:

My project is called Heads Up Poker, a game where a user can play a 1-on-1 No Limit Texas Hold-em Poker game against a bot I designed.
At the start of every game, each player is assigned 100 chips with the small blind being 1 chip and the big blind being 2 chips.
After each game, the user's wins and losses are recorded within their profile and can be viewed relationally to other players' records through the leaderboard.

For detailed rules on how to play poker, see this website: https://upswingpoker.com/poker-rules/texas-holdem-rules/

Here are a few clarifying tips:

--- Every time you make a move, the bot will make subsequent moves until it is your turn to move again.
    It may be confusing why after one hand in the small blind, the next hand also appears to be in the small blind.
    That's not an error; the next hand loaded with the bot in the small blind, and the bot just decided to fold immediately.
    If ever confused what happened, there is a log to the right of the screen that records your moves, the bot's moves, the betting street, and the winner of pots.

--- If you ever make a move and get a message saying it is invalid, don't worry. There are a few invalid moves in poker, such as:
        Checking when facing a raise, calling when not facing a raise, raising larger than your stack size,
        raising too small (a raise must be as much as the big blind (2), and if facing a bet, must be at least the opponent's bet plus a big blind),
        and folding when not facing a raise (this is technically not illegal, but there is no reason to do it, so it is not allowed)

--- If either you or the bot goes all-in during a hand, the betting will stop, and you will be taken directly to the showdown screen.
    Here you will see both of your hands and the board. You can take time to process each other's hands and who won (although the server will also do this for you).
    Once you are done looking, you can click Next Hand. If after the hand, one player has 0 chips, you will advance to the Play screen with a message that you won or lost.
    Otherwise, you will be redirected to the next hand and may continue to play.

#### How to Play:

# Step 1: Registering/Logging In

Click the Register button in the top right, where you can make an account with a username and password.
Once you are registered, you should be automatically logged in. If you ever want to leave the page and return to your account, you can do so through the Log In portal.

# Step 2: Start a game

Click the Play button in the top left, where you will see a red button that says "Start Game" if you haven't started a game yet, and "Resume Game" if you are currently in a game.
The game will start with you in the small blind position. From here, you can play the game out until either you or the bot wins.
If you ever want to leave and return to the game later, that's fine! The server will save your game automatically, and just by returning to the website and clicking "Resume Game," you can pick up where you left off.

# Step 3: Playing the bot

In the game itself, you will be able to see on the left are the action buttons (check, call, raise, fold), in the middle is the game, and on the right is the log.
Each time you make a move, the page will reload and the bot will make a subsequent move.
You do not have to wait for the bot to act, because after the reload, the log should confirm that the bot has acted.

#### Other Features:

# Profile Tab

To the right of the Play tab is the Profile tab, where you can see your username and record against the bot.
You may also change your password as long as you confirm your old password first.

# Leaderboard

The home screen shows the leaderboard, where you can compare yourself against other players.
You can always access this home screen by clicking the Heads Up Poker logo on the top left corner of the screen.
In this leaderboard, you will see every player's wins and losses.
Standings on the board are determined by points, which are simply calculated by doubling the number of wins and subtracting the number of losses.