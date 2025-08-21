import random

print("Wogle Doice Boss Battle™")

money = 0
health = 10
bosshealth = 100

def microtransactions():
    global money
    #insert way to convert real money to in-game money
    print("Microtransactions are not implemented yet. Stay tuned for future updates!")

def shopen():
    global money, health
    print(f"Money: {money}")
    print(f"Health: {health}")
    if input("Do you want to go to the shop? (yes/no): ").strip().lower() == "yes":
        shop()
    else:
        print("Continuing without shopping.")

def shop():
    priceisrice = input("What do you want to buy? (health potion for 5 coins, buy more coins, or nothing): ").strip().lower()
    if priceisrice == "health potion":
        if input("Do you want to buy a health potion for 5 coins? (yes/no): ").strip().lower() == "yes":
            global health, money
            if money >= 5:
                if health < 10:
                    health += 1
                    print(f"Health increased to {health}.")
                else:
                    print("Health is already at maximum.")
            else:
                print("Not enough money to buy a health potion.")
        elif priceisrice == "buy more coins":
            if input("Do you want to buy 10 coins for 5 real money? (yes/no): ").strip().lower() == "yes":
                microtransactions()

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
            shopen()
            print("Roll again!")
            play_game()

play_game()
# dicegame.py
