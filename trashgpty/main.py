import ollama
from ollama import chat
from ollama import ChatResponse

ollama.pull('gemma3')

def main():
    msg = input("User: ")

    response: ChatResponse = chat(model='gemma3', messages=[
        {
            'role': 'user',
            'content': msg,
        },
    ])
    resp = response['message']['content']
    # or access fields directly from the response object
    resp = response.message.content

    print(f"Gemma: {resp}")

    main()

if __name__ == "__main__":
    main()