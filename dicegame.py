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

        self.shop_button = ttk.Button(self.root, text="Shop", command=self.open_shop)
        self.shop_button.pack(pady=5)

        self.quit_button = ttk.Button(self.root, text="Quit", command=self.root.quit)
        self.quit_button.pack(pady=5)

    def get_status(self):
        return f"Money: {self.money} | Health: {self.health} | Boss Health: {self.bosshealth}"

    def update_status(self):
        self.status_label.config(text=self.get_status())

    def rollforbanana():
        messagebox.showinfo("Congratulations!", "You rolled a 6, roll again for a chance to win a banana!")
        if random.randint(1, 6) == 6:
            messagebox.showinfo("You Win!", "You rolled another 6! You win a banana!")
            bosshealth = bosshealth - (bosshealth // 5)

    def play_game(self):
        num = random.randint(1, 6)
        nem = random.randint(1, 6)
        self.bosshealth -= num
        self.health -= (nem - defense)
        self.update_status()
        message = f"You rolled a {num}.\nBoss health: {self.bosshealth}\nEnemy rolled a {nem}.\nYour health: {self.health}"
        if num == 6:
            rollforbanana()
        if self.health < 1:
            messagebox.showinfo("Game Over", "You lose!")
            self.ask_play_again()
            return
        if self.bosshealth < 1:
            self.money += 10
            self.update_status()
            messagebox.showinfo("Victory!", f"You win!\nMoney: {self.money}")
            self.ask_play_again()
            return
        messagebox.showinfo("Roll Result", message)

    def ask_play_again(self):
        if messagebox.askyesno("Play Again?", "Do you want to play again?"):
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
        ttk.Button(shop_win, text="Buy Paper Hat (15 coins)", command=lambda: self.buy_hat.pack(pady=3)
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
