# Design Choices

# Account Handling

I decided to have SQL table called users to store every user's information (username, password, wins, and losses).
I created register and log in pages similar to those in CS50 Finance. Both pages use forms to submit post requests, which subsequently update the database.
This table was helpful because it allowed people to store their records against the bot.
It also helped assign games to players, making it such that a player can leave their game and resume it later at the same point.

# Game Functionality

The game's functionality relies on the SQL table called games.
The table stores all relevant information about any given game:
    Player's id, whether the game is active, player's chips, opponent's chips, pot size,
    betting street, player's hand, opponent's hand, board, player's bet, and opponent's bet.
The game functions by constantly updating this table whenever the player makes a move, the bot makes a move, the betting street advances, etc.

#### Hands and Board Generation

To generate hands and a board, I created a helper function in helpers.py called render_hand().
This function creates a deck and uses helper functions like draw_card() to create hands and a board that are ensured to not have overlapping cards.
It returns a dictionary of hand, opp_hand, and board as keys. This function was helpful because it needed to be called at the start of every hand.

#### Hand Comparison Algorithm

I next created a hand comparison function in helpers.py called compare_hands that takes in two hands and a board and outputs the winner.
This function required many helper functions to check for the existence of all possible poker hands (quads, full house, flush, etc.)
In compare_hands, I checked for each hand from strongest to weakest, returning the player with the stronger hand.
If both players have the same strength hand, the algorithm checks for tie-breakers (aka kickers).
If both players have the exact same 5-card hand, the function returns that it is a chop pot.

#### User Actions (check, call, raise, fold)

On the game page, there are buttons for the user's actions. Each is represented on the backend by a form that sends a post request to /game.
I created if statements to see which button the user pressed, and within themm, I wrote their functionality.
The first thing I did was check for invalid moves (as described in README.md).
Next, I updated the games table to change the state of the game.
    For example, a call would set the user's bet equal to the opponent's bet and decrease the user's stack accordingly.
Then, I checked if the user's move would end the action (i.e. advances the betting street).
    For example, a check in the small blind always ends the action as long as it isn't preflop.
    Another example, a call always ends the action unless calling the big blind during preflop.
If the user's move ends the action, the function next_street() is called unless the current street is the river.
    I programmed this function to update the games table, adding the user and opponent's bets to the pot and updating the street.
    The program then checks if the opponent is on the big blind, because if so, it allows the bot to move first.
If the current street is the river, the showdown() and reset() functions are called.
    showdown() compares the user's hand to the opponent's and assigned the pot's chips accordingly.
    reset() advances the games table to the next hand, switching the user's position, clearing the pot, and dealing new hands and a new board.
If the user's move does not end the action, the bot is allowed to move.
    The program then checks if the bot's move ends the action and repeats the steps above.

The steps I took to design this aspect of the game were the hardest because I had to consider many edge cases.
It is also because I decided to have the bot move after every user move (which is also a post request).
Every reload has the bot making moves behind the scenes, which means the user never sees the bot move synchronously.
I designed the game this way because it was allowed me to use the tools of CS50 to change SQL tables after every post request and redirect back to /game at the end.
This design choice also made it simpler for me to not have to check for a user's timing. In other words, if my game were designed so that the
bot would move synchronously with some kind of delay, I would have to implement safeguards to make sure the user cannot act while the bot is moving.
The design that I chose is a little more confusing at first glance because an opponent can make multiple moves without you seeing them physically being done.
    For example, the bot can fold a hand and in the next hand fold immediately from the small blind. This would bring you to the following hand,
    where you might be wondering why you're in the same position two hands in a row.
To remedy this confusion, I created a log that carefully documents the user's actions, the bot's actions, betting streets, and pot winners. (More on that later)

# Bot Functionality

I programmed the bot using the helper function bot_action(). The bot creates an index indicating the strength of its hand.
This index is determined in bot_strength(), and finds the average probability of winning against a random hand given the board.
Based on the bot's perceived strength of their hand, they perform certain actions (as described below).

I originally wanted the bot to simulate every board and every of your possible hands, but that would require almost 52^7 combinations of hands.
When I tried this implementation, it was too expensive and caused my server to crash.
Therefore, I gave my bot knowledge of the board beforehand, so it could average the probability of beating any possible opposing hand.
This algorithm can seem unfair, since the bot knows the full board before the user can see it.
However, it is still beatable and not completely unfair since it does not know your hand and assumes that any of your possible hands are equally likely.

#### Bot Algorithm

Within bot_action(), I tried to make the bot somewhat unpredictable, so the player doesn't immediately know how strong the bot perceives its hand.
    With a very high strength index, the bot always raises.
    With a relatively high strength index, the bot sometimes raises and sometimes checks/calls.
    With a moderate strength index, the bot sometimes checks/calls and sometimes checks/folds.
    With a low strength index, the bot sometimes checks/folds and sometimes raises (as a bluff).

#### Determining when it is Bot's Move

There were two main scenarios where I could tell that it was the bot's turn to move and had to call the bot_action() function.
The first was at the beginning of a new betting street or a new hand.
    If the bot was in the small blind during preflop, it would act first.
    If the bot was in the big blind during the flop, turn, or river, it would act first.
The second was after the user made a move that did not end action.
    For example, any raise from the player would have to be responded to by a bot move.
    Another example, if the player checked from the big blind (except during preflop), the bot could either check back or raise.

# Log

The log was a design choice for me to make the game more user-friendly. For people not as familiar with poker, the log helps keep track of everything happening in a hand.
I implemented this with a two tables in my database. The table entries included a list of entries (e.g. "Opponent calls") and their respective log ids. The table logs was a linking table that connected an id to a game_id.
To make an entry in a given game, I added an entry to the entries table and set its log id to the id of the log associated with the game.

# Other Features

#### Profile Tab

The profile tab was rather simple to make. I used jinja to display the user's username and record.
I included a form at the bottom to change the user's password. The form sent a post request to /profile.
I first checked that the inputs were valid and that the old password matched the current password.
If everything lined up, I simply updated the users SQL table to include the hash of the new password.

#### Leaderboard

The leaderboard was also done through jinja, and I just had to import the users table into the template.
To sort the users by points, I made a helper function points(e) that returned the points of a given user.
I used python's built-in sort function to sort by points in reverse order before importing the list of users into the template.