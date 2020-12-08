import os
import requests
import urllib.parse
import random

from cs50 import SQL
from flask import redirect, render_template, request, session
from functools import wraps

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///poker.db")

def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


"""Draws random card from deck"""
def draw_card(deck):
    card = deck[random.randint(0,len(deck)-1)]
    remove_card(card, deck)
    return card


"""Returns two random cards"""
def deal_hand(deck):
    return draw_card(deck) + draw_card(deck)


"""Removes card from deck"""
def remove_card(card, deck):
    if card in deck:
        deck.remove(card)


"""Creates new hands and board"""
def render_hand():

    # Creates deck
    deck = []
    values = ["2","3","4","5","6","7","8","9","T","J","Q","K","A"]
    suits = ["C","H","D","S"]
    for i in range(13):
        for j in range(4):
            deck.append(values[i] + suits[j])

    # Deals hands
    hand = deal_hand(deck)
    opp_hand = deal_hand(deck)

    # Creates board
    board = ""
    for i in range(5):
        board += draw_card(deck)

    return {"hand":hand, "opp_hand":opp_hand, "board":board}


"""Returns 5-card flush in list, [0,0,0,0,0] if no flush"""
def flush(hand, board):

    all_cards = hand + board
    suits = all_cards[1::2] # String of all suits in hand and board

    # Creates dictionary of the number of cards of each suit
    suit_count = {}
    for suit in suits:
        if suit not in suit_count:
            suit_count[suit] = 1
        else:
            suit_count[suit] += 1

    # Sets flush_suit to suit with 5 or more instances
    flush_suit = ""
    for suit in suit_count:
        if suit_count[suit] >= 5:
            flush_suit = suit

    # Exits if no flush
    if flush_suit == "":
        return [0,0,0,0,0]

    # Creates array of all numbers of the flush suit, converts face cards to their respective values
    ans = []
    face_card_vals = {"T":10, "J":11, "Q":12, "K":13, "A":14}
    for i in range(len(all_cards)):
        if all_cards[i] == flush_suit:
            if all_cards[i-1] in face_card_vals:
                ans.append(face_card_vals[all_cards[i-1]])
            else:
                ans.append(int(all_cards[i-1]))

    # Sorts array from high to low and truncates to highest 5 numbers
    ans.sort(reverse=True)
    ans = ans[:5]

    return ans


"""Returns high card of straight or 0 if no straight"""
def straight(hand, board):

    all_cards = hand + board
    nums = all_cards[::2] # String of all numbers in hand and board

    # Creates an array of all numbers in hand and board, converts face cards to their respective values
    numlist = []
    for num in nums:
        face_card_vals = {"T":10, "J":11, "Q":12, "K":13, "A":14}
        if num in face_card_vals:
            numlist.append(face_card_vals[num])
        else:
            numlist.append(int(num))

    # Sorts array from low to high
    numlist.sort()

    # If Ace in cards, also count it as 1
    if numlist[len(numlist)-1] == 14:
        numlist.append(1)
        numlist.sort()

    # General Case
    isstraight = True
    # Iterates through numlist 3 times because there are at most 3 straights given 7 cards
    for i in range(3):
        isstraight = True
        # Starts from highest card in numlist (at the end) and checks if 4 consequtively decreasing numbers are in numlist. If not, checks the second highest card in numlist, then third
        for j in range(4):
            if numlist[len(numlist)-1-i] - j - 1 not in numlist:
                isstraight = False
        # If straight exists, return the top card in the sequence
        if isstraight:
            return numlist[len(numlist)-1-i]

    return 0


"""Returns dictionary with count of each number in a list of cards"""
def create_num_count_dict(nums):
    face_card_vals = {"T":10, "J":11, "Q":12, "K":13, "A":14}
    ans = {}
    for num in nums:
        if num in face_card_vals:
            num_val = face_card_vals[num]
        else:
            num_val = int(num)

        if num_val not in ans:
            ans[num_val] = 1
        else:
            ans[num_val] += 1

    return ans


"""Returns list of kickers given two exceptions"""
def create_kickers(num_count, e1, e2):
    ans = []
    for num in num_count:
        if num != e1 and num != e2:
            ans.append(num)
    ans.sort(reverse=True)
    return ans


"""Returns [four of a kind, kicker] or [0, 0] if none"""
def four_of_a_kind(hand, board):

    all_cards = hand + board
    nums = all_cards[::2] # String of all numbers in hand and board

    # Creates dictionary of the number of instances of each number, converts face cards into their respective values
    num_count = create_num_count_dict(nums)

    # Sets quad to the number with 4 instances, 0 if none exist
    quad = 0
    for num in num_count:
        if num_count[num] == 4:
            quad = num

    # Sets list of kickers in decreasing order
    kickers = create_kickers(num_count, quad, 0)

    if quad > 0:
        return [quad,kickers[0]]

    return [0,0]


"""Returns [three of a kind, kicker 1, kicker 2] and [0, 0, 0] if none"""
def three_of_a_kind(hand, board):

    all_cards = hand + board
    nums = all_cards[::2] # String of all numbers in hand and board

    # Creates dictionary of the number of instances of each number, converts face cards into their respective values
    num_count = create_num_count_dict(nums)

    # Sets triple to the number with 3 instances, 0 if none exist
    triple = 0
    for num in num_count:
        if num_count[num] == 3 and num > triple:
            triple = num

    # Sets list of kickers in decreasing order
    kickers = create_kickers(num_count, triple, 0)

    if triple > 0:
        return [triple, kickers[0], kickers[1]]

    return [0,0,0]


"""Returns array of [triple, pair] or [0,0] if none"""
def full_house(hand, board):

    all_cards = hand + board
    nums = all_cards[::2] # String of all numbers in hand and board

    # Creates dictionary of the number of instances of each number, converts face cards into their respective values
    num_count = create_num_count_dict(nums)

    # Sets triple to the highest number with 3 instances, 0 if none exist
    triple = 0
    for num in num_count:
        if num_count[num] == 3 and num > triple:
            triple = num

    # Sets pair to the highest number with 2 instances, 0 if none exist
    pair = 0
    for num in num_count:
        if num_count[num] >= 2 and num > pair and num != triple:
            pair = num

    if triple > 0 and pair > 0:
        return [triple,pair]

    return [0,0]


"""Returns array of [high pair, low pair, kicker] or [0, 0, 0] if none"""
def two_pair(hand, board):

    all_cards = hand + board
    nums = all_cards[::2] # String of all numbers in hand and board

    # Creates dictionary of the number of instances of each number, converts face cards into their respective values
    num_count = create_num_count_dict(nums)

    # Sets high_pair to the highest number with 2 instances, 0 if none exist
    high_pair = 0
    for num in num_count:
        if num_count[num] == 2 and num > high_pair:
            high_pair = num

    # Sets low_pair to the second highest number with 2 instances, 0 if none exist
    low_pair = 0
    for num in num_count:
        if num_count[num] == 2 and num > low_pair and num != high_pair:
            low_pair = num

    # Sets list of kickers in decreasing order
    kickers = create_kickers(num_count, high_pair, low_pair)

    if high_pair > 0 and low_pair > 0:
        return [high_pair,low_pair,kickers[0]]

    return [0,0,0]


"""Returns [pair, kicker 1, kicker 2, kicker 3] or [0, 0, 0, 0] if none"""
def one_pair(hand, board):

    all_cards = hand + board
    nums = all_cards[::2] # String of all numbers in hand and board

    # Creates dictionary of the number of instances of each number, converts face cards into their respective values
    num_count = create_num_count_dict(nums)

    # Sets pair to the highest number with 2 instances, 0 if none exist
    pair = 0
    for num in num_count:
        if num_count[num] == 2 and num > pair:
            pair = num

    # Sets list of kickers in decreasing order
    kickers = create_kickers(num_count, pair, 0)

    if pair > 0:
        return [pair,kickers[0],kickers[1],kickers[2]]

    return [0,0,0,0]


"""Returns sorted array of 5-card hand"""
def high_card(hand, board):

    all_cards = hand + board
    nums = all_cards[::2] # String of all numbers in hand and board

    # Creates dictionary of the number of instances of each number, converts face cards into their respective values
    num_count = create_num_count_dict(nums)

    # Sets list of kickers in decreasing order
    kickers = create_kickers(num_count, 0, 0)

    return kickers[:5]


"""Returns 0 if list 1 is greater than list 2, 1 if list 2 is greater, 2 if the same (Assumes same length)"""
def compare_lists(l1, l2):
    length = len(l1)
    for i in range(length):
        if l1[i] > l2[i]:
            return 0
        elif l1[i] < l2[i]:
            return 1
    return 2


"""Returns 0 if hand 1 wins, 1 if hand 2 wins, 2 if split"""
def compare_hands(h1, h2, board):

    # Checks for quads
    quad1 = four_of_a_kind(h1, board)
    quad2 = four_of_a_kind(h2, board)
    if quad1[0] > 0 and quad2[0] == 0:
        return 0
    elif quad2[0] > 0 and quad1[0] == 0:
        return 1
    elif quad1[0] > 0 and quad2[0] > 0:
        return compare_lists(quad1, quad2)

    # Checks for full house
    fh1 = full_house(h1, board)
    fh2 = full_house(h2, board)
    if fh1[0] > 0 and fh2[0] == 0:
        return 0
    elif fh2[0] > 0 and fh1[0] == 0:
        return 1
    elif fh1[0] > 0 and fh2[0] > 0:
        return compare_lists(fh1, fh2)

    # Checks for flush
    flush1 = flush(h1, board)
    flush2 = flush(h2, board)
    if flush1[0] > 0 and flush2[0] == 0:
        return 0
    elif flush2[0] > 0 and flush1[0] == 0:
        return 1
    elif flush1[0] > 0 and flush2[0] > 0:
        return compare_lists(flush1, flush2)

    # Checks for straight
    straight1 = straight(h1, board)
    straight2 = straight(h2, board)
    if straight1 > straight2:
        return 0
    elif straight2 > straight1:
        return 1
    elif straight1 > 0 and straight2 > 0:
        return 2

    # Checks for three of a kind
    three1 = three_of_a_kind(h1, board)
    three2 = three_of_a_kind(h2, board)
    if three1[0] > 0 and three2[0] == 0:
        return 0
    elif three2[0] > 0 and three1[0] == 0:
        return 1
    elif three1[0] > 0 and three2[0] > 0:
        return compare_lists(three1, three2)

    # Checks for two pair
    pairs1 = two_pair(h1, board)
    pairs2 = two_pair(h2, board)
    if pairs1[0] > 0 and pairs2[0] == 0:
        return 0
    elif pairs2[0] > 0 and pairs1[0] == 0:
        return 1
    elif pairs2[0] > 0 and pairs1[0] > 0:
        return compare_lists(pairs1, pairs2)

    # Checks for one pair
    pair1 = one_pair(h1, board)
    pair2 = one_pair(h2, board)
    if pair1[0] > 0 and pair2[0] == 0:
        return 0
    elif pair2[0] > 0 and pair1[0] == 0:
        return 1
    elif pair1[0] > 0 and pair2[0] > 0:
        return compare_lists(pair1, pair2)

    # Checks for high card
    high1 = high_card(h1, board)
    high2 = high_card(h2, board)
    return compare_lists(high1, high2)


"""Resets board and hands to preflop"""
def reset(session_id):

    game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session_id)[0]

    # Sets street to preflop
    db.execute("UPDATE games SET street = ? WHERE player_id = ? AND active = 1", "preflop", session_id)

    # Creates new hands and board
    hand_info = render_hand()

    # Sets hands and board to new values
    db.execute("UPDATE games SET hand = ?, opp_hand = ?, board = ?, pot = ? WHERE player_id = ? AND active = 1", hand_info['hand'], hand_info['opp_hand'], hand_info['board'], 0, session_id)

    # Changes position and inputs blinds
    if game['position'] == "sb":
        db.execute("UPDATE games SET position = ? WHERE player_id = ? AND active = 1", "bb", session_id)
        db.execute("UPDATE games SET bet = ?, opp_bet = ?, chips = ?, opp_chips = ? WHERE player_id = ? AND active = 1", 2, 1, game['chips'] - 2, game['opp_chips'] - 1, session_id)
    else:
        db.execute("UPDATE games SET position = ? WHERE player_id = ? AND active = 1", "sb", session_id)
        db.execute("UPDATE games SET bet = ?, opp_bet = ?, chips = ?, opp_chips = ? WHERE player_id = ? AND active = 1", 1, 2, game['chips'] - 1, game['opp_chips'] - 2, session_id)

    # Logs the beginning of preflop
    log_id = db.execute("SELECT id FROM logs WHERE game_id = (SELECT id FROM games WHERE player_id = ? AND active = 1)", session_id)[0]['id']
    db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", "Preflop:", log_id)


"""Bot check/call"""
def bot_checkcall(session_id):

    game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session_id)[0]

    # If facing a raise, call. If not, check.
    if game['bet'] > game['opp_bet']:

        # Updates bot's chips and bet size
        db.execute("UPDATE games SET opp_chips = ? WHERE player_id = ? AND active = 1", game['opp_chips'] - game['bet'] + game['opp_bet'], session_id)
        db.execute("UPDATE games SET opp_bet = ? WHERE player_id = ? AND active = 1", game['bet'], session_id)

        return "Opponent calls"

    return "Opponent checks"


"""Bot raise"""
def bot_raise(session_id):

    game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session_id)[0]

    # If facing a raise, reraise to twice the player's bet. If opening, raise to half pot.
    if game['bet'] > 0:
        raise_size = game['bet'] * 2
    else:
        raise_size = round(game['pot'] * 0.5)

    # If raise size is larger than the player's stack, adjust it to put them exactly all in
    if raise_size > game['chips'] + game['bet']:
        raise_size = game['chips'] + game['bet']

    # If raise size is larger than bot's stack, adjust it to put the bot all in
    if raise_size > game['opp_chips'] + game['opp_bet']:
        raise_size = game['opp_chips'] + game['opp_bet']

    # Updates bot's chips and bet size
    db.execute("UPDATE games SET opp_chips = ? WHERE player_id = ? AND active = 1", game['opp_chips'] - raise_size + game['opp_bet'], session_id)
    db.execute("UPDATE games SET opp_bet = ? WHERE player_id = ? AND active = 1", raise_size, session_id)

    return "Opponent raises to " + str(raise_size)


"""Bot check/fold"""
def bot_checkfold(session_id):

    game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session_id)[0]

    # If facing a raise, fold. If not, check.
    if game['bet'] > game['opp_bet']:

        # Gives chips in pot to player
        db.execute("UPDATE games SET chips = ? WHERE player_id = ? AND active = 1", game['chips'] + game['bet'] + game['opp_bet'] + game['pot'], session_id)

        return "Opponent folds"

    return "Opponent checks"


"""Returns bot's hand strength"""
def bot_strength(session_id):

    board = db.execute("SELECT board FROM games WHERE player_id = ? AND active = 1", session_id)[0]['board']
    opp_hand = db.execute("SELECT opp_hand FROM games WHERE player_id = ? AND active = 1", session_id)[0]['opp_hand']

    values = ["2","3","4","5","6","7","8","9","T","J","Q","K","A"]
    suits = ["S","C","D","H"]
    deck = []

    # Creates a deck of all cards not in bot's hand
    for value in values:
        for suit in suits:
            card = value + suit
            if card not in opp_hand:
                deck.append(card)

    # Creates an array of all the player's possible hands
    possible_hands = []
    for card1 in deck:
        for card2 in deck:
            if card1 != card2 and card1 + card2 not in possible_hands and card2 + card1 not in possible_hands:
                possible_hands.append(card1 + card2)

    # Creates index for strength of bot's hand
    hand_strength = 0

    # For each possible hand, add 1 to hand_strength if the bot will win at showdown and 0.5 if bot will chop the pot at showdown
    for hand in possible_hands:
        comparison = compare_hands(hand, opp_hand, board)
        if comparison == 2:
            hand_strength += 0.5
        else:
            hand_strength += comparison

    # Divides by number of possible hands to get an average probability of beating a hand
    hand_strength = hand_strength / len(possible_hands)

    return hand_strength


"""Bot decision-making"""
def bot_action(hand_strength, session_id):

    game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session_id)[0]

    # Choose action based on strength of hand
    if hand_strength >= 0.9:

        # If player is all in or putting the bot all in, call. Otherwise, raise
        if game['chips'] == 0 or game['bet'] >= game['opp_chips'] + game['opp_bet']:
            return bot_checkcall(session_id)
        return bot_raise(session_id)

    elif hand_strength >= 0.7:

        # If player is all in or putting the bot all in, call. Otherwise, 50% of the time, check/call, and the other 50% of the time, raise.
        rng = random.randint(0,1)
        if rng == 0 or game['chips'] == 0 or game['bet'] >= game['opp_chips'] + game['opp_bet']:
            return bot_checkcall(session_id)
        return bot_raise(session_id)

    elif hand_strength >= 0.4:

        # 50% of the time, check/call, and the other 50% of the time, check/fold.
        rng = random.randint(0,1)
        if rng == 0:
            return bot_checkcall(session_id)
        return bot_checkfold(session_id)

    else:

        # 20% of the time, bluff. The other 80% of the time, check/fold.
        rng = random.randint(0,4)
        if rng == 0 and game['chips'] != 0 and game['bet'] < game['opp_chips'] + game['opp_bet']:
            return bot_raise(session_id)
        return bot_checkfold(session_id)


"""Updates betting street"""
def next_street(session_id):

    game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session_id)[0]
    log_id = db.execute("SELECT id FROM logs WHERE game_id = (SELECT id FROM games WHERE player_id = ? AND active = 1)", session_id)[0]['id']

    # Move bets into the pot
    db.execute("UPDATE games SET pot = ? WHERE player_id = ? AND active = 1", game['pot'] + game['bet'] + game['opp_bet'], session_id)
    db.execute("UPDATE games SET bet = ?, opp_bet = ? WHERE player_id = ? AND active = 1", 0, 0, session_id)

    # Updates street to next street and logs it
    if game['street'] == "preflop":
        db.execute("UPDATE games SET street = ? WHERE player_id = ? AND active = 1", "flop", session_id)
        db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", "Flop:", log_id)
    elif game['street'] == "flop":
        db.execute("UPDATE games SET street = ? WHERE player_id = ? AND active = 1", "turn", session_id)
        db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", "Turn:", log_id)
    elif game['street'] == "turn":
        db.execute("UPDATE games SET street = ? WHERE player_id = ? AND active = 1", "river", session_id)
        db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", "River:", log_id)

"""Showdown updates"""
def showdown(session_id):

    game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session_id)[0]
    log_id = db.execute("SELECT id FROM logs WHERE game_id = (SELECT id FROM games WHERE player_id = ? AND active = 1)", session_id)[0]['id']
    username = db.execute("SELECT username FROM users WHERE id = ?", session_id)[0]['username']

    # Stores winner of showdown
    comparison = compare_hands(game['hand'], game['opp_hand'], game['board'])

    # Player wins
    if comparison == 0:
        db.execute("UPDATE games SET chips = ? WHERE player_id = ? AND active = 1", game['chips'] + game['bet'] + game['opp_bet'] + game['pot'], session_id)
        db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", username + " wins pot of " + str(game['bet'] + game['opp_bet'] + game['pot']), log_id)

    # Bot wins
    elif comparison == 1:
        db.execute("UPDATE games SET opp_chips = ? WHERE player_id = ? AND active = 1", game['opp_chips'] + game['bet'] + game['opp_bet'] + game['pot'], session_id)
        db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", "Opponent wins pot of " + str(game['bet'] + game['opp_bet'] + game['pot']), log_id)

    # Chop pot
    else:
        half_pot1 = round((game['bet'] + game['opp_bet'] + game['pot'])/2)
        half_pot2 = game['bet'] + game['opp_bet'] + game['pot'] - half_pot1
        db.execute("UPDATE games SET chips = ? WHERE player_id = ? AND active = 1", half_pot1, session_id)
        db.execute("UPDATE games SET opp_chips = ? WHERE player_id = ? AND active = 1", half_pot2, session_id)
        db.execute("INSERT INTO entries (entry, log_id) VALUES (?, ?)", "Chop pot of " + str(game['bet'] + game['opp_bet'] + game['pot']), log_id)


"""Returns 0 if neither player is all in, 1 if one player is all in"""
def all_in(session_id):
    game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session_id)[0]
    if game['chips'] == 0 or game['opp_chips'] == 0:
        return 1
    return 0


"""Returns 0 if neither player has won, 1 if user has won, 2 if opponent has won"""
def win(session_id):

    game = db.execute("SELECT * FROM games WHERE player_id = ? AND active = 1", session_id)[0]

    # Bot won
    if game['chips'] == 0:

        # Set game to inactive
        db.execute("UPDATE games SET active = 0 WHERE player_id = ? AND active = 1", session_id)

        # Update player's losses
        current_losses = db.execute("SELECT losses FROM users WHERE id = ?", session_id)[0]['losses']
        db.execute("UPDATE users SET losses = ? WHERE id = ?", current_losses + 1, session_id)

        return 2

    # Player won
    if game['opp_chips'] == 0:

        # Set game to inactive
        db.execute("UPDATE games SET active = 0 WHERE player_id = ? AND active = 1", session_id)

        # Update player's wins
        current_wins = db.execute("SELECT wins FROM users WHERE id = ?", session_id)[0]['wins']
        db.execute("UPDATE users SET wins = ? WHERE id = ?", current_wins + 1, session_id)

        return 1

    return 0

"""Returns points given user's wins and losses"""
def points(e):
    return e['wins'] * 2 - e['losses']