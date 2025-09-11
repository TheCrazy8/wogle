import ollama
from ollama import chat
from ollama import ChatResponse
import tkinter as tk
from tkinter import ttk
import threading

try:
    import sv_ttk
except ImportError:
    sv_ttk = None  # Themeing is optional

# Keep track of which models we've already pulled in this session
loaded_models = set()

def main():
    """Launch a Tkinter chat UI with selectable Ollama model and multi-turn memory."""
    root = tk.Tk()
    root.title("AI Chat")

    # Shared conversation history (list of message dicts) + lock
    history_lock = threading.Lock()
    messages = []  # each: {'role': 'user'|'assistant'|'system', 'content': str}

    # Optionally seed with a system prompt (editable later if desired)
    system_prompt = "You are a helpful AI assistant."
    messages.append({'role': 'system', 'content': system_prompt})

    # --- Top: model selection ---
    top_frame = ttk.Frame(root, padding=(10, 10, 10, 0))
    top_frame.grid(row=0, column=0, sticky="ew")
    root.columnconfigure(0, weight=1)

    ttk.Label(top_frame, text="Model:").grid(row=0, column=0, sticky="w")

    # Try to list local models; fall back to a curated set (fix for empty dropdown)
    curated_defaults = ['gemma3', 'llama3', 'mistral', 'phi3', 'qwen2', 'codellama']
    try:
        listed = ollama.list()
        model_names = [m.get('name', '').split(':')[0] for m in listed.get('models', []) if m.get('name')]
        # Deduplicate while preserving order
        seen = set()
        model_names = [m for m in model_names if not (m in seen or seen.add(m))]
        if not model_names:
            model_names = curated_defaults
    except Exception:
        model_names = curated_defaults

    default_model = 'gemma3' if 'gemma3' in model_names else (model_names[0] if model_names else 'gemma3')
    current_model_var = tk.StringVar(value=default_model)

    model_box = ttk.Combobox(top_frame, textvariable=current_model_var, values=model_names, width=25, state='normal')
    model_box.grid(row=0, column=1, padx=5, sticky="w")

    pull_status_var = tk.StringVar(value="")
    status_label = ttk.Label(top_frame, textvariable=pull_status_var, foreground='#888')
    status_label.grid(row=0, column=2, padx=10, sticky='w')

    def update_model_list_if_new(model_name: str):
        if model_name not in model_names:
            model_names.append(model_name)
            model_box.configure(values=model_names)

    # --- Conversation display ---
    text_frame = ttk.Frame(root, padding=10)
    text_frame.grid(row=1, column=0, sticky="nsew")

    root.rowconfigure(1, weight=1)

    convo = tk.Text(text_frame, wrap="word", height=20, width=80, state="disabled")
    convo.grid(row=0, column=0, columnspan=6, sticky="nsew")

    scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=convo.yview)
    scrollbar.grid(row=0, column=6, sticky="ns")
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

    clear_btn = ttk.Button(text_frame, text="Clear", command=lambda: clear_conversation())
    clear_btn.grid(row=1, column=3, padx=5, pady=(8,0))

    dump_btn = ttk.Button(text_frame, text="Dump History")
    dump_btn.grid(row=1, column=4, padx=5, pady=(8,0))

    quit_btn = ttk.Button(text_frame, text="Quit", command=root.destroy)
    quit_btn.grid(row=1, column=5, padx=5, pady=(8,0))

    load_btn = ttk.Button(top_frame, text="Load / Pull")
    load_btn.grid(row=0, column=3, padx=5, sticky='w')

    def append(text: str):
        # GUI append
        convo.configure(state="normal")
        convo.insert("end", text + "\n")
        convo.see("end")
        convo.configure(state="disabled")
        # Mirror to console immediately
        print(text)

    def format_history_lines(include_system=False):
        with history_lock:
            for msg in messages:
                if msg['role'] == 'system' and not include_system:
                    continue
                role = msg['role']
                content = msg['content']
                yield f"[{role}] {content}"

    def print_history(include_system=False):
        print("\n=== Conversation History ===")
        for line in format_history_lines(include_system=include_system):
            print(line)
        print("=== End History ===\n")

    def clear_conversation():
        with history_lock:
            # Preserve system prompt only
            del messages[:]
            messages.append({'role': 'system', 'content': system_prompt})
        convo.configure(state='normal')
        convo.delete('1.0','end')
        convo.configure(state='disabled')
        append("[Conversation cleared]")
        print_history(include_system=True)

    def pull_model_if_needed(model_name: str):
        if model_name in loaded_models:
            return
        pull_status_var.set(f"Pulling {model_name}…")
        try:
            ollama.pull(model_name)
            loaded_models.add(model_name)
            update_model_list_if_new(model_name)
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

    load_btn.configure(command=thread_pull)

    def do_inference(user_msg: str, model_name: str):
        # Ensure model is pulled (might take time)
        pull_model_if_needed(model_name)
        try:
            with history_lock:
                temp_history = messages + [{'role': 'user', 'content': user_msg}]
            print(f"--- Streaming response from {model_name} ---")
            full_chunks = []
            # Stream tokens/thought process
            stream = chat(model=model_name, messages=temp_history, stream=True)
            for part in stream:
                # Each part may contain an incremental content piece
                delta = part.get('message', {}).get('content', '')
                if delta:
                    full_chunks.append(delta)
                    # Print without newline to simulate continuous thinking
                    print(f"{delta}", end='', flush=True)
            print("\n--- End of streamed response ---")
            resp = ''.join(full_chunks).strip()
            if not resp:
                resp = "[No content returned]"
        except Exception as e:
            resp = f"[Error querying model '{model_name}': {e}]"
        # Back to main thread to update UI
        root.after(0, lambda: finalize_response(user_msg, resp, model_name))

    def finalize_response(user_msg: str, resp: str, model_name: str):
        with history_lock:
            messages.append({'role': 'user', 'content': user_msg})
            messages.append({'role': 'assistant', 'content': resp})
        append(f"{model_name}: {resp}")
        # Dump updated history to console automatically
        print_history(include_system=False)
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
        send_btn.configure(state="disabled")
        entry.configure(state="disabled")
        threading.Thread(target=do_inference, args=(user_msg, model_name), daemon=True).start()

    def dump_history_action():
        print_history(include_system=True)

    dump_btn.configure(command=dump_history_action)
    send_btn.configure(command=send)
    entry.bind('<Return>', send)

    append("AI Chat ready. Pick / load a model, then type a message and press Enter or Send.")
    entry.focus()

    # Apply dark theme if available
    if sv_ttk is not None:
        try:
            sv_ttk.set_theme("dark")
        except Exception:
            pass

    root.mainloop()

if __name__ == "__main__":
    main()