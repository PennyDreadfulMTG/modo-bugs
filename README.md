# MODO Bugs
Issue Tracker for Magic Online bugs

# Categories

## Game Breaking

Game Breaking bugs make it impossible to finish the game.  

They come in two varieties:
* Soft-locks - The game stops advancing, usually by asking a player to answer a prompt over and over again.
* Resets - The game rewinds, replays the entire game twice, then starts you back on Turn 1 in a buggy state.

## Advantageous

Advantageous bugs allow the controller of the bugged card to get additional value compared to the printed card.

## Disadvantagous

Disadvantageous bugs make the card strictly worse than the printed card.

# Non-functional

Non-functional cards do nothing.  Treat the text box as blank.

We generally don't apply this to creatures, as they're still useful for combat.

# Graphical

Graphical bugs affect the artwork or blue text of a card.  

The card still functions as printed, it just looks weird while doing so.

# How report or update bugs

Go to <https://github.com/PennyDreadfulMTG/modo-bugs/issues>.

Create an issue with the name `[cardname] bug description`. 

For example: `[Power Conduit] Activating its ability will restart the game`

Where possible, try to provide screenshots or videos.

If you only care about Penny Dreadful legal cards, click [here](https://github.com/PennyDreadfulMTG/modo-bugs/issues?q=is%3Aopen+is%3Aissue+label%3A%22Affects+PD%22)

# Viewing the Data

There is collated data available [in visual form](https://pennydreadfulmagic.com/bugs) or as a [Json blob](https://pennydreadfulmtg.github.io/modo-bugs/bugs.json).
