# Moral Short Stories API

A REST API built with FastAPI serving Panchatantra-style and classic moral short stories, each with a title, full story text, moral/lesson, origin, characters, and tags.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   (On Windows, if `pip` doesn't work directly, use `py -m pip install -r requirements.txt`)

2. Run the server:
   ```bash
   uvicorn main:app --reload
   ```
   (On Windows: `py -m uvicorn main:app --reload`)

3. Open your browser:
   - API root: http://127.0.0.1:8000/
   - Interactive Swagger docs: http://127.0.0.1:8000/docs

## Endpoints

| Method | Endpoint                | Description                                         |
|--------|---------------------------|------------------------------------------------------|
| GET    | `/`                        | Welcome message + API guide                          |
| GET    | `/stories`                 | Paginated list of stories (filter by origin/character)|
| GET    | `/stories/{id}`            | Get a single story by ID                              |
| GET    | `/stories/random`          | Get one random story                                  |
| GET    | `/stories/search?q=...`    | Search stories by keyword                             |
| GET    | `/origins`                 | List all story origins (Panchatantra, Aesop's, etc.)  |
| GET    | `/morals`                  | List every story's title + moral/lesson               |

## Examples

```
GET /stories
GET /stories?page=1&limit=5
GET /stories?origin=Panchatantra
GET /stories?character=Fox
GET /stories/random
GET /stories/1
GET /stories/search?q=greed
GET /origins
GET /morals
```

## Project Structure

```
short-stories-api/
├── main.py
├── data/
│   └── stories.json    # Seed dataset (20 stories)
├── requirements.txt
└── README.md
```

## Data

Seeded with 20 classic moral stories, sourced from traditions like the Panchatantra and Aesop's Fables, each written in original wording with title, full story, moral, origin, characters, and tags.

## Next steps / ideas to extend

- Add more stories (currently 20)
- Add a `POST /stories` endpoint to add new stories via API
- Move to a real database (SQLite) for easier growth
- Deploy online (e.g., Render) for a public URL
