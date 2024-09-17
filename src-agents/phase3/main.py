import os
import json
import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from enum import Enum
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

app = FastAPI()

load_dotenv()


class QuestionType(str, Enum):
    multiple_choice = "multiple_choice"
    true_or_false = "true_or_false"
    popular_choice = "popular_choice"
    estimation = "estimation"


class Ask(BaseModel):
    question: str | None = None
    type: QuestionType
    correlationToken: str | None = None


class Answer(BaseModel):
    answer: str
    correlationToken: str | None = None
    promptTokensUsed: int | None = None
    completionTokensUsed: int | None = None


client: AzureOpenAI

if "AZURE_OPENAI_API_KEY" in os.environ:
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
else:
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    client = AzureOpenAI(
        azure_ad_token_provider=token_provider,
        api_version=os.getenv("AZURE_OPENAI_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )

deployment_name = os.getenv("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME")
index_name = "movies-semantic-index"
service_endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
model_name = os.getenv("AZURE_OPENAI_COMPLETION_MODEL")


smoorghApi = "https://smoorgh-api.happypebble-f6fb3666.northeurope.azurecontainerapps.io/"


def get_movie_rating(title):
    try:
        headers = {"title": title}
        response = requests.get(f"{smoorghApi}rating", headers=headers)
        print('The api response for rating is:', response.text)
        return response.text

    except:
        return "Sorry, I couldn't find a rating for that movie."


def get_movie_year(title):
    try:
        headers = {"title": title}
        response = requests.get(f"{smoorghApi}year", headers=headers)
        print('The api response for year is:', response.text)
        return response.text

    except:
        return "Sorry, I couldn't find a year for that movie."


def get_movie_actor(title):
    try:
        headers = {"title": title}
        response = requests.get(f"{smoorghApi}actor", headers=headers)
        print('The api response for actor is:', response.text)
        return response.text

    except:
        return "Sorry, I couldn't find an actor for that movie."


def get_movie_location(title):
    try:
        headers = {"title": title}
        response = requests.get(f"{smoorghApi}location", headers=headers)
        print('The api response for location is:', response.text)
        return response.text

    except:
        return "Sorry, I couldn't find a location for that movie."


def get_movie_genre(title):
    try:
        headers = {"title": title}
        response = requests.get(f"{smoorghApi}genre", headers=headers)
        print('The api response for genre is:', response.text)
        return response.text

    except:
        return "Sorry, I couldn't find a genre for that movie."


functions = [
    {
        "type": "function",
        "function": {
                "name": "get_movie_rating",
                "description": "Gets the rating of a movie",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "The movie name. The movie name should be a string without quotation marks.",
                        }
                    },
                    "required": ["title"],
                },
        }
    },
    {
        "type": "function",
        "function": {
                "name": "get_movie_year",
                "description": "Gets the year of a movie",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "The movie name. The movie name should be a string without quotation marks.",
                        }
                    },
                    "required": ["title"],
                },
        }
    },
    {
        "type": "function",
        "function": {
                "name": "get_movie_actor",
                "description": "Gets the actor of a movie",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "The movie name. The movie name should be a string without quotation marks.",
                        }
                    },
                    "required": ["title"],
                },
        }
    },
    {
        "type": "function",
        "function": {
                "name": "get_movie_location",
                "description": "Gets the location of a movie",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "The movie name. The movie name should be a string without quotation marks.",
                        }
                    },
                    "required": ["title"],
                },
        }
    },
    {
        "type": "function",
        "function": {
                "name": "get_movie_genre",
                "description": "Gets the genre of a movie",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "The movie name. The movie name should be a string without quotation marks.",
                        }
                    },
                    "required": ["title"],
                },
        }
    }
]
available_functions = {
    "get_movie_rating": get_movie_rating,
    "get_movie_year": get_movie_year,
    "get_movie_actor": get_movie_actor,
    "get_movie_location": get_movie_location,
    "get_movie_genre": get_movie_genre
}


@app.get("/")
async def root():
    return {"message": "Hello Smorgs"}


@app.post("/ask", summary="Ask a question", operation_id="ask")
async def ask_question(ask: Ask):
    """
    Ask a question
    """
    if ask.type == QuestionType.multiple_choice:
        system_prompt = "Please choose the correct option:"
    elif ask.type == QuestionType.true_or_false:
        system_prompt = "Is the following statement true or false: answer in true or false in lower case without \".\""
    elif ask.type == QuestionType.popular_choice:
        system_prompt = "What is the most popular choice for:"
    else:
        system_prompt = "Please estimate the value of: Answer only in numbers."

    question = ask.question
    messages = [{"role": "assistant", "content": question}, {"role": "system", "content": "Answer this question with exact content only. Option number is not required. Answer will be used as such for verification. Numbers can also be used. Avoid unnecessary literals. Use the tools available to you. " + system_prompt}
                ]
    first_response = client.chat.completions.create(
        model=deployment_name,
        messages=messages,
        tools=functions,
        tool_choice="auto",
    )

    print(first_response)
    response_message = first_response.choices[0].message
    tool_calls = response_message.tool_calls
    print("Recommended Function call:")
    print(tool_calls)
    print()

    # Step 2: check if GPT wanted to call a function
    if tool_calls:
        # Step 3: call the function
        messages.append(response_message)

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            # verify function exists
            if function_name not in available_functions:
                return "Function " + function_name + " does not exist"
            else:
                print("Calling function: " + function_name)
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)
            print(function_args)
            function_response = function_to_call(**function_args)
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                }
            )
            print("Adding this message to the next prompt:")
            print(messages)

            # extend conversation with function response
            second_response = client.chat.completions.create(
                model=deployment_name,
                # get a new response from the model where it can see the function response
                messages=messages)

            print("second_response")
            messages.append(second_response.choices[0].message)
    if tool_calls:
        answer = Answer(answer=second_response.choices[0].message.content)
        answer.promptTokensUsed = second_response.usage.prompt_tokens
        answer.completionTokensUsed = second_response.usage.completion_tokens
    else:
        answer = Answer(answer=first_response.choices[0].message.content)
        answer.promptTokensUsed = first_response.usage.prompt_tokens
        answer.completionTokensUsed = first_response.usage.completion_tokens
    answer.correlationToken = ask.correlationToken
    return answer


@app.get("/get_actor/{title}", summary="Get the actor of a movie", operation_id="get_actor")
async def get_actor(title: str):
    """
    Get the actor of a movie
    """
    actor = get_movie_actor("Hobbiton: The Heist of the Silver Dragon")
    return {"actor": actor}
