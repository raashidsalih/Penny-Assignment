
# Penny Procurement Assistant

**An AI-powered Procurement Agent.**

## Overview

**Penny Procurement Assistant** is an intelligent data assistant designed to democratize access to procurement data (namely, California procurement data). Instead of writing complex queries manually, users can ask natural language questions like _"How much did we spend with Ramsell in 2015?"_ or _"Show me the top 5 suppliers by transaction count."_

Penny translates these questions into MongoDB aggregation pipelines, fetches the data, and presents it in an interactive chat interface. It leverages **Google's Gemini** models via **PydanticAI** for high-speed, structured reasoning.

## Features

### Frontend

- **Interactive Chat Interface:** A familiar, ChatGPT-like experience with typing simulation.
- **Data Visualization:** Automatically renders query results into interactive tables.
- **Data Export:** Download full query results as CSV, Excel, or JSON.
- **Session Management:** Create, rename, delete, and switch between multiple chat history sessions.
- **Query Transparency:** "View Code" expanders allow technical users to inspect the generated MongoDB queries.
- **Connection Health:** Real-time indicator of database connectivity.

### Backend

- **Hybrid Intelligence:** Distinguishes between data requests (query generation) and general chatter (LLM knowledge) to save costs and reduce latency.
- **Schema-Aware Generation:** Dynamically injects database context and query rules into the prompt to ensure high accuracy.
- **Robust Error Handling:** Implements automatic retries for failed queries and safe fallbacks.
- **Connection Pooling:** Uses PyMongo's built-in connection pooling for efficient database access.
- **Persistent History:** Stores all conversations and metadata in MongoDB collections.

## Tech Stack

- **Language:** Python 3.10+
- **LLM Framework:** [PydanticAI](https://github.com/pydantic/pydantic-ai)
- **Model:** Google Gemini Flash (latest)
- **Database:** MongoDB
- **DB Driver:** PyMongo 4.6+
- **Frontend:** Streamlit
- **Configuration:** Pydantic Settings & Python-dotenv

## How to Run

### Prerequisites

- Python 3.10 or higher
- MongoDB installed and running locally (or MongoDB Atlas)

### 1. Clone and Configure

```bash
git clone https://github.com/your-username/penny-procurement.git
cd penny-procurement
```

### 2. Set up Virtual Environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start MongoDB

```bash
# macOS with Homebrew
brew services start mongodb-community

# Or run directly
mongod --dbpath /path/to/data/db
```

### 5. Environment Variables

Create a `.env` file in the root directory:

```env
# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=penny_db

# AI Configuration
GOOGLE_API_KEY=your_google_api_key_here

# Data Configuration
TABLE_NAME=california_procurement
INPUT_CSV_PATH=PURCHASE ORDER DATA EXTRACT 2012-2015_0.csv
CLEANED_CSV_OUTPUT=procurement_data_cleaned.csv
```

### 6. Load Data

Run the data loader script to populate MongoDB with the California procurement dataset:

```bash
python data_load.py
```

### 7. Launch the App

Start the Streamlit interface:

```bash
streamlit run streamlit_app_py.py
```

## Project Structure

```
penny-procurement/
├── config_py.py           # Application configuration (MongoDB settings)
├── database_py.py         # MongoDB connection and query execution
├── data_load.py           # CSV to MongoDB data loader
├── chat_manager_py.py     # Chat session management (MongoDB collections)
├── sql_agent_py.py        # PydanticAI agent for query generation
├── streamlit_app_py.py    # Streamlit frontend
├── system_prompt.txt      # AI system prompt template
├── table_schema.yaml      # Database schema definition
├── requirements.txt       # Python dependencies
└── .env                   # Environment variables
```

## Design Decisions

### Why PydanticAI instead of LangChain/LangGraph?

1. Pydantic is a leader in the space, offering production-ready solutions to major players.
2. The documentation tends to be more consistent, especially in contrast to LangChain's quick, sometimes breaking changes.
3. By focusing on structured JSON output and type-hinting, PydanticAI provides a more stable and predictable interface to the LLM.
4. The logic remains within standard Python functions and loops, making the control flow easy to debug and maintain.

### MongoDB Indexes

To improve data retrieval performance, especially for analytical queries involving filtering and grouping, MongoDB indexes are created on:
- `department_name` + `purchase_date` (compound)
- `supplier_name`
- `lpa_number`
- `acquisition_type`
- `fiscal_year`

### Connection Pooling

PyMongo's `MongoClient` maintains a connection pool by default, with configurable `minPoolSize` and `maxPoolSize` settings for efficient concurrent access.

## Other Considerations

### Why PostgreSQL over MongoDB (NoSQL)?

While NoSQL is often attractive for rapid prototyping, I advice for a SQL setup considering this use case:

1. Generally, NOSQL may be appealing when one is starting out, but the fast and loose nature of it, especially when the data could be structured otherwise, would lead to mounting technical debt over time.
2. Given the fixed schema of the dataset in question, using NOSQL is adding unneeded complexity. MongoDB would incur a denormalization penalty and the aggregation pipeline would be more sophisticated as a result.
3. Furthermore, according to [this paper](https://arxiv.org/abs/2411.05521), the translation complexity is inherently higher for MQL due to how unfamiliar the data on it is in contrast with SQL, contributing to the poor zero-shot accuracy (21.55%) compared to the latter (47.05%). Of course, this can be mitigated by employing some form of RAG for similar queries, but it just feels unnecessary.
4. Finally, for the typical read-heavy analytical use case like this one, NOSQL adds a potential latency hit compared to the well optimized SQL setup. This is also very important considering the chat interface, where quick responses are an expectation.

### Async Handling

1. This is to achieve responsiveness for concurrent users which requires non-blocking operations.
2. However, the Streamlit framework is not natively async. Therefore, a custom coroutine bridge is implemented to manually manage the asyncio event loop.
3. Most backend MongoDB elements aren't async due to the quick refactor from Postgres.

### Read-Only Database Access

For production deployments, consider creating a dedicated MongoDB user with read-only access to the procurement collection to prevent accidental or malicious data modifications.

### Consensus RAG Feature

To enhance query accuracy beyond basic schema injection:
1. Build a collection of user-approved "golden" queries
2. Use RAG to retrieve relevant, high-accuracy examples
3. Include these examples in the agent's prompt to guide generation

### Query Healing

If MongoDB returns an error, the agent can automatically retry with the error message fed back to the LLM for self-correction (configured via `MAX_QUERY_RETRIES`).

### Data Compliance

For sensitive data or enterprise deployments, consider on-premise LLM options to ensure proprietary data never leaves the controlled infrastructure.
