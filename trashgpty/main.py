import ollama
from ollama import chat
from ollama import ChatResponse
import tkinter as tk
from tkinter import ttk
import threading

# Pull the model once at startup (will noop if already present)
try:
    ollama.pull('gemma3')
except Exception as e:
    print(f"Warning: could not pull model gemma3: {e}")
    

def main():
    """Launch a simple Tkinter chat UI for the gemma3 model."""
    root = tk.Tk()
    root.title("Gemma Chat")

    # Conversation display
    text_frame = ttk.Frame(root, padding=10)
    text_frame.grid(row=0, column=0, sticky="nsew")

    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)

    convo = tk.Text(text_frame, wrap="word", height=20, width=70, state="disabled")
    convo.grid(row=0, column=0, columnspan=3, sticky="nsew")

    scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=convo.yview)
    scrollbar.grid(row=0, column=3, sticky="ns")
    convo.configure(yscrollcommand=scrollbar.set)

    text_frame.rowconfigure(0, weight=1)
    text_frame.columnconfigure(0, weight=1)

    # Entry + buttons
    entry_var = tk.StringVar()
    entry = ttk.Entry(text_frame, textvariable=entry_var, width=55)
    entry.grid(row=1, column=0, sticky="ew", pady=(8,0))
    text_frame.columnconfigure(0, weight=1)

    send_btn = ttk.Button(text_frame, text="Send")
    send_btn.grid(row=1, column=1, padx=5, pady=(8,0))

    quit_btn = ttk.Button(text_frame, text="Quit", command=root.destroy)
    quit_btn.grid(row=1, column=2, padx=5, pady=(8,0))

    def append(text: str):
        convo.configure(state="normal")
        convo.insert("end", text + "\n")
        convo.see("end")
        convo.configure(state="disabled")

    def do_inference(user_msg: str):
        try:
            response: ChatResponse = chat(model='gemma3', messages=[{
                'role': 'user',
                'content': user_msg,
            }])
            resp = response['message']['content']
        except Exception as e:
            resp = f"[Error querying model: {e}]"
        # Back to main thread to update UI
        root.after(0, lambda: finalize_response(resp))

    def finalize_response(resp: str):
        append(f"Gemma: {resp}")
        send_btn.configure(state="normal")
        entry.configure(state="normal")
        entry_var.set("")
        entry.focus()

    def send(event=None):  # event param for Enter key binding
        user_msg = entry_var.get().strip()
        if not user_msg:
            return
        append(f"You: {user_msg}")
        # Disable input while processing
        send_btn.configure(state="disabled")
        entry.configure(state="disabled")
        threading.Thread(target=do_inference, args=(user_msg,), daemon=True).start()

    send_btn.configure(command=send)
    entry.bind('<Return>', send)

    append("Gemma Chat ready. Type a message and press Enter or Send.")
    entry.focus()

    root.mainloop()

if __name__ == "__main__":
    main()