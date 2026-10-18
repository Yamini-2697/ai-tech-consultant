from fastapi import FastAPI
from pydantic import BaseModel, Field

import os
from dotenv import load_dotenv

from task1_knowledge_brain.database import (
    initialize_database,
    search_articles,
)
load_dotenv()
from anthropic import Anthropic

api_key = os.getenv("ANTHROPIC_API_KEY")

client = Anthropic(api_key=api_key) if api_key else None

app = FastAPI(
    title="AI Tech Consultant",
    description="Knowledge Brain API",
    version="1.0.0",
)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


@app.on_event("startup")
async def startup():
    initialize_database()


@app.get("/")
async def home():
    return {
        "project": "AI Tech Consultant",
        "task": "Knowledge Brain",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/ask")
async def ask_question(request: QuestionRequest):
    articles = search_articles(request.question, limit=5)

    if not articles:
        return {
            "question": request.question,
            "answer": None,
            "sources": [],
            "message": (
                "I could not find relevant articles. "
                "A human expert may need to answer this question."
            ),
        }

    sources = [
        {
            "title": article["title"],
            "url": article["url"],
        }
        for article in articles
    ]

    context = "\n\n".join(
        f"Title: {article['title']}\n"
        f"URL: {article['url']}\n"
        f"Content: {article['content'][:1500]}"
        for article in articles
    )

    if client is None:
        answer = (
            "Claude API is not configured. "
            "Please configure ANTHROPIC_API_KEY."
        )
    else:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=800,
            system=(
                "You are a helpful technical support assistant. "
                "Answer using only the supplied help-center context. "
                "If the context does not contain the answer, say so. "
                "Do not invent information."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Question: {request.question}\n\n"
                        f"Help-center context:\n{context}"
                    ),
                }
            ],
        )
        answer = response.content[0].text

    return {
        "question": request.question,
        "answer": answer,
        "sources": sources,
        "retrieved_context": context,
    }


