
# Penny Procurement Assistant

**An AI-powered Procurement Agent.**

_(Note: Please replace `assets/demo.gif` with your actual recording of the application)_

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

-   Python 3.9 or higher
    
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

Create a `.env` file in the root directory, or rename sample.env for convenience.

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

While NoSQL is often attractive for rapid prototyping, we deliberately chose a Relational Database Management System (RDBMS) for this use case:

1.  **Technical Debt & Structure:** Procurement data is inherently tabular and structured. Using NoSQL for highly structured data often leads to "loose" schemas that accumulate technical debt and data quality issues over time.
    
2.  **Schema Complexity:** A NoSQL approach like MongoDB would likely require significant denormalization. This complicates the aggregation pipeline, whereas SQL is purpose-built for the types of `JOIN`, `GROUP BY`, and `SUM` operations required for financial analytics.
    
3.  **LLM Accuracy:** Recent research (see [ArXiv:2411.05521](https://arxiv.org/abs/2411.05521 "null")) indicates that LLMs struggle significantly more with MongoDB Query Language (MQL) (approx. 21.55% zero-shot accuracy) compared to SQL (47.05%). The translation complexity for MQL is inherently higher due to the nested nature of JSON documents.
    
4.  **Performance:** For read-heavy analytical dashboards, a well-indexed PostgreSQL database offers superior latency and optimization compared to document stores, which is critical for a responsive chat interface.
    

### Why PydanticAI instead of LangChain?

We chose PydanticAI for its "close-to-the-metal" philosophy:

-   **Type Safety:** It leverages Python's native type hinting system, making the codebase easier to debug and maintain compared to LangChain's heavy abstractions.
    
-   **Structured Output:** PydanticAI excels at forcing LLMs to return valid JSON (e.g., our `SQLResponse` model). This significantly reduces the parser errors common in string-based chain libraries.
    
-   **Control Flow:** Instead of complex "Graphs" or "Chains," PydanticAI uses standard Python functions and loops, making the logic transparent.
    

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
