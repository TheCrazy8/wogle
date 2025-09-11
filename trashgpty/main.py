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

import os, io, base64, datetime, json, re
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
SD_PROGRESS_ENDPOINT = f'{SD_API_URL}/sdapi/v1/progress'

# SD runtime feature flags
SD_AVAILABLE = {'value': False}  # mutable container so inner closures can modify
SD_LAST_ERROR = {'value': None}

# Keep track of which models we've already pulled in this session (for Ollama text only)
loaded_models = set()
_image_refs = []  # Prevent GC of PhotoImages

# ------------------------------------------------------------
# Utility: check Stable Diffusion availability
# ------------------------------------------------------------
def check_sd_available(timeout=4):
    if not _REQUESTS_AVAILABLE:
        SD_AVAILABLE['value'] = False
        SD_LAST_ERROR['value'] = 'requests not installed'
        return False, SD_LAST_ERROR['value']
    try:
        r = requests.get(SD_PROGRESS_ENDPOINT, timeout=timeout)
        if r.status_code == 200:
            SD_AVAILABLE['value'] = True
            SD_LAST_ERROR['value'] = None
            return True, None
        SD_AVAILABLE['value'] = False
        SD_LAST_ERROR['value'] = f'HTTP {r.status_code}'
        return False, SD_LAST_ERROR['value']
    except Exception as e:
        SD_AVAILABLE['value'] = False
        SD_LAST_ERROR['value'] = str(e)
        return False, SD_LAST_ERROR['value']


def main():
    """Tkinter chat UI with fixed text model (gemma3) + external Stable Diffusion for /img and /web."""
    root = tk.Tk()
    root.title("AI Chat (gemma3 + SD + /web)")

    history_lock = threading.Lock()
    messages = [{'role': 'system', 'content': "You are a helpful AI assistant. You may be given fetched web excerpts labeled 'WEB EXCERPT' to ground answers."}]

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

    # --- Utility append functions (unchanged) ---
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

    # --- Model pull (text only) ---
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

    def initial_startup():
        pull_model_if_needed(TEXT_MODEL)
        ok, err = check_sd_available()
        if ok:
            pull_status_var.set('Text ready / SD online')
        else:
            pull_status_var.set(f'Text ready / SD offline ({err})')
            append(f'[Stable Diffusion offline: {err}] Start Automatic1111 WebUI on {SD_API_URL} to enable /img.')

    threading.Thread(target=initial_startup, daemon=True).start()

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
        body = raw[len('/img'):].strip()
        if '||' in body:
            prompt, negative = body.split('||', 1)
            return prompt.strip(), negative.strip()
        return body.strip(), ''

    # --- Stable Diffusion generation (Automatic1111) with availability guard ---
    def generate_image(prompt: str, negative: str):
        if not SD_AVAILABLE['value']:
            append(f'[SD offline: {SD_LAST_ERROR["value"] or "not reachable"}] Use /sdstatus after starting the WebUI.')
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
            append(f'[SD request error: {e}]')
            SD_AVAILABLE['value'] = False
            SD_LAST_ERROR['value'] = str(e)
            return
        if resp.status_code != 200:
            append(f'[SD HTTP {resp.status_code}: {resp.text[:100]}]')
            return
        try:
            data = resp.json()
        except Exception as e:
            append(f'[SD JSON parse error: {e}]')
            return
        images = data.get('images') or []
        if not images:
            append('[SD returned no images]')
            return
        os.makedirs('generated_images', exist_ok=True)
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        for idx, b64img in enumerate(images):
            try:
                binary = base64.b64decode(b64img)
            except Exception as e:
                append(f'[Decode failed: {e}]')
                continue
            filename = f'generated_images/{ts}_{idx}.png'
            try:
                with open(filename, 'wb') as f:
                    f.write(binary)
            except Exception as e:
                append(f'[Write failed {filename}: {e}]')
                continue
            if _PIL_AVAILABLE:
                try:
                    img = Image.open(io.BytesIO(binary))
                except Exception as e:
                    append(f'[PIL open failed: {e}]')
                    continue
                embed_image(img, f'Image saved: {filename}')
            else:
                append(f'Image saved: {filename} (install Pillow to preview)')

    # --- /web, fetch helpers (unchanged from previous revision) ---
    def sanitize_url_or_query(arg: str):
        if re.match(r'^https?://', arg, re.I):
            return arg, None
        return None, arg

    def duckduckgo_search(query: str, max_results=3):
        if not _REQUESTS_AVAILABLE:
            return []
        try:
            r = requests.get('https://duckduckgo.com/html/', params={'q': query}, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code != 200:
                return []
            links = re.findall(r'<a rel="nofollow" class="result__a" href="(.*?)"', r.text)
            cleaned = []
            for l in links:
                if l.startswith('http') and 'duckduckgo.com' not in l:
                    cleaned.append(l)
                if len(cleaned) >= max_results:
                    break
            return cleaned
        except Exception:
            return []

    def fetch_url(url: str, max_chars=6000):
        if not _REQUESTS_AVAILABLE:
            return '[requests not installed]', ''
        try:
            resp = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            if resp.status_code != 200:
                return f'[HTTP {resp.status_code}]', ''
            text = resp.text
        except Exception as e:
            return f'[Fetch error: {e}]', ''
        stripped = re.sub(r'<script.*?</script>|<style.*?</style>', '', text, flags=re.S|re.I)
        stripped = re.sub(r'<[^>]+>', ' ', stripped)
        stripped = re.sub(r'&nbsp;|&amp;|&lt;|&gt;', ' ', stripped)
        stripped = re.sub(r'\s+', ' ', stripped).strip()
        snippet = stripped[:max_chars]
        return None, snippet

    def summarize_snippet(snippet: str):
        if not snippet:
            return '[Empty snippet]'
        chunks = []
        size = 1000
        for i in range(0, len(snippet), size):
            chunks.append(snippet[i:i+size])
        summaries = []
        for idx, ch in enumerate(chunks[:4]):
            try:
                resp = chat(model=TEXT_MODEL, messages=[
                    {'role': 'system', 'content': 'Summarize the provided web text accurately and concisely.'},
                    {'role': 'user', 'content': ch}
                ])
                summaries.append(resp['message']['content'])
            except Exception as e:
                summaries.append(f'[Summarization error chunk {idx}: {e}]')
        return '\n'.join(summaries)

    def handle_web_command(raw: str):
        arg = raw[len('/web'):].strip()
        if not arg:
            append('[Usage] /web <url or search terms>')
            return finalize_web(None)
        url, query = sanitize_url_or_query(arg)
        urls = []
        if url:
            urls = [url]
        else:
            append(f'[Searching: {query}]')
            urls = duckduckgo_search(query, max_results=2)
            if not urls:
                append('[No search results]')
                return finalize_web(None)
        append(f'[Fetching {len(urls)} source(s)]')
        def worker():
            combined_contexts = []
            for u in urls:
                err, snippet = fetch_url(u)
                if err:
                    root.after(0, lambda e=err: append(f'{u} -> {e}'))
                    continue
                summary = summarize_snippet(snippet)
                combined_contexts.append(f'URL: {u}\nSUMMARY:\n{summary}')
            if not combined_contexts:
                root.after(0, lambda: finalize_web(None))
                return
            web_block = '\n\n'.join(combined_contexts)
            with history_lock:
                messages.append({'role': 'system', 'content': f'WEB EXCERPT BEGIN\n{web_block}\nWEB EXCERPT END'})
            root.after(0, lambda: finalize_web(len(combined_contexts)))
        threading.Thread(target=worker, daemon=True).start()

    def finalize_web(ct):
        send_btn.configure(state='normal')
        entry.configure(state='normal')
        entry_var.set('')
        if ct:
            append(f'[Added {ct} summarized source(s) to context]')
        entry.focus()

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

    def handle_sdstatus():
        append('[Checking Stable Diffusion status…]')
        def worker():
            ok, err = check_sd_available()
            root.after(0, lambda: append('[SD online]' if ok else f'[SD offline: {err}]'))
        threading.Thread(target=worker, daemon=True).start()

    def send(event=None):
        user_msg = entry_var.get().strip()
        if not user_msg:
            return
        send_btn.configure(state='disabled')
        entry.configure(state='disabled')
        if user_msg.startswith('/img'):
            handle_image_command(user_msg)
            return
        if user_msg.startswith('/web'):
            handle_web_command(user_msg)
            return
        if user_msg.startswith('/sdstatus'):
            handle_sdstatus()
            send_btn.configure(state='normal')
            entry.configure(state='normal')
            entry_var.set('')
            entry.focus()
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
        append('Install requests (pip install requests) for /web & /img commands.')
    append('Ready. Commands: /img <prompt> [|| negative], /web <url or search terms>, /sdstatus to re-check Stable Diffusion availability.')
    entry.focus()

    if sv_ttk is not None:
        try:
            sv_ttk.set_theme('dark')
        except Exception:
            pass

    root.mainloop()

if __name__ == '__main__':
    main()