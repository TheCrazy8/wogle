import ollama
from ollama import chat
from ollama import ChatResponse

ollama.pull('gemma3')

def main():
    msg = input("Enter your message: ")

    response: ChatResponse = chat(model='gemma3', messages=[
        {
            'role': 'user',
            'content': msg,
        },
    ])
    print(response['message']['content'])
    # or access fields directly from the response object
    print(response.message.content)

if __name__ == "__main__":
    main()