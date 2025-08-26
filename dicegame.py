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
        self.money = 0
        self.health = 10
        self.defense = 0
        self.bosshealth = 100
        self.current_payment_id = None
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.geometry(f"{screen_width}x{screen_height}+0+0")

        self.status_label = ttk.Label(self.root, text=self.get_status(), font=("Arial", 14))
        self.status_label.pack(pady=10)

        self.roll_button = ttk.Button(self.root, text="Roll Dice", command=self.play_game)
        self.roll_button.pack(pady=5)

        self.language = "en"
        self.easter_egg_button = ttk.Button(self.root, text="Easter Egg", command=self.toggle_language)
    def toggle_language(self):
        # Toggle between English and Spanish
        self.language = "egg" if self.language == "en" else "en"
        self.update_ui_language()
        messagebox.showinfo(self._t("Easter Egg"), self._t("You found the easter egg! Language changed!"))

    def _t(self, text):
        # Simple translation dictionary
        translations = {
            "en": {
                "Roll Dice": "Roll Dice",
                "Shop": "Shop",
                "Quit": "Quit",
                "Easter Egg": "Easter Egg",
                "You found the easter egg! Language changed!": "You found the easter egg! Language changed!",
                "Money": "Money",
                "Health": "Health",
                "Boss Health": "Boss Health",
                "Congratulations!": "Congratulations!",
                "You rolled a 6, roll again for a chance to win a banana!": "You rolled a 6, roll again for a chance to win a banana!",
                "You Win!": "You Win!",
                "You rolled another 6! You win a banana!": "You rolled another 6! You win a banana!",
                "Game Over": "Game Over",
                "You lose!": "You lose!",
                "Play Again?": "Play Again?",
                "Do you want to play again?": "Do you want to play again?",
                "Victory!": "Victory!",
                "You win!\nMoney: ": "You win!\nMoney: ",
                "Roll Result": "Roll Result",
                "Instant Loss": "Instant Loss",
                "You found a shotgun with one bullet.  It, uhh, well, its kinda not well kept, so, uhh, well, OH DANG THE BOSS ATTACK SPARKED OH SHOOT THERE GOES THE GUNPOWDER aaaaand you blew up. :/ You lose": "You found a shotgun with one bullet.  It, uhh, well, its kinda not well kept, so, uhh, well, OH DANG THE BOSS ATTACK SPARKED OH SHOOT THERE GOES THE GUNPOWDER aaaaand you blew up. :/ You lose"
            },
            "egg": {
                "Roll Dice": "Roll Block",
                "Shop": "Tem Shop",
                "Quit": "Bye Bye!",
                "Easter Egg": "Tem find Egg!!!!!",
                "You found the easter egg! Language changed!": "Dont leave me tem friend!!!",
                "Money": "Muns",
                "Health": "Temmie Flakes :3",
                "Boss Health": "Evil Temmie Flakes >:(",
                "Congratulations!": "Yippie!!!",
                "You rolled a 6, roll again for a chance to win a banana!": "Get a 6, get banan!!!",
                "You Win!": "¡Ganaste!",
                "You rolled another 6! You win a banana!": "BannanaananananannaS!!!!!!!!!!!!!",
                "Game Over": "Womp Womp Womp :(",
                "You lose!": "You Lose :(",
                "Play Again?": "Try Again?",
                "Do you want to play again?": "want to try again?",
                "Victory!": "Yay!!! Victory!!!",
                "You win!\nMoney: ": "you winned \nmuns: ",
                "Roll Result": "rolled",
                "Instant Loss": "ded.  Rip. :(",
                "You found a shotgun with one bullet.  It, uhh, well, its kinda not well kept, so, uhh, well, OH DANG THE BOSS ATTACK SPARKED OH SHOOT THERE GOES THE GUNPOWDER aaaaand you blew up. :/ You lose": "Gun.  instant ded.  rip. :("
            }
        }
        return translations[self.language].get(text, text)

    def update_ui_language(self):
        self.roll_button.config(text=self._t("Roll Dice"))
        self.shop_button.config(text=self._t("Shop"))
        self.quit_button.config(text=self._t("Quit"))
        self.easter_egg_button.config(text=self._t("Easter Egg"))
        self.update_status()
        # Do not pack the easter egg button, so it remains hidden
        self.schedule_easter_egg()

    def schedule_easter_egg(self):
        # Try to show the easter egg button every minute
        self.root.after(60000, self.try_show_easter_egg)

    def try_show_easter_egg(self):
        # 1 in 5 chance to show the button each minute
        if random.randint(1, 5) == 1:
            self.easter_egg_button.pack(pady=5)
            self.root.after(1000, self.hide_easter_egg)
        self.schedule_easter_egg()

    def hide_easter_egg(self):
        self.easter_egg_button.pack_forget()

        self.shop_button = ttk.Button(self.root, text="Shop", command=self.open_shop)
        self.shop_button.pack(pady=5)

        self.quit_button = ttk.Button(self.root, text="Quit", command=self.root.quit)
        self.quit_button.pack(pady=5)

        # Start the game automatically when the window opens
        self.root.after(100, self.play_game)

    def get_status(self):
        return f"{self._t('Money')}: {self.money} | {self._t('Health')}: {self.health} | {self._t('Boss Health')}: {self.bosshealth}"

    def update_status(self):
        self.status_label.config(text=self.get_status())

    def rollforbanana(self):
        messagebox.showinfo(self._t("Congratulations!"), self._t("You rolled a 6, roll again for a chance to win a banana!"))
        if random.randint(1, 6) == 6:
            messagebox.showinfo(self._t("You Win!"), self._t("You rolled another 6! You win a banana!"))
            self.bosshealth = self.bosshealth - (self.bosshealth // 5)
            self.update_status()

    def play_game(self):
        num = random.randint(1, 6)
        nem = random.randint(1, 6)
        self.bosshealth -= num
        self.health -= (nem - self.defense)
        self.money += 2
        self.update_status()
        message = f"{self._t('You rolled a {num}.\nBoss health: {self.bosshealth}\nEnemy rolled a {nem}.\nYour health: {self.health}').format(num=num, bosshealth=self.bosshealth, nem=nem, health=self.health)}"
        if num == 6:
            self.rollforbanana()
        if self.health < 1:
            messagebox.showinfo(self._t("Game Over"), self._t("You lose!"))
            self.ask_play_again()
            return
        if random.randint(1, 1000000) == 6:
            self.health = 0
            self.update_status()
            messagebox.showinfo(self._t("Instant Loss"), self._t("You found a shotgun with one bullet.  It, uhh, well, its kinda not well kept, so, uhh, well, OH DANG THE BOSS ATTACK SPARKED OH SHOOT THERE GOES THE GUNPOWDER aaaaand you blew up. :/ You lose"))
            self.ask_play_again()
            return
        if self.bosshealth < 1:
            self.money += 10
            self.update_status()
            messagebox.showinfo(self._t("Victory!"), f"{self._t('You win!\nMoney: ')}{self.money}")
            self.ask_play_again()
            return
        messagebox.showinfo(self._t("Roll Result"), message)

    def ask_play_again(self):
        if messagebox.askyesno(self._t("Play Again?"), self._t("Do you want to play again?")):
            self.money = 0
            self.health = 10
            self.bosshealth = 100
            self.update_status()
        else:
            self.root.quit()

    def open_shop(self):
        shop_win = tk.Toplevel(self.root)
        shop_win.title("Shop")
        ttk.Label(shop_win, text=self.get_status(), font=("Arial", 12)).pack(pady=5)

        ttk.Button(shop_win, text="Buy Health Potion (5 coins)", command=lambda: self.buy_health(shop_win)).pack(pady=3)
        ttk.Button(shop_win, text="Buy 5000 Coins (5.00 USD)", command=lambda: self.buy_coins(shop_win)).pack(pady=3)
        ttk.Button(shop_win, text="Buy Lootbox (10 coins)", command=lambda: self.buy_lootbox(shop_win)).pack(pady=3)
        ttk.Button(shop_win, text="Buy Paper Hat (15 coins)", command=lambda: self.buy_hat(shop_win)).pack(pady=3)
        ttk.Button(shop_win, text="Close", command=shop_win.destroy).pack(pady=3)

    def buy_health(self, win):
        if self.money >= 5:
            if self.health < 10:
                self.money -= 5
                self.health += 1
                self.update_status()
                messagebox.showinfo("Shop", f"Health increased to {self.health}.")
            else:
                messagebox.showinfo("Shop", "Health is already at maximum.")
        else:
            messagebox.showinfo("Shop", "Not enough money to buy a health potion.")
        win.destroy()

    def buy_hat(self, win):
        if self.money >= 15:
            self.money -= 15
            self.defense += 1
            self.update_status()
            messagebox.showinfo("Shop", "You bought a paper hat! (defense +1)")
        else:
            messagebox.showinfo("Shop", "Not enough money to buy a paper hat.")
        win.destroy()

    def track_payment(self):
        # Poll PayPal for payment status using the stored payment ID
        if paypalrestsdk and self.current_payment_id:
            try:
                payment = paypalrestsdk.Payment.find(self.current_payment_id)
                if payment and payment.state == "approved":
                    self.money += 5000
                    self.update_status()
                    messagebox.showinfo("PayPal", "Payment successful! 5000 coins added.")
                    self.current_payment_id = None
                elif payment and payment.state == "failed":
                    messagebox.showerror("PayPal Error", "Payment failed.")
                    self.current_payment_id = None
                else:
                    # Not approved yet, poll again after 5 seconds
                    self.root.after(5000, self.track_payment)
            except Exception as e:
                messagebox.showerror("PayPal Error", f"Error tracking payment: {e}")
                self.current_payment_id = None
        else:
            messagebox.showinfo("PayPal", "Simulated: Payment successful! 5000 coins added.")

    def buy_coins(self, win):
        if paypalrestsdk:
            if messagebox.askyesno("Buy Coins", "Do you want to buy 5000 coins for $5.00 USD? (price to cover paypal transaction fees)"):
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
                    if approval_url:
                        self.current_payment_id = payment.id
                        messagebox.showinfo("PayPal", f"Payment created! Approve at: {approval_url}\nAfter approval, coins will be added automatically.")
                        browser.open(approval_url, new=1)
                        # Start polling for payment approval
                        self.root.after(5000, self.track_payment)
                    else:
                        messagebox.showinfo("PayPal", "Payment created, but no approval URL found.")
                else:
                    messagebox.showerror("PayPal Error", str(payment.error))
        else:
            self.money += 5000
            self.update_status()
            messagebox.showinfo("Shop", "Simulated: 5000 coins added.")
        win.destroy()

    def buy_lootbox(self, win):
        if self.money >= 10:
            self.money -= 10
            loot = random.choice(["health potion", "extra life", "nothing"])
            if loot == "health potion":
                if self.health < 10:
                    self.health += 1
                    messagebox.showinfo("Lootbox", "You found a health potion! Health increased by 1.")
                else:
                    messagebox.showinfo("Lootbox", "You found a health potion but your health is already full.")
            elif loot == "extra life":
                self.health += 5
                messagebox.showinfo("Lootbox", "You found an extra life! Health increased by 5.")
            else:
                messagebox.showinfo("Lootbox", "The lootbox was empty. Better luck next time!")
            self.update_status()
        else:
            messagebox.showinfo("Lootbox", "Not enough money to buy a lootbox.")
        win.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = DiceGameGUI(root)
    sv_ttk.set_theme("dark")
    root.mainloop()
