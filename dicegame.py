import random

print("Wogle")
def dice_roll():
    return random.randint(1, 6)

def play_game():
    if input("Roll: (just hit enter)") == "":
        num = dice_roll()
        print(f"You rolled a {num}.")
        if num == 1:
            print("You lose!")
            if input("Play again?: (just hit enter)") == "":
                play_game()
        elif num == 6:
            print("You win!")
            if input("Play again?: (just hit enter)") == "":
                play_game()
        else:
            print("Roll again!")
            play_game()

play_game()