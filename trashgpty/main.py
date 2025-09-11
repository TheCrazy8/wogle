import ollama
from ollama import chat
from ollama import ChatResponse
import tkinter as tk
from tkinter import ttk
import threading
import sv_ttk

# Keep track of which models we've already pulled in this session
loaded_models = set()

def main():
    """Launch a Tkinter chat UI with selectable Ollama model."""
    root = tk.Tk()
    root.title("AI Chat")

    # --- Top: model selection ---
    top_frame = ttk.Frame(root, padding=(10, 10, 10, 0))
    top_frame.grid(row=0, column=0, sticky="ew")
    root.columnconfigure(0, weight=1)

    ttk.Label(top_frame, text="Model:").grid(row=0, column=0, sticky="w")

    # Try to list local models; fall back to a curated set
    try:
        listed = ollama.list()
        model_names = [m.get('name','').split(':')[0] for m in listed.get('models', []) if m.get('name')]
        # Deduplicate while preserving order
        seen = set()
        model_names = [m for m in model_names if not (m in seen or seen.add(m))]
    except Exception:
        model_names = [
            'gemma3', 'llama3', 'phi3', 'mistral', 'qwen2', 'codellama'
        ]

    default_model = 'gemma3' if 'gemma3' in model_names else (model_names[0] if model_names else 'gemma3')
    current_model_var = tk.StringVar(value=default_model)

    model_box = ttk.Combobox(top_frame, textvariable=current_model_var, values=model_names, width=25, state='normal')
    model_box.grid(row=0, column=1, padx=5, sticky="w")

    pull_status_var = tk.StringVar(value="")
    status_label = ttk.Label(top_frame, textvariable=pull_status_var, foreground='#888')
    status_label.grid(row=0, column=2, padx=10, sticky='w')

    def append(text: str):
        convo.configure(state="normal")
        convo.insert("end", text + "\n")
        convo.see("end")
        convo.configure(state="disabled")

    def pull_model_if_needed(model_name: str):
        if model_name in loaded_models:
            return
        pull_status_var.set(f"Pulling {model_name}…")
        try:
            ollama.pull(model_name)
            loaded_models.add(model_name)
            pull_status_var.set(f"{model_name} ready")
        except Exception as e:
            pull_status_var.set(f"Pull failed: {e}")
            append(f"[Error pulling model '{model_name}': {e}]")

    def thread_pull():
        model_name = current_model_var.get().strip()
        if not model_name:
            return
        load_btn.configure(state='disabled')
        threading.Thread(target=lambda: (pull_model_if_needed(model_name), root.after(0, lambda: load_btn.configure(state='normal'))), daemon=True).start()

    load_btn = ttk.Button(top_frame, text="Load / Pull", command=thread_pull)
    load_btn.grid(row=0, column=3, padx=5, sticky='w')

    # --- Conversation display ---
    text_frame = ttk.Frame(root, padding=10)
    text_frame.grid(row=1, column=0, sticky="nsew")

    root.rowconfigure(1, weight=1)

    convo = tk.Text(text_frame, wrap="word", height=20, width=80, state="disabled")
    convo.grid(row=0, column=0, columnspan=4, sticky="nsew")

    scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=convo.yview)
    scrollbar.grid(row=0, column=4, sticky="ns")
    convo.configure(yscrollcommand=scrollbar.set)

    text_frame.rowconfigure(0, weight=1)
    text_frame.columnconfigure(0, weight=1)

    # --- Entry + buttons ---
    entry_var = tk.StringVar()
    entry = ttk.Entry(text_frame, textvariable=entry_var, width=60)
    entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8,0))
    text_frame.columnconfigure(0, weight=1)

    send_btn = ttk.Button(text_frame, text="Send")
    send_btn.grid(row=1, column=2, padx=5, pady=(8,0), sticky='e')

    clear_btn = ttk.Button(text_frame, text="Clear", command=lambda: (convo.configure(state='normal'), convo.delete('1.0','end'), convo.configure(state='disabled')))
    clear_btn.grid(row=1, column=3, padx=5, pady=(8,0))

    quit_btn = ttk.Button(text_frame, text="Quit", command=root.destroy)
    quit_btn.grid(row=1, column=4, padx=5, pady=(8,0))

    def do_inference(user_msg: str, model_name: str):
        # Ensure model is pulled (might take time)
        pull_model_if_needed(model_name)
        try:
            response: ChatResponse = chat(model=model_name, messages=[{
                'role': 'user',
                'content': user_msg,
            }])
            resp = response['message']['content']
        except Exception as e:
            resp = f"[Error querying model '{model_name}': {e}]"
        # Back to main thread to update UI
        root.after(0, lambda: finalize_response(resp, model_name))

    def finalize_response(resp: str, model_name: str):
        append(f"{model_name}: {resp}")
        send_btn.configure(state="normal")
        entry.configure(state="normal")
        entry_var.set("")
        entry.focus()

    def send(event=None):  # event param for Enter key binding
        user_msg = entry_var.get().strip()
        model_name = current_model_var.get().strip() or default_model
        if not user_msg:
            return
        append(f"You: {user_msg}")
        # Disable input while processing
        send_btn.configure(state="disabled")
        entry.configure(state="disabled")
        threading.Thread(target=do_inference, args=(user_msg, model_name), daemon=True).start()

    send_btn.configure(command=send)
    entry.bind('<Return>', send)

    append("AI Chat ready. Pick / load a model, then type a message and press Enter or Send.")
    entry.focus()

    # Apply dark theme if available
    try:
        sv_ttk.set_theme("dark")
    except Exception:
        pass

    root.mainloop()

if __name__ == "__main__":
    main()