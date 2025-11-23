# Penny Procurement Assistant

A comprehensive text-to-SQL chat application built with PydanticAI, PostgreSQL, and Streamlit. Ask natural language questions about California procurement data and get SQL-powered insights.

## 🌟 Features

### Backend (PydanticAI Agent)
- **Natural Language to SQL**: Powered by Google Gemini via PydanticAI
- **Intelligent Query Generation**: Context-aware SQL generation with schema understanding
- **Automatic Retry Logic**: Up to 3 automatic retries for failed queries with user feedback
- **Conversation Memory**: Maintains context across queries for better follow-up questions
- **Structured Responses**: Type-safe responses with Pydantic validation
- **Error Handling**: Comprehensive error handling with detailed user feedback

### Frontend (Streamlit)
- **Professional Chat Interface**: Clean, modern UI with chat-style interactions
- **Example Queries**: One-click example queries to get started
- **Session Management**: Create, rename, and delete chat sessions
- **SQL Transparency**: View generated SQL queries for any response
- **Results Visualization**: Interactive dataframes with download capability
- **Light/Dark Theme**: Automatic theme switching support
- **Real-time Processing**: Async query processing with loading indicators

### Database
- **PostgreSQL Backend**: Reliable data storage and query execution
- **Connection Pooling**: Efficient connection management with psycopg3
- **Chat Persistence**: Store all conversations in PostgreSQL
- **Schema-Aware**: Loads and understands table schema from YAML configuration

## 📋 Prerequisites

- Python 3.10 or higher
- PostgreSQL 12 or higher
- Google Gemini API key

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd procurement-sql-assistant
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the `.env.example` to `.env` and update with your credentials:

```bash
cp .env.example .env
```

Edit `.env` and set:
- `GOOGLE_API_KEY`: Your Google Gemini API key
- `DB_*`: Your PostgreSQL connection details

### 5. Set Up Database

#### Create Database
```bash
psql -U postgres
CREATE DATABASE penny_db;
\q
```

#### Load Your Data
If you have the California procurement CSV:
```bash
# Use your preferred method to load the CSV into the california_procurement table
# Example using psql:
psql -U postgres -d penny_db -c "\COPY california_procurement FROM 'your_data.csv' WITH CSV HEADER;"
```

### 6. Initialize Chat Tables
The application will automatically create the necessary chat management tables on first run:
- `chat_sessions`: Stores chat session metadata
- `chat_messages`: Stores individual messages

## 🎯 Usage

### Start the Application
```bash
streamlit run streamlit_app.py
```

The application will open in your default browser at `http://localhost:8501`

### Using the Interface

1. **Start with Examples**: Click any example query on the welcome screen
2. **Ask Questions**: Type natural language questions in the chat input
3. **View Results**: See SQL queries, explanations, and data results
4. **Download Data**: Export query results as CSV
5. **Manage Sessions**: Create new chats, rename, or delete from the sidebar

### Example Questions

- "What was the total procurement spending in fiscal year 2014-15?"
- "Show me the top 10 suppliers by total spending"
- "How many purchase orders were made using CalCard?"
- "What are the most purchased items by the Department of Transportation?"
- "Show procurement spending by acquisition type for 2013"

## 🏗️ Project Structure

```
procurement-sql-assistant/
├── .streamlit/
│   └── config.toml          # Streamlit theme configuration
├── config.py                 # Application configuration
├── database.py               # Database connection and query execution
├── sql_agent.py             # PydanticAI agent for SQL generation
├── chat_manager.py          # Chat session management
├── streamlit_app.py         # Streamlit frontend
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (create from .env.example)
├── table_schema.yaml        # Database schema definition
├── prompt.txt              # Base system prompt
└── README.md               # This file
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_USER` | PostgreSQL username | postgres |
| `DB_PASSWORD` | PostgreSQL password | postgres |
| `DB_HOST` | Database host | localhost |
| `DB_PORT` | Database port | 5432 |
| `DB_NAME` | Database name | penny_db |
| `TABLE_NAME` | Target table name | california_procurement |
| `GOOGLE_API_KEY` | Google Gemini API key | (required) |
| `GEMINI_MODEL` | Gemini model to use | gemini-2.0-flash |
| `MAX_QUERY_RETRIES` | Maximum retry attempts | 3 |
| `SESSION_TIMEOUT` | Session timeout (minutes) | 30 |
| `DEBUG_MODE` | Enable debug logging | False |

### Schema Configuration

The `table_schema.yaml` file defines your database schema. The agent uses this to:
- Understand available columns and their types
- Generate appropriate SQL queries
- Provide context-aware suggestions

## 🎨 Customization

### Changing Themes
Edit `.streamlit/config.toml` to customize colors and appearance for both light and dark modes.

### Adding Example Queries
Update the `EXAMPLE_QUERIES` variable in `.env` with pipe-separated queries.

### Modifying System Prompt
Edit `prompt.txt` or modify the `_build_system_prompt()` method in `sql_agent.py` to adjust agent behavior.

## 🐛 Troubleshooting

### Connection Issues
- Verify PostgreSQL is running: `pg_isready`
- Check database credentials in `.env`
- Ensure database exists and is accessible

### API Issues
- Verify `GOOGLE_API_KEY` is set correctly
- Check API quota and limits
- Enable debug mode for detailed logs

### Query Failures
- Review generated SQL in the expander
- Check table schema matches actual database
- Verify data types in `table_schema.yaml`

## 📦 Dependencies

### Core Packages
- **pydantic-ai** (0.0.16): AI agent framework
- **pydantic** (2.10.4): Data validation
- **google-generativeai** (0.8.3): Gemini API client
- **psycopg** (3.2.3): PostgreSQL adapter
- **streamlit** (1.41.1): Web interface
- **python-dotenv** (1.0.1): Environment management
- **pyyaml** (6.0.2): YAML parsing

## 🔐 Security Notes

- Never commit `.env` file with real credentials
- Use environment variables for sensitive data
- Implement proper authentication for production deployments
- Sanitize user inputs (handled by psycopg parameterized queries)
- Limit database user permissions to necessary operations

## 🚧 Future Enhancements

- [ ] Support for multiple tables and joins
- [ ] Query result caching
- [ ] Export to multiple formats (Excel, JSON)
- [ ] Advanced visualization options
- [ ] Query history analytics
- [ ] Multi-user authentication
- [ ] Query templates and saved queries

## 📝 License

This project is provided as-is for educational and commercial use.

For issues and questions:
1. Check this README
2. Review error messages in debug mode
3. Check the logs
4. Contact the administrator
