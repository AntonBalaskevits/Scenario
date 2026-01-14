## Features

- CSV-based data source (transactions & FX rates)
- Average, total, min/max transaction statistics
- Dynamic currency dropdowns in Swagger
- Admin reload endpoint (`POST /admin/reload`)
- Auto-generated API documentation (Swagger)

---

## Tech Stack

- Python 3.10+
- FastAPI
- Uvicorn
- CSV file storage
- Swagger / OpenAPI

---

## Setup & Run

- git clone https://github.com/<your-username>/fastapi-transactions-api.git
- cd fastapi-transactions-api
- python -m venv venv
- venv\Scripts\activate      # Windows
- pip install -r requirements.txt
- python -m uvicorn main:app --reload --port 8001

## swagger UI
http://127.0.0.1:8001/docs