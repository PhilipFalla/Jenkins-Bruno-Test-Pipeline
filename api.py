import os
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
from pydantic import BaseModel, Field

API_KEY = os.getenv("DEMO_API_KEY")  # unset = no auth
SEED = [
    {"title": "Grokking Continuous Delivery", "author": "Christie Wilson", "year": 2022, "copies": 3},
    {"title": "Accelerate", "author": "Forsgren, Humble, Kim", "year": 2018, "copies": 2},
    {"title": "Working Effectively with Legacy Code", "author": "Michael Feathers", "year": 2004, "copies": 1},
]

books: dict[int, dict] = {}
next_id = 0


def seed() -> None:
    global books, next_id
    books, next_id = {}, 0
    for row in SEED:
        create(row)


def create(data: dict) -> dict:
    global next_id
    next_id += 1
    book = {"id": next_id, **data}
    books[next_id] = book
    return book


def get_or_404(book_id: int) -> dict:
    book = books.get(book_id)
    if book is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no book with id {book_id}")
    return book


async def require_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "X-API-Key missing or wrong")


class BookIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    author: str = Field(min_length=1, max_length=120)
    year: int = Field(ge=1450, le=2100)  # 1450 = Gutenberg, a boundary worth asking about
    copies: int = Field(default=1, ge=0, le=999)


class BookPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    author: str | None = Field(default=None, min_length=1, max_length=120)
    year: int | None = Field(default=None, ge=1450, le=2100)
    copies: int | None = Field(default=None, ge=0, le=999)


app = FastAPI(title="Books demo API", version="1.0.0")
writes = [Depends(require_key)]


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "books": len(books)}


@app.get("/books")
async def list_books(author: str | None = None) -> list[dict]:
    if author is None:
        return list(books.values())
    return [b for b in books.values() if author.lower() in b["author"].lower()]


@app.post("/books", status_code=201, dependencies=writes)
async def add_book(book: BookIn, response: Response) -> dict:
    created = create(book.model_dump())
    response.headers["Location"] = f"/books/{created['id']}"
    return created


@app.get("/books/{book_id}")
async def read_book(book_id: int) -> dict:
    return get_or_404(book_id)


@app.head("/books/{book_id}")
async def head_book(book_id: int) -> Response:
    get_or_404(book_id)
    return Response(status_code=200)


@app.put("/books/{book_id}", dependencies=writes)
async def replace_book(book_id: int, book: BookIn) -> dict:
    get_or_404(book_id)
    books[book_id] = {"id": book_id, **book.model_dump()}
    return books[book_id]


@app.patch("/books/{book_id}", dependencies=writes)
async def edit_book(book_id: int, patch: BookPatch) -> dict:
    book = get_or_404(book_id)
    book.update(patch.model_dump(exclude_unset=True))
    return book


@app.delete("/books/{book_id}", status_code=204, dependencies=writes)
async def remove_book(book_id: int) -> Response:
    get_or_404(book_id)
    del books[book_id]
    return Response(status_code=204)


@app.options("/books")
async def options_books() -> Response:
    return Response(status_code=204, headers={"Allow": "GET, POST, OPTIONS"})


@app.post("/reset")
async def reset() -> dict:
    seed()
    return {"status": "reset", "books": len(books)}


seed()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "8000")), log_level="info")
