
# Penny Procurement Assistant

**An AI-powered Procurement Agent.**

![main screen](https://github.com/raashidsalih/Penny-Assignment/blob/main/assets/main_screen.png)

## Overview

**Penny Procurement Assistant** is an intelligent data assistant designed to democratize access to procurement data (namely, California procurement data). Instead of writing complex SQL queries manually, users can ask natural language questions like _"How much did we spend with Ramsell in 2015?"_ or _"Show me the top 5 suppliers by transaction count."_

Penny translates these questions into safe, executable PostgreSQL queries, fetches the data, and presents it in an interactive chat interface. It leverages **Google's Gemini** models via **PydanticAI** for high-speed, structured reasoning.

## Features

### Frontend

-   **Interactive Chat Interface:** A familiar, ChatGPT-like experience with typing simulation.
    
-   **Data Visualization:** Automatically renders SQL results into interactive tables.
    
-   **Data Export:** Download full query results for offline analysis.
    
-   **Session Management:** Create, rename, delete, and switch between multiple chat history sessions.
    
-   **SQL Transparency:** "View Code" expanders allow technical users to inspect the generated SQL for verification.
    
-   **Connection Health:** Real-time indicator of database connectivity.
    

### Backend

-   **Hybrid Intelligence:** Distinguishes between data requests (SQL generation) and general chatter (LLM knowledge) to save costs and reduce latency.
    
-   **Schema-Aware Generation:** dynamically injects database context and "cheat sheet" rules into the prompt to ensure high accuracy.
    
-   **Robust Error Handling:** Implements automatic retries for failed queries and safe fallbacks.
    
-   **Connection Pooling:** Uses `psycopg_pool` to handle concurrent database requests efficiently.
    
-   **Persistent History:** Stores all conversations and metadata in a structured PostgreSQL schema.
    

## Tech Stack

-   **Language:** Python 3.10+
    
-   **LLM Framework:** [PydanticAI](https://github.com/pydantic/pydantic-ai "null")
    
-   **Model:** Google Gemini Flash (latest)
    
-   **Database:** PostgreSQL
    
-   **DB Driver:** `psycopg` (v3) with Connection Pooling
    
-   **Frontend:** Streamlit
    
-   **Configuration:** Pydantic Settings & Python-dotenv
    

## How to Run

### Prerequisites

-   Python 3.10 or higher
    
-   PostgreSQL installed and running locally or in the cloud.
    

### 1. Clone and Configure

```
git clone [https://github.com/your-username/penny-procurement.git](https://github.com/your-username/penny-procurement.git)
cd penny-procurement

```

### 2. Set up Virtual Environment

```
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

```

### 3. Install Dependencies

```
pip install -r requirements.txt

```

### 4. Environment Variables

Create a `.env` file in the root directory, or rename sample.env for convenience. Ensure you update GOOGLE_API_KEY for the model and INPUT_CSV_PATH for the California procurement data CSV source.

### 5. Load Data

Run the data loader script to populate your PostgreSQL database with the California procurement dataset.

```
python data_load.py

```

### 6. Launch the App

Start the Streamlit interface:

```
streamlit run streamlit_app_py.py

```

## Design Decisions

### Why PostgreSQL over MongoDB (NoSQL)?

While NoSQL is often attractive for rapid prototyping, I deliberately chose a SQL setup for this use case:

1. Generally, NOSQL may be appealing when one is starting out, but the fast and loose nature of it, especially when the data could be structured otherwise, would lead to mounting technical debt over time.
2. Given the fixed schema of the dataset in question, using NOSQL is adding unneeded complexity. MongoDB would incur a denormalization penalty and the aggregation pipeline would be more sophisticated as a result.
3. Furthermore, according to [this paper](https://arxiv.org/abs/2411.05521), the translation complexity is inherently higher for MQL due to how unfamiliar the data on it is in contrast with SQL, contributing to the poor zero-shot accuracy (21.55%) compared to the latter (47.05%). Of course, this can be mitigated by employing some form of RAG for similar queries, but it just feels unnecessary.
4. Finally, for the typical read-heavy analytical use case like this one, NOSQL adds a potential latency hit compared to the well optimized SQL setup. This is also very important considering the chat interface, where quick responses are an expectation.
    

### Why PydanticAI instead of LangChain/LangGraph?

I chose PydanticAI for its "close-to-the-metal" philosophy:
    

### Async Handling in Streamlit

Streamlit is fundamentally synchronous, while high-performance AI agents are asynchronous.

-   **The Constraint:** Running `async` code directly in Streamlit often leads to event loop conflicts.
    
-   **The Solution:** We implemented a custom `run_async` bridge that manages the `asyncio` event loop manually. This allows us to keep the frontend simple while leveraging the non-blocking performance of PydanticAI in the backend.
    

### Security: Read-Only Database Access

To prevent the Agent from accidentally (or maliciously) altering data:

-   The database user credentials provided to the `SQLAgent` should be restricted at the PostgreSQL level.
    
-   **Policy:** The user typically has `CONNECT` and `SELECT` privileges only. Commands like `DROP`, `DELETE`, or `INSERT` will be rejected by the database engine itself, providing a hard security layer beyond prompt engineering.
    

### Security: SQL Injection Prevention

-   **Chat History:** Interactions with the application database (storing chat logs) utilize `psycopg`'s parameterized queries (e.g., `VALUES (%s, %s)`). This ensures user input is treated strictly as data, not executable code.
    
-   **Generated SQL:** While the LLM generates the SQL, we validate the syntax and rely on the Read-Only database permissions to prevent destructive injection attacks.
    

### Data Compliance & Privacy

To ensure data sovereignty and prevent leakage:

-   **Schema-Only Transmission:** The LLM is **never** fed the actual rows of data in the prompt. It only receives the `table_schema.yaml` (column names and types). The actual financial data remains in your private PostgreSQL instance.
    
-   **Result Filtering:** Data is queried locally. The LLM only sees the _results_ if a summary is requested, minimizing the data footprint sent to external APIs
