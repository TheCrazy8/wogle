import random

print("Wogle Doice Boss Battle™")

money = 0
health = 10
bosshealth = 100

def microtransactions():
    if money := input("Do you want to buy a health potion for 5 coins? (yes/no): ").strip().lower() == "yes":
        global health
        if health < 10:
            health += 1
            print(f"Health increased to {health}.")
        else:
            print("Health is already at maximum.")

def dice_roll():
    return random.randint(1, 6)

def enemy_roll():
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
            money += 10
            print(f"Money: {money}")
            if input("Play again?: (just hit enter)") == "":
                play_game()
        else:
            print("Roll again!")
            play_game()

play_game()
# dicegame.py
