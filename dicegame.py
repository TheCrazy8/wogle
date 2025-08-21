import random

print("Wogle Doice Boss Battle™")

health = 10
bosshealth = 10

def dice_roll():
    return random.randint(1, 6)

def play_game():
    if input("Roll: (just hit enter)") == "":
        num = dice_roll()
        nem = enemy_roll()
        global health, bosshealth
        print(f"You rolled a {num}.")
        bosshealth -= num
        print(f"Boss health: {bosshealth}")
        print(f"Enemy rolled a {nem}")
        health -= nem
        if health < 1:
            print("You lose!")
            if input("Play again?: (just hit enter)") == "":
                play_game()
        if bosshealth < 1:
            print("You win!")
            if input("Play again?: (just hit enter)") == "":
                play_game()
        else:
            print("Roll again!")
            play_game()

play_game()
# dicegame.py
