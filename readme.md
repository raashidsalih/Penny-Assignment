
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

1. Pydantic is a leader in the space, offering production ready solutioning to major players.
2. The documentation tends to be more consistent, especially in contrast to LangChain's quick, sometimes breaking changes.
3. By focusing on structured JSON output and type-hinting, PydanticAI provides a more stable and predictable interface to the LLM compared to chain-based systems.
4. The logic remains within standard Python functions and loops, making the control flow easy to debug and maintain.
    

### Async Handling

1. This is to achieve responsiveness for concurrent users which requires non-blocking operations. 
2. However, the Streamlit framework is not natively async. Therefore, I had to implement a custom coroutine bridge to manually manage the asyncio event loop.
    

### SQL Indexes

1. To further improve data retrieval performance, especially for analytical queries that involve filtering and grouping, SQL Indexes were defined.
2. These indexes are strategically applied to common analytical columns to ensure rapid query execution times.
    

### Connection Pooling

1. Inefficiencies are often caused by the overhead of opening and closing database connections on demand.
2. To mitigate this, I implemented Connection Pooling using the latest psycopg driver.
3. This keeps a set of database connections ready and reusable, significantly reducing latency for concurrent requests.
    

### SQL Injection Prevention
1. I prevent SQL Injection attacks by ensuring all user-provided values are handled as data, not as executable code.
2. This is achieved by using parameterized queries rather than directly injecting user input into the raw query string.

## Other Considerations

### Read-Only Database Access
1. To establish a hard security layer against potential issues or nefarious attacks (such as accidental or malicious UPDATE or DELETE commands), the LLM agent must use a dedicated database user.
2. This user should be configured at the database level with read-only access (typically CONNECT and SELECT privileges) to the procurement tables.

### Consensus RAG Feature
To enhance query accuracy beyond the basic schema injection, a Consensus RAG Feature can be considered. This involves:

1. Building a vector database of user-approved "golden" SQL queries.
2. Using RAG to retrieve these relevant, high-accuracy examples.
3. Including these examples in the agent's prompt to guide the LLM's generation, further improving accuracy.

### Query Healing
To improve the robustness of the agent, Query Healing can also be considered.

1. If the database returns an error upon executing the LLM-generated SQL, the agent will automatically pass the error message back to the LLM and prompt it to generate a fixed query.
2. This retry mechanism will be performed a fixed number of times to resolve potential LLM hallucinations or minor syntax errors automatically.

### Data Compliance
1. To fully address data governance for LLMs, especially for handling sensitive data or achieving specific certifications, the next steps must include figuring out enterprise solutions or on-premise LLM options.
2. This will allow Penny to manage the LLM processing environment and ensure the proprietary data never leaves the controlled, compliant infrastructure.
