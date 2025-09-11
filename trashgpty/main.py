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

import os, io, base64, datetime, json
try:
    from PIL import Image, ImageTk
    _PIL_AVAILABLE = True
except Exception:
    _PIL_AVAILABLE = False

# Stable Diffusion (Automatic1111) API dependency
try:
    import requests
    _REQUESTS_AVAILABLE = True
except Exception:
    _REQUESTS_AVAILABLE = False

# Fixed text model (Ollama)
TEXT_MODEL = 'gemma3'

# Stable Diffusion WebUI API endpoint (adjust if different)
SD_API_URL = 'http://127.0.0.1:7860'
SD_TXT2IMG_ENDPOINT = f'{SD_API_URL}/sdapi/v1/txt2img'

# Keep track of which models we've already pulled in this session (for Ollama text only)
loaded_models = set()
_image_refs = []  # Prevent GC of PhotoImages

def main():
    """Tkinter chat UI with fixed text model (gemma3) + external Stable Diffusion (Automatic1111) for /img."""
    root = tk.Tk()
    root.title("AI Chat (gemma3 + SD WebUI)")

    history_lock = threading.Lock()
    messages = [{'role': 'system', 'content': "You are a helpful AI assistant."}]

    # --- Top bar ---
    top_frame = ttk.Frame(root, padding=(10, 10, 10, 0))
    top_frame.grid(row=0, column=0, sticky='ew')
    root.columnconfigure(0, weight=1)

    ttk.Label(top_frame, text=f"Text model: {TEXT_MODEL}").grid(row=0, column=0, sticky='w')
    ttk.Label(top_frame, text=f"Image: SD WebUI API").grid(row=0, column=1, padx=15, sticky='w')

    pull_status_var = tk.StringVar(value="Initializing…")
    ttk.Label(top_frame, textvariable=pull_status_var, foreground='#888').grid(row=0, column=2, padx=10, sticky='w')

    # Conversation area
    text_frame = ttk.Frame(root, padding=10)
    text_frame.grid(row=1, column=0, sticky='nsew')
    root.rowconfigure(1, weight=1)

    convo = tk.Text(text_frame, wrap='word', height=20, width=80, state='disabled')
    convo.grid(row=0, column=0, columnspan=6, sticky='nsew')
    scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=convo.yview)
    scrollbar.grid(row=0, column=6, sticky='ns')
    convo.configure(yscrollcommand=scrollbar.set)
    text_frame.rowconfigure(0, weight=1)
    text_frame.columnconfigure(0, weight=1)

    # Input + buttons
    entry_var = tk.StringVar()
    entry = ttk.Entry(text_frame, textvariable=entry_var, width=60)
    entry.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(8,0))
    text_frame.columnconfigure(0, weight=1)

    send_btn = ttk.Button(text_frame, text='Send')
    send_btn.grid(row=1, column=2, padx=5, pady=(8,0), sticky='e')
    clear_btn = ttk.Button(text_frame, text='Clear')
    clear_btn.grid(row=1, column=3, padx=5, pady=(8,0))
    dump_btn = ttk.Button(text_frame, text='Dump History')
    dump_btn.grid(row=1, column=4, padx=5, pady=(8,0))
    quit_btn = ttk.Button(text_frame, text='Quit', command=root.destroy)
    quit_btn.grid(row=1, column=5, padx=5, pady=(8,0))

    streaming_active = {'value': False}
    streaming_buffer = {'text': ''}

    # --- Utility ---
    def append(text: str):
        convo.configure(state='normal')
        convo.insert('end', text + '\n')
        convo.see('end')
        convo.configure(state='disabled')
        print(text)

    def append_no_newline(text: str):
        convo.configure(state='normal')
        convo.insert('end', text)
        convo.see('end')
        convo.configure(state='disabled')

    def embed_image(pil_image, caption: str):
        if not _PIL_AVAILABLE:
            append(f"[PIL not installed: {caption}]")
            return
        photo = ImageTk.PhotoImage(pil_image)
        _image_refs.append(photo)
        convo.configure(state='normal')
        convo.insert('end', caption + '\n')
        convo.image_create('end', image=photo)
        convo.insert('end', '\n')
        convo.see('end')
        convo.configure(state='disabled')

    def format_history_lines(include_system=False):
        with history_lock:
            for msg in messages:
                if msg['role'] == 'system' and not include_system:
                    continue
                yield f"[{msg['role']}] {msg['content']}"

    def print_history(include_system=False):
        print('\n=== Conversation History ===')
        for line in format_history_lines(include_system=include_system):
            print(line)
        print('=== End History ===\n')

    def clear_conversation():
        with history_lock:
            system = messages[0]
            messages.clear()
            messages.append(system)
        convo.configure(state='normal')
        convo.delete('1.0','end')
        convo.configure(state='disabled')
        append('[Conversation cleared]')
        print_history(include_system=True)

    clear_btn.configure(command=clear_conversation)

    # --- Ollama model pull (text only) ---
    def pull_model_if_needed(model_name: str):
        if model_name in loaded_models:
            return
        try:
            pull_status_var.set(f'Pulling {model_name}…')
            ollama.pull(model_name)
            loaded_models.add(model_name)
            pull_status_var.set(f'{model_name} ready')
        except Exception as e:
            pull_status_var.set(f'Pull failed {model_name}')
            append(f"[Error pulling {model_name}: {e}]")

    def initial_pull():
        pull_model_if_needed(TEXT_MODEL)
        if _REQUESTS_AVAILABLE:
            try:
                r = requests.get(f'{SD_API_URL}/sdapi/v1/progress', timeout=3)
                if r.status_code == 200:
                    pull_status_var.set('Models & SD ready')
                else:
                    pull_status_var.set('Text ready / SD unreachable')
            except Exception:
                pull_status_var.set('Text ready / SD offline')
        else:
            pull_status_var.set('Text ready / install requests for SD')

    threading.Thread(target=initial_pull, daemon=True).start()

    # --- Streaming helpers ---
    def begin_stream():
        streaming_active['value'] = True
        streaming_buffer['text'] = ''
        convo.configure(state='normal')
        convo.insert('end', f'{TEXT_MODEL}: ')
        convo.see('end')
        convo.configure(state='disabled')

    def stream_token(delta: str):
        if not streaming_active['value']:
            return
        streaming_buffer['text'] += delta
        append_no_newline(delta)

    def end_stream():
        if not streaming_active['value']:
            return
        convo.configure(state='normal')
        convo.insert('end', '\n')
        convo.configure(state='disabled')
        streaming_active['value'] = False

    # --- /img parsing ---
    def parse_image_command(raw: str):
        """/img <prompt> [|| negative prompt]
        Example: /img a red sunset over mountains || blurry, low quality
        """
        body = raw[len('/img'):].strip()
        if '||' in body:
            prompt, negative = body.split('||', 1)
            return prompt.strip(), negative.strip()
        return body.strip(), ''

    # --- Stable Diffusion generation (Automatic1111) ---
    def generate_image(prompt: str, negative: str):
        if not _REQUESTS_AVAILABLE:
            root.after(0, lambda: append('[Install requests: pip install requests]'))
            return
        payload = {
            'prompt': prompt,
            'negative_prompt': negative,
            'steps': 25,
            'width': 512,
            'height': 512,
            'sampler_name': 'Euler a'
        }
        try:
            resp = requests.post(SD_TXT2IMG_ENDPOINT, json=payload, timeout=120)
        except Exception as e:
            root.after(0, lambda e=e: append(f'[SD request error: {e}]'))
            return
        if resp.status_code != 200:
            root.after(0, lambda: append(f'[SD HTTP {resp.status_code}: {resp.text[:100]}]'))
            return
        try:
            data = resp.json()
        except Exception as e:
            root.after(0, lambda e=e: append(f'[SD JSON parse error: {e}]'))
            return
        images = data.get('images') or []
        if not images:
            root.after(0, lambda: append('[SD returned no images]'))
            return
        os.makedirs('generated_images', exist_ok=True)
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        for idx, b64img in enumerate(images):
            try:
                binary = base64.b64decode(b64img)
            except Exception as e:
                root.after(0, lambda e=e: append(f'[Decode failed: {e}]'))
                continue
            filename = f'generated_images/{ts}_{idx}.png'
            try:
                with open(filename, 'wb') as f:
                    f.write(binary)
            except Exception as e:
                root.after(0, lambda e=e, fn=filename: append(f'[Write failed {fn}: {e}]'))
                continue
            if _PIL_AVAILABLE:
                try:
                    img = Image.open(io.BytesIO(binary))
                except Exception as e:
                    root.after(0, lambda e=e: append(f'[PIL open failed: {e}]'))
                    continue
                root.after(0, lambda img=img, fn=filename: embed_image(img, f'Image saved: {fn}'))
            else:
                root.after(0, lambda fn=filename: append(f'Image saved: {fn} (install Pillow to preview)'))

    # --- Text inference ---
    def do_inference(user_msg: str):
        pull_model_if_needed(TEXT_MODEL)
        try:
            with history_lock:
                temp_history = messages + [{'role': 'user', 'content': user_msg}]
            print(f'--- Streaming response from {TEXT_MODEL} ---')
            root.after(0, begin_stream)
            full_chunks = []
            stream_resp = chat(model=TEXT_MODEL, messages=temp_history, stream=True)
            for part in stream_resp:
                delta = part.get('message', {}).get('content', '')
                if delta:
                    full_chunks.append(delta)
                    root.after(0, lambda d=delta: stream_token(d))
                    print(delta, end='', flush=True)
            print('\n--- End of streamed response ---')
            resp_text = ''.join(full_chunks).strip() or '[No content returned]'
        except Exception as e:
            resp_text = f'[Error querying model {TEXT_MODEL}: {e}]'
        root.after(0, lambda: finalize_response(user_msg, resp_text))

    def finalize_response(user_msg: str, resp_text: str):
        end_stream()
        with history_lock:
            messages.append({'role': 'user', 'content': user_msg})
            messages.append({'role': 'assistant', 'content': resp_text})
        print_history(include_system=False)
        send_btn.configure(state='normal')
        entry.configure(state='normal')
        entry_var.set('')
        entry.focus()

    # --- Handlers ---
    def handle_image_command(raw: str):
        prompt, negative = parse_image_command(raw)
        if not prompt:
            append('[Usage] /img <prompt> [|| negative prompt]')
            send_btn.configure(state='normal')
            entry.configure(state='normal')
            return
        append(f'You (image prompt): {prompt}' + (f' | neg: {negative}' if negative else ''))
        with history_lock:
            summary = prompt if len(prompt) < 120 else prompt[:117] + '...'
            messages.append({'role': 'user', 'content': f'(image prompt) {summary}'})
        threading.Thread(target=generate_image, args=(prompt, negative), daemon=True).start()
        send_btn.configure(state='normal')
        entry.configure(state='normal')
        entry_var.set('')
        entry.focus()

    def send(event=None):
        user_msg = entry_var.get().strip()
        if not user_msg:
            return
        send_btn.configure(state='disabled')
        entry.configure(state='disabled')
        if user_msg.startswith('/img'):
            handle_image_command(user_msg)
            return
        append(f'You: {user_msg}')
        threading.Thread(target=do_inference, args=(user_msg,), daemon=True).start()

    def dump_history_action():
        print_history(include_system=True)

    dump_btn.configure(command=dump_history_action)
    send_btn.configure(command=send)
    entry.bind('<Return>', send)

    # Initial message
    if not _REQUESTS_AVAILABLE:
        append('Install requests (pip install requests) for image generation.')
    append('Ready. Text via gemma3. Images: /img <prompt> [|| negative]. Requires running Automatic1111 at 127.0.0.1:7860.')
    entry.focus()

    if sv_ttk is not None:
        try:
            sv_ttk.set_theme('dark')
        except Exception:
            pass

    root.mainloop()

if __name__ == '__main__':
    main()