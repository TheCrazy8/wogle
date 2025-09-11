import ollama

ollama.pull('llama2')
name = "__main__"
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