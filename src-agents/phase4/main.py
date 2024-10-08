import os
import json
import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from enum import Enum
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
# import redis
from azure.search.documents.models import (
    VectorizedQuery
)
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

app = FastAPI()

load_dotenv()

credential = AzureKeyCredential(os.environ["AZURE_AI_SEARCH_KEY"]) if len(
    os.environ["AZURE_AI_SEARCH_KEY"]) > 0 else DefaultAzureCredential()


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

# Redis connection details
redis_host = os.getenv('REDIS_HOST')
redis_port = os.getenv('REDIS_PORT')
redis_password = os.getenv('REDIS_PASSWORD')

# Connect to the Redis server
# conn = redis.Redis(host=redis_host, port=redis_port,
#                    password=redis_password, encoding='utf-8', decode_responses=True)

# if conn.ping():
#     print("Connected to Redis")

service_endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL")


def get_embedding(text, model=embedding_model):
    return client.embeddings.create(input=[text], model=model).data[0].embedding


@app.get("/")
async def root():
    return {"message": "Hello Smorgs"}


@app.post("/ask", summary="Ask a question", operation_id="ask")
async def ask_question(ask: Ask):
    """
    Ask a question
    """
    print(ask.question)
    index_name = "question-semantic-index"

    # create new searchclient using our new index for the questions
    search_client = SearchClient(
        endpoint=os.environ["AZURE_AI_SEARCH_ENDPOINT"],
        index_name=index_name,
        credential=credential
    )

    # create a vectorized query based on the question
    vector = VectorizedQuery(vector=get_embedding(
        ask.question), k_nearest_neighbors=5, fields="vector")

    # create search client to retrieve movies from the vector store
    found_questions = list(search_client.search(
        search_text=None,
        query_type="semantic",
        semantic_configuration_name="question-semantic-config",
        vector_queries=[vector],
        select=["question", "answer"],
        top=5,
        minimum_similarity=0.9
    ))

    questionMatchCount = len(found_questions)
    if (questionMatchCount > 0):
        print("Found a match in the cache.")
        # put the new question & answer in the cache as well
        docIdCount = search_client.get_document_count() + 1
        # add the new question and answer to the cache
        search_client.upload_documents(documents=[
            {
                "id": str(docIdCount),
                "question": ask.question,
                "answer": response.choices[0].message.content
            }
        ])
        return answer
    else:
        print("No match found in the cache.")

        #   reach out to the llm to get the answer.
        print('Sending a request to LLM')
        start_phrase = ask.question
        messages = [{"role": "assistant", "content": start_phrase},
                    {"role": "system", "content": "Answer this question with a very short answer. Don't answer with a full sentence, and do not format the answer."}]

        response = client.chat.completions.create(
            model=deployment_name,
            messages=messages,
        )
        answer = Answer(answer=response.choices[0].message.content)

        #  put the new question & answer in the cache as well
        docIdCount = search_client.get_document_count() + 1
        search_client.upload_documents(documents=[
            {
                "id": str(docIdCount),
                "question": ask.question,
                "answer": response.choices[0].message.content
            }
        ])

        print("Added a new answer and question to the cache: " +
              answer.answer + "in position" + str(docIdCount))
        return answer
