import random

# Define a list of random answers
answers = [
    "It is certain.",
    "It is decidedly so.",
    "Without a doubt.",
    "Yes - definitely.",
    "You may rely on it.",
    "As I see it, yes.",
    "Most likely.",
    "Outlook good.",
    "Yes.",
    "Signs point to yes.",
    "Reply hazy, try again.",
    "Ask again later.",
    "Better not tell you now.",
    "Cannot predict now.",
    "Concentrate and ask again.",
    "Don't count on it.",
    "My reply is no.",
    "My sources say no.",
    "Outlook not so good.",
    "Very doubtful."
]

# Function to choose a random answer
def choose_random_answer():
    return random.choice(answers)

# Main program
while True:
    question = input("Ask me a question: ")
    if question.lower() == "exit":
        break
    answer = choose_random_answer()
    print(answer)
