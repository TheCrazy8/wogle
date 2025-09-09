import ollama
from ollama import chat
from ollama import ChatResponse
ollama.pull('llama2')

def main():
    # Send a chat message to a specified model
    response = ollama.chat(model='llama2', messages=[
        {
            'role': 'user',
            'content': input("Enter your message: "),
        },
    ])

    # Print the model's response
    print(response['message']['content'])

if __name__ == "__main__":
    main()