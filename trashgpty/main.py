import ollama

ollama.pull('llama2')
name = "__main__"
def main():
    msg = input("Enter your message: ")
    # Send a chat message to a specified model
    response = ollama.chat(model='llama2', messages=[
        {
            'role': 'user',
            'content': msg,
        },
    ])

    # Print the model's response
    print(response['message']['content'])

if __name__ == "__main__":
    main()