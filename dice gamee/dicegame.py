import random
import webbrowser as browser
import tkinter as tk
from tkinter import ttk, messagebox
import sv_ttk
 
try:
    import paypalrestsdk
    paypalrestsdk.configure({
        "mode": "sandbox",  # or "live"
        "client_id": "AUJZrgKvHjxiFGRcq1U0H24wCoe8SUXwHb-z9walXFnbxQFRrpvzaJ-QqJDZ41F_GRhQPhb8XbNKiih7",
        "client_secret": "EHx22VM0teHMAhjEeA0GmL5h_Sc-nUVbSKQ1KO211Fs8S8kBaSx0flmQKxx0pIHiW8YmtB18P1oS20WF"
    })
except ImportError:
    paypalrestsdk = None

loopfun = 0
paytag = f"buy_coins_{random.randint(10000, 99999)}"

class DiceGameGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Wogle Doice Boss Battle™")
        self.money = 5
        self.stock20 = True
        self.max = 6
        self.health = 25
        self.defense = 0
        self.bosshealth = 100
        self.wins = 0
        self.temmie_mode = False
        self.current_payment_id = None
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.geometry(f"{screen_width}x{screen_height}+0+0")

        self.status_label = ttk.Label(self.root, text=self.get_status(), font=("Arial", 14))
        self.status_label.pack(pady=10)

        self.roll_button = ttk.Button(self.root, text="Roll Dice", command=self.play_game)
        self.roll_button.pack(pady=5)

        self.shop_button = ttk.Button(self.root, text="Shop", command=self.open_shop)
        self.shop_button.pack(pady=5)

        self.quit_button = ttk.Button(self.root, text="Quit", command=self.root.quit)
        self.quit_button.pack(pady=5)

        # Start the game automatically when the window opens
        self.root.after(100, self.start_game)

        self.temmie_mode = False
        self.easter_egg_button = ttk.Button(self.root, text="Easter Egg", command=self.enable_temmie_mode)

    def temmie_text(self, text):
        # Simple Temmie-style transformation
        replacements = [
            ("the", "da"),
            ("The", "Da"),
            ("you", "u"),
            ("You", "U"),
            ("your", "ur"),
            ("Your", "Ur"),
            ("are", "is"),
            ("have", "has"),
            ("and", "an"),
            ("for", "fur"),
            ("to", "tu"),
            ("is", "iz"),
            ("lose", "loose"),
            ("win", "winn"),
            ("money", "munny"),
            ("coins", "coinns"),
            ("health", "helth"),
            ("boss", "bosss"),
            ("potion", "potun"),
            ("shop", "shoop"),
            ("hat", "hatt"),
            ("banana", "banan"),
            ("Congratulations", "CONGRATULASHUNS"),
            ("Victory", "VIKTORI"),
            ("Game Over", "GAM OVAR"),
            ("Roll Result", "ROLL RESOLT"),
            ("extra life", "xtra lyfe"),
            ("nothing", "nuthin"),
            ("found", "fownd"),
            ("already", "alreddy"),
            ("maximum", "maximom"),
            ("full", "ful"),
            ("empty", "emty"),
            ("better luck next time", "bettur luk next tiem"),
        ]
        for old, new in replacements:
            text = text.replace(old, new)
        return text + " hOI!"

    def enable_temmie_mode(self):
        self.temmie_mode = True
        messagebox.showinfo("Easter Egg", self.temmie_text("You found the easter egg!  Enabling Temmie Text!"))
        self.update_status()
        # Do not pack the easter egg button, so it remains hidden

    def schedule_easter_egg(self):
        # Try to show the easter egg button every second
        self.root.after(6000, self.try_show_easter_egg)

    def try_show_easter_egg(self):
        # 1 in 5 chance to show the button each minute
        if random.randint(1, 5) == 1:
            self.easter_egg_button.pack(pady=5)
            self.root.after(1000, self.hide_easter_egg)
        self.schedule_easter_egg()

    def hide_easter_egg(self):
        self.easter_egg_button.pack_forget()

    def get_status(self):
        status = f"Money: {self.money} | Health: {self.health} | Boss Health: {self.bosshealth} | Wins: {self.wins}"
        if self.temmie_mode:
            return self.temmie_text(status)
        return status

    def update_status(self):
        self.status_label.config(text=self.get_status())

    def rollforbanana(self):
        msg1 = "Congratulations! You rolled a 15 or more, roll again for a chance to win a banana!"
        msg2 = "You Win! You rolled 6! You win a banana!"
        if self.temmie_mode:
            msg1 = self.temmie_text(msg1)
            msg2 = self.temmie_text(msg2)
        messagebox.showinfo("Congratulations!", msg1)
        if random.randint(1, 6) == 6:
            messagebox.showinfo("You Win!", msg2)
            self.bosshealth = self.bosshealth - (self.bosshealth // 5)
            self.update_status()

    def start_game(self):
        msg = "Welcome to Wogle Doice Boss Battle™! Roll the dice to attack the boss. If you roll a 6, you get a chance to win a banana and deal extra damage! You can visit the shop to buy health potions, lootboxes, and paper hats for defense. Good luck!"
        if self.temmie_mode:
            msg = self.temmie_text(msg)
        messagebox.showinfo("Welcome!", msg)
        self.money = 5
        self.stock20 = True
        self.max = 6
        self.health = 25
        self.defense = 0
        self.bosshealth = 100
        self.wins = 0
        self.temmie_mode = False
        self.current_payment_id = None
        self.update_status()
        self.play_game()

    def play_game(self):
        self.schedule_easter_egg()
        num = random.randint(1, self.max)
        nem = random.randint(1, 6)
        self.bosshealth -= num
        if nem > self.defense:
            self.health -= (nem - self.defense)
        else:
            self.health -= 0
        self.money += 2
        self.update_status()
        message = f"You rolled a {num}.\nBoss health: {self.bosshealth}\nEnemy rolled a {nem}.\nYour health: {self.health}"
        if self.temmie_mode:
            message = self.temmie_text(message)
        if num >= 15:
            self.rollforbanana()
        if self.health < 1:
            msg = "You lose!"
            if self.temmie_mode:
                msg = self.temmie_text(msg)
            messagebox.showinfo("Game Over", msg)
            self.ask_play_again()
            return
        if random.randint(1, 1000000) == 6:
            self.health = 0
            self.update_status()
            msg = "You found a shotgun with one bullet.  It, uhh, well, its kinda not well kept, so, uhh, well, OH DANG THE BOSS ATTACK SPARKED OH SHOOT THERE GOES THE GUNPOWDER aaaaand you blew up. :/ You lose"
            if self.temmie_mode:
                msg = self.temmie_text(msg)
            messagebox.showinfo("Instant Loss", msg)
            self.ask_play_again()
            return
        if self.bosshealth < 1:
            self.money += 10
            self.update_status()
            msg = f"You win!\nMoney: {self.money}"
            if self.temmie_mode:
                msg = self.temmie_text(msg)
            messagebox.showinfo("Victory!", msg)
            self.health = 25
            self.bosshealth = 100
            self.wins += 1
            self.play_game()
            return
        messagebox.showinfo("Roll Result", message)

    def ask_play_again(self):
        msg = "Do you want to play again?"
        if self.temmie_mode:
            msg = self.temmie_text(msg)
        if messagebox.askyesno("Play Again?", msg):
            self.start_game()
            self.update_status()
        else:
            self.root.quit()

    def open_shop(self):
        shop_win = tk.Toplevel(self.root)
        shop_win.title("Shop")
        label_text = self.get_status()
        if self.temmie_mode:
            label_text = self.temmie_text(label_text)
        ttk.Label(shop_win, text=label_text, font=("Arial", 12)).pack(pady=5)

        btns = [
            ("Buy Health Potion (5 coins)", lambda: self.buy_health(shop_win)),
            ("Buy 5000 Coins (5.00 USD)", lambda: self.buy_coins(shop_win)),
            ("Buy Lootbox (10 coins)", lambda: self.buy_lootbox(shop_win)),
            ("Buy Paper Hat (15 coins)", lambda: self.buy_hat(shop_win)),
            ("Buy D20 (7 coins)", lambda: self.buy_D20(shop_win)),
            ("Close", shop_win.destroy)
        ]
        for text, cmd in btns:
            btn_text = self.temmie_text(text) if self.temmie_mode else text
            ttk.Button(shop_win, text=btn_text, command=cmd).pack(pady=3)

    def buy_D20(self, win):
        if self.money >= 7 and self.stock20 == True:
            self.money -= 7
            self.max = 20
            self.stock20 = False
            self.update_status()

        else:
            msg = "Not enough money to buy a D20."
            if self.temmie_mode:
                msg = self.temmie_text(msg)
            messagebox.showinfo("Shop", msg)
        win.destroy()

    def buy_health(self, win):
        if self.money >= 5:
            if self.health < 50:
                self.money -= 5
                self.health += 5
                self.update_status()
                msg = f"Health increased to {self.health}."
                if self.temmie_mode:
                    msg = self.temmie_text(msg)
                messagebox.showinfo("Shop", msg)
            else:
                msg = "Health is already at maximum."
                if self.temmie_mode:
                    msg = self.temmie_text(msg)
                messagebox.showinfo("Shop", msg)
        else:
            msg = "Not enough money to buy a health potion."
            if self.temmie_mode:
                msg = self.temmie_text(msg)
            messagebox.showinfo("Shop", msg)
        win.destroy()

    def buy_hat(self, win):
        if self.money >= 15:
            self.money -= 15
            self.defense += 1
            self.update_status()
            msg = "You bought a paper hat! (defense +1)"
            if self.temmie_mode:
                msg = self.temmie_text(msg)
            messagebox.showinfo("Shop", msg)
        else:
            msg = "Not enough money to buy a paper hat."
            if self.temmie_mode:
                msg = self.temmie_text(msg)
            messagebox.showinfo("Shop", msg)
        win.destroy()

    def track_payment(self):
        # Poll PayPal for payment status using the stored payment ID
        if paypalrestsdk and self.current_payment_id:
            try:
                payment = paypalrestsdk.Payment.find(self.current_payment_id)
                if payment and payment.state == "approved":
                    self.money += 5000
                    self.update_status()
                    msg = "Payment successful! 5000 coins added."
                    if self.temmie_mode:
                        msg = self.temmie_text(msg)
                    messagebox.showinfo("PayPal", msg)
                    self.current_payment_id = None
                elif payment and payment.state == "failed":
                    msg = "Payment failed."
                    if self.temmie_mode:
                        msg = self.temmie_text(msg)
                    messagebox.showerror("PayPal Error", msg)
                    self.current_payment_id = None
                else:
                    # Not approved yet, poll again after 5 seconds
                    self.root.after(5000, self.track_payment)
            except Exception as e:
                msg = f"Error tracking payment: {e}"
                if self.temmie_mode:
                    msg = self.temmie_text(msg)
                messagebox.showerror("PayPal Error", msg)
                self.current_payment_id = None
        else:
            msg = "Simulated: Payment successful! 5000 coins added."
            if self.temmie_mode:
                msg = self.temmie_text(msg)
            messagebox.showinfo("PayPal", msg)

    def buy_coins(self, win):
        ask_msg = "Do you want to buy 5000 coins for $5.00 USD? (price to cover paypal transaction fees)"
        if self.temmie_mode:
            ask_msg = self.temmie_text(ask_msg)
        if paypalrestsdk:
            if messagebox.askyesno("Buy Coins", ask_msg):
                payment = paypalrestsdk.Payment({
                    "intent": "sale",
                    "payer": {"payment_method": "paypal"},
                    "transactions": [{
                        "amount": {"total": "5.00", "currency": "USD"},
                        "description": "Buying five-thousand coins!"
                    }],
                    "redirect_urls": {
                        "return_url": "http://localhost:3000/process_payment",
                        "cancel_url": "http://localhost:3000/cancel_payment"
                    }
                })
                if payment.create():
                    self.update_status()
                    approval_url = None
                    for link in payment.links:
                        if link.rel == "approval_url":
                            approval_url = str(link.href)
                    msg = f"Payment created! Approve at: {approval_url}\nAfter approval, coins will be added automatically."
                    if self.temmie_mode:
                        msg = self.temmie_text(msg)
                    if approval_url:
                        self.current_payment_id = payment.id
                        messagebox.showinfo("PayPal", msg)
                        browser.open(approval_url, new=1)
                        # Start polling for payment approval
                        self.root.after(5000, self.track_payment)
                    else:
                        msg = "Payment created, but no approval URL found."
                        if self.temmie_mode:
                            msg = self.temmie_text(msg)
                        messagebox.showinfo("PayPal", msg)
                else:
                    err_msg = str(payment.error)
                    if self.temmie_mode:
                        err_msg = self.temmie_text(err_msg)
                    messagebox.showerror("PayPal Error", err_msg)
        else:
            self.money += 5000
            self.update_status()
            msg = "Simulated: 5000 coins added."
            if self.temmie_mode:
                msg = self.temmie_text(msg)
            messagebox.showinfo("Shop", msg)
        win.destroy()

    def buy_lootbox(self, win):
        if self.money >= 10:
            self.money -= 10
            loot = random.choice(["health potion", "extra life", "nothing"])
            if loot == "health potion":
                if self.health < 50:
                    self.health += 5
                    msg = "You found a health potion! Health increased by 1."
                else:
                    msg = "You found a health potion but your health is already full."
            elif loot == "extra life":
                self.health += 5
                msg = "You found an extra life! Health increased by 5."
            else:
                msg = "The lootbox was empty. Better luck next time!"
            if self.temmie_mode:
                msg = self.temmie_text(msg)
            messagebox.showinfo("Lootbox", msg)
            self.update_status()
        else:
            msg = "Not enough money to buy a lootbox."
            if self.temmie_mode:
                msg = self.temmie_text(msg)
            messagebox.showinfo("Lootbox", msg)
        win.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = DiceGameGUI(root)
    sv_ttk.set_theme("dark")
    root.mainloop()
