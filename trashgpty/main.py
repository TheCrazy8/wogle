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

import os, io, base64, datetime, json, re, subprocess, time, sys
try:
    from PIL import Image, ImageTk
    _PIL_AVAILABLE = True
except Exception:
    _PIL_AVAILABLE = False

# HTTP dependency (still used for /web)
try:
    import requests
    _REQUESTS_AVAILABLE = True
except Exception:
    _REQUESTS_AVAILABLE = False

# DeepFloyd IF (diffusers) dependency
try:
    import torch
    from diffusers import IFPipeline  # Stage 1 only for now
    _IF_AVAILABLE = True
except Exception:
    _IF_AVAILABLE = False

# Fixed text model (Ollama)
TEXT_MODEL = 'gemma3'

###############################################
# DeepFloyd IF configuration
###############################################
# Model repo: https://huggingface.co/DeepFloyd/IF-I-XL-v1.0
# This model is large and requires significant GPU VRAM (recommended >= 16GB for fp16).
# We load only Stage I for a faster first integration. Add super-resolution stages later if desired.
IF_MODEL_ID = os.environ.get('IF_MODEL_ID', 'DeepFloyd/IF-I-XL-v1.0')
IF_PIPELINE = {'pipe': None, 'loading': False, 'error': None}
IF_DEVICE = 'cuda' if 'torch' in globals() and hasattr(torch, 'cuda') and torch.cuda.is_available() else 'cpu'
IF_DTYPE = torch.float16 if IF_DEVICE == 'cuda' else torch.float32

# Keep track of which models we've already pulled in this session (for Ollama text only)
loaded_models = set()
_image_refs = []  # Prevent GC of PhotoImages

def load_if_pipeline_async(callback=None):
    """Load DeepFloyd IF pipeline in a background thread."""
    if not _IF_AVAILABLE:
        IF_PIPELINE['error'] = 'diffusers/torch not installed'
        if callback:
            callback(False, IF_PIPELINE['error'])
        return
    if IF_PIPELINE['pipe'] is not None or IF_PIPELINE['loading']:
        if callback:
            callback(True, None)
        return
    IF_PIPELINE['loading'] = True
    def worker():
        try:
            pipe = IFPipeline.from_pretrained(IF_MODEL_ID, variant="fp16" if IF_DTYPE==torch.float16 else None, torch_dtype=IF_DTYPE)
            # Move to device
            pipe.to(IF_DEVICE)
            IF_PIPELINE['pipe'] = pipe
            IF_PIPELINE['error'] = None
            ok = True
        except Exception as e:
            IF_PIPELINE['error'] = str(e)
            ok = False
        finally:
            IF_PIPELINE['loading'] = False
        if callback:
            callback(ok, IF_PIPELINE['error'])
    threading.Thread(target=worker, daemon=True).start()


def main():
    """Tkinter chat UI with fixed text model (gemma3), external Stable Diffusion (/img), /web fetch, and SD autostart."""
    root = tk.Tk()
    root.title("AI Chat (gemma3 + DeepFloyd IF + /web)")

    history_lock = threading.Lock()
    messages = [{'role': 'system', 'content': "You are a helpful AI assistant. You may be given fetched web excerpts labeled 'WEB EXCERPT' to ground answers."}]

    # --- Top bar ---
    top_frame = ttk.Frame(root, padding=(10, 10, 10, 0))
    top_frame.grid(row=0, column=0, sticky='ew')
    root.columnconfigure(0, weight=1)

    ttk.Label(top_frame, text=f"Text model: {TEXT_MODEL}").grid(row=0, column=0, sticky='w')
    ttk.Label(top_frame, text=f"Image: DeepFloyd IF").grid(row=0, column=1, padx=15, sticky='w')

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

    # --- Utility append functions ---
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

    # --- Initial startup: pull text model only ---
    def initial_startup():
        pull_model_if_needed(TEXT_MODEL)
        pull_status_var.set('Text model ready / IF idle')
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

    # --- DeepFloyd IF generation ---
    def generate_image(prompt: str, negative: str):
        if not _IF_AVAILABLE:
            append('[DeepFloyd IF not available: install torch, diffusers, transformers, accelerate, safetensors]')
            return
        if IF_PIPELINE['pipe'] is None:
            if IF_PIPELINE['loading']:
                append('[IF model still loading… please wait]')
                return
            append('[Loading DeepFloyd IF model (first load can take minutes & large disk download)…]')
            def after_load(ok, err):
                if ok:
                    append('[IF model loaded]')
                    threading.Thread(target=lambda: generate_image(prompt, negative), daemon=True).start()
                else:
                    append(f'[IF load error: {err}]')
            load_if_pipeline_async(callback=lambda ok, err: root.after(0, lambda: after_load(ok, err)))
            return
        pipe = IF_PIPELINE['pipe']
        try:
            generator = torch.manual_seed(int(time.time()) % 2**32)
            out = pipe(prompt=prompt, negative_prompt=negative or None, guidance_scale=7.0, generator=generator, num_inference_steps=50)
            images = out.images
        except Exception as e:
            append(f'[IF inference error: {e}]')
            return
        if not images:
            append('[IF returned no images]')
            return
        os.makedirs('generated_images', exist_ok=True)
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        for idx, img in enumerate(images):
            filename = f'generated_images/{ts}_if_{idx}.png'
            try:
                img.save(filename)
            except Exception as e:
                append(f'[Save failed {filename}: {e}]')
                continue
            if _PIL_AVAILABLE:
                embed_image(img, f'Image saved: {filename}')
            else:
                append(f'Image saved: {filename} (install Pillow to preview)')

    # --- /web helpers (unchanged logic) ---
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
            links = re.findall(r'<a rel=\"nofollow\" class=\"result__a\" href=\"(.*?)\"', r.text)
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
            finalize_web(None)
            return
        url, query = sanitize_url_or_query(arg)
        urls = []
        if url:
            urls = [url]
        else:
            append(f'[Searching: {query}]')
            urls = duckduckgo_search(query, max_results=2)
            if not urls:
                append('[No search results]')
                finalize_web(None)
                return
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

    # Optional: command to reload IF
    def handle_ifreload():
        if IF_PIPELINE['loading']:
            append('[IF already loading]')
            return
        IF_PIPELINE['pipe'] = None
        append('[Reloading IF pipeline…]')
        load_if_pipeline_async(callback=lambda ok, err: root.after(0, lambda: append('[IF model loaded]' if ok else f'[IF load error: {err}]')))

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
        if user_msg.startswith('/ifreload'):
            handle_ifreload()
            reset_input_state()
            return
        append(f'You: {user_msg}')
        threading.Thread(target=do_inference, args=(user_msg,), daemon=True).start()

    def reset_input_state():
        send_btn.configure(state='normal')
        entry.configure(state='normal')
        entry_var.set('')
        entry.focus()

    def dump_history_action():
        print_history(include_system=True)

    dump_btn.configure(command=dump_history_action)
    send_btn.configure(command=send)
    entry.bind('<Return>', send)

    # Initial message
    if not _REQUESTS_AVAILABLE:
        append('Install requests (pip install requests) for /web & /img & SD autostart.')
    append('Ready. Commands: /img <prompt> [|| negative], /web <url or search>, /ifreload (reload DeepFloyd IF).')
    if not _IF_AVAILABLE:
        append('Install dependencies for IF: pip install torch diffusers transformers accelerate safetensors')
    entry.focus()

    if sv_ttk is not None:
        try:
            sv_ttk.set_theme('dark')
        except Exception:
            pass

    root.mainloop()

if __name__ == '__main__':
    main()