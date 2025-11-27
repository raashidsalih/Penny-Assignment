"""Streamlit frontend for text-to-SQL chat interface - Enhanced Version."""

import streamlit as st
import pandas as pd
import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import json

from config_py import config
from sql_agent_py import sql_agent as global_sql_agent
from chat_manager_py import chat_manager as global_chat_manager
from database_py import db_manager as global_db_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO if config.DEBUG_MODE else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
MAX_HISTORY_MESSAGES = 20
MAX_DISPLAY_ROWS = 50
QUICK_ACTIONS = [
    {"icon": "📈", "text": "Show trends", "query": "Show me spending trends over time"},
    {"icon": "🏢", "text": "Top vendors", "query": "Who are the top 10 vendors by total spending?"},
    {"icon": "💰", "text": "Largest contracts", "query": "What are the largest contracts this year?"},
    {"icon": "📊", "text": "Department breakdown", "query": "Break down spending by department"},
]

# Page Configuration
st.set_page_config(
    page_title="Penny Procurement Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced Styling
st.markdown("""
<style>
    /* Main chat styling */
    .stChatMessage { 
        padding: 1rem; 
        border-radius: 0.5rem; 
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* Welcome screen */
    .welcome-container { 
        text-align: center; 
        padding: 3rem 2rem;
        max-width: 800px;
        margin: 0 auto;
    }
    .welcome-title { 
        font-size: 2.5rem; 
        font-weight: bold; 
        margin-bottom: 0.5rem;
        color: #1e88e5;
    }
    .welcome-subtitle { 
        font-size: 1.2rem; 
        color: #666; 
        margin-bottom: 2rem;
        line-height: 1.6;
    }
    .feature-box {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #1e88e5;
        color: #333;
    }
    
    /* Example queries */
    .example-query {
        transition: all 0.2s ease;
    }
    .example-query:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* SQL query display */
    .sql-container {
        background: #f5f5f5;
        border-left: 3px solid #1e88e5;
        padding: 1rem;
        border-radius: 0.25rem;
    }
    
    /* Stats badges */
    .stat-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.85rem;
        margin: 0.25rem;
    }
    .stat-success { background: #e8f5e9; color: #2e7d32; }
    .stat-warning { background: #fff3e0; color: #f57c00; }
    .stat-info { background: #e3f2fd; color: #1976d2; }
    
    /* Sidebar improvements */
    .sidebar .element-container { margin-bottom: 0.5rem; }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Tooltip styling */
    .tooltip {
        position: relative;
        display: inline-block;
        cursor: help;
    }
    
    /* Empty state styling */
    .empty-state {
        text-align: center;
        padding: 3rem;
        color: #666;
    }
    
    /* Progress indicators */
    .query-stage {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem;
        background: #f0f7ff;
        border-radius: 0.25rem;
        margin: 0.5rem 0;
        font-size: 0.9rem;
        color: #333;
    }
    
    /* Result summary cards */
    .result-summary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Cached Resources
@st.cache_resource
def get_managers():
    """Initialize and cache manager instances."""
    return global_db_manager, global_chat_manager, global_sql_agent

db_manager, chat_manager, sql_agent = get_managers()

# Async Helper
def run_async(coro):
    """
    Run async coroutine properly in Streamlit.
    Note: This still blocks, but Streamlit isn't truly async-native.
    For production, consider using asyncio.run() or proper async framework.
    """
    try:
        # Try to get existing loop
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            # Create new loop if closed
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        # No loop exists, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Run the coroutine
    try:
        return loop.run_until_complete(coro)
    except RuntimeError as e:
        # If we still get "Event loop is closed", create fresh loop
        logger.warning(f"Loop closed error, creating new loop: {e}")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

# UI Helpers
def format_session_title(session_name: str, message_count: int, is_current: bool) -> str:
    """Format session title with metadata."""
    icon = "💬" if message_count > 0 else "📝"
    badge = " 🔵" if is_current else ""
    msg_text = f" ({message_count})" if message_count > 0 else " (empty)"
    return f"{icon} {session_name}{msg_text}{badge}"

def render_stat_badge(label: str, value: str, badge_type: str = "info") -> str:
    """Generate HTML for stat badge."""
    return f'<span class="stat-badge stat-{badge_type}">{label}: {value}</span>'

def generate_data_insights(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate automatic insights from query results."""
    insights = {
        'has_insights': False,
        'insights': [],
        'numeric_cols': []
    }
    
    # Find numeric columns
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
    insights['numeric_cols'] = numeric_cols
    
    if not numeric_cols:
        return insights
    
    insights['has_insights'] = True
    
    # Summary statistics
    for col in numeric_cols[:3]:  # Limit to first 3 numeric columns
        col_sum = df[col].sum()
        col_mean = df[col].mean()
        col_max = df[col].max()
        col_min = df[col].min()
        
        if col_sum > 0:
            insights['insights'].append(
                f"**{col}**: Total = {col_sum:,.2f}, Average = {col_mean:,.2f}, Range = {col_min:,.2f} to {col_max:,.2f}"
            )
    
    # Check for date columns
    date_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
    if date_cols:
        for col in date_cols[:2]:
            min_date = df[col].min()
            max_date = df[col].max()
            insights['insights'].append(
                f"**{col}**: From {min_date} to {max_date}"
            )
    
    return insights

def analyze_sql_query(sql_query: str) -> Dict[str, Any]:
    """Analyze SQL query and extract metadata."""
    upper_query = sql_query.upper()
    
    # Determine query type
    if upper_query.strip().startswith('SELECT'):
        query_type = 'SELECT'
    elif upper_query.strip().startswith('INSERT'):
        query_type = 'INSERT'
    elif upper_query.strip().startswith('UPDATE'):
        query_type = 'UPDATE'
    elif upper_query.strip().startswith('DELETE'):
        query_type = 'DELETE'
    else:
        query_type = 'OTHER'
    
    # Count tables (rough estimate)
    table_count = upper_query.count('FROM') + upper_query.count('JOIN')
    
    # Line count
    lines = len(sql_query.split('\n'))
    
    return {
        'type': query_type,
        'table_count': table_count,
        'lines': lines
    }

def render_results_table(results: list, unique_key: str, sql_query: Optional[str] = None):
    """Render data results with enhanced UI and insights."""
    if not results:
        st.info("🔍 Query executed successfully but returned no results.")
        return

    df = pd.DataFrame(results)
    total_rows = len(df)
    
    # Generate quick insights
    insights = generate_data_insights(df)
    
    # Stats row with visual cards
    st.markdown('<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 0.5rem; color: white; margin: 1rem 0;">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📊 Total Rows", f"{total_rows:,}")
    with col2:
        st.metric("📋 Columns", len(df.columns))
    with col3:
        if insights['numeric_cols']:
            st.metric("🔢 Numeric Fields", len(insights['numeric_cols']))
        else:
            st.metric("📝 Data Type", "Text/Mixed")
    with col4:
        memory_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
        st.metric("💾 Size", f"{memory_mb:.2f} MB")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Quick insights
    if insights['has_insights']:
        with st.expander("💡 Quick Insights", expanded=False):
            for insight in insights['insights']:
                st.markdown(f"- {insight}")
    
    # Action buttons
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        csv = df.to_csv(index=False)
        st.download_button(
            label=f"📥 Download CSV",
            data=csv,
            file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            key=f"dl_csv_{unique_key}",
            width='stretch'
        )
    with col2:
        # Excel download
        try:
            from io import BytesIO
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Query Results')
            st.download_button(
                label="📊 Download Excel",
                data=buffer.getvalue(),
                file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"dl_xlsx_{unique_key}",
                width='stretch'
            )
        except ImportError:
            st.button("📊 Excel (Install openpyxl)", disabled=True, width='stretch', key=f"no_excel_{unique_key}")
    with col3:
        # JSON download
        json_str = df.to_json(orient='records', indent=2)
        st.download_button(
            label="📋 Download JSON",
            data=json_str,
            file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            key=f"dl_json_{unique_key}",
            width='stretch'
        )
    
    # Data preview with column info
    with st.expander("📊 View Data", expanded=True):
        # Column type summary
        col_info = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            null_count = df[col].isnull().sum()
            col_info.append(f"**{col}** ({dtype}) - {null_count} nulls" if null_count > 0 else f"**{col}** ({dtype})")
        
        with st.expander("ℹ️ Column Information", expanded=False):
            st.markdown(" | ".join(col_info[:5]))
            if len(col_info) > 5:
                st.markdown(f"...and {len(col_info) - 5} more columns")
        
        if total_rows > MAX_DISPLAY_ROWS:
            st.warning(f"⚠️ Showing first {MAX_DISPLAY_ROWS} of {total_rows:,} rows. Download for complete data.")
            st.dataframe(df.head(MAX_DISPLAY_ROWS), width='stretch', height=400)
        else:
            st.dataframe(df, width='stretch', height=min(400, total_rows * 35 + 50))
        
        # Quick filters (if reasonable size)
        if total_rows <= 10000 and len(df.columns) > 0:
            st.markdown("---")
            st.markdown("**🔍 Quick Filters** (applies to view only)")
            filter_col = st.selectbox("Filter by column:", ["None"] + list(df.columns), key=f"filter_{unique_key}")
            if filter_col != "None":
                unique_vals = df[filter_col].unique()
                if len(unique_vals) <= 50:
                    selected_val = st.selectbox(f"Show rows where {filter_col} =", unique_vals, key=f"filter_val_{unique_key}")
                    filtered_df = df[df[filter_col] == selected_val]
                    st.dataframe(filtered_df, width='stretch')
                else:
                    st.info(f"Too many unique values ({len(unique_vals)}) for quick filtering.")

def render_sql_query(sql_query: str, unique_key: str):
    """Render SQL query with advanced options."""
    with st.expander("🔍 SQL Query", expanded=False):
        # Query stats
        query_stats = analyze_sql_query(sql_query)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption(f"**Type:** {query_stats['type']}")
        with col2:
            st.caption(f"**Tables:** {query_stats['table_count']}")
        with col3:
            st.caption(f"**Lines:** {query_stats['lines']}")
        
        # Main query display
        st.code(sql_query, language='sql', line_numbers=True)
        
        # Action buttons
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            if st.button("📋 Copy", key=f"copy_{unique_key}", width='stretch'):
                st.toast("SQL copied to clipboard!", icon="✅")
                # Note: Actual clipboard copy requires JavaScript
        with col_b:
            if st.button("📝 Explain Query", key=f"explain_{unique_key}", width='stretch'):
                st.info("Ask me: 'Can you explain this SQL query?' to get a breakdown!")
        with col_c:
            if st.button("🔧 Modify Query", key=f"modify_{unique_key}", width='stretch'):
                st.info("Ask me: 'Can you modify the query to...' with your changes!")

def initialize_session_state():
    """Initialize Streamlit session state with defaults."""
    if 'current_session_id' not in st.session_state:
        session_id = chat_manager.create_session()
        st.session_state.current_session_id = session_id
    
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    
    if 'feedback_given' not in st.session_state:
        st.session_state.feedback_given = set()
    
    if 'toast_message' not in st.session_state:
        st.session_state.toast_message = None

def load_session(session_id: int):
    """Load a chat session with error handling."""
    try:
        st.session_state.current_session_id = session_id
        all_messages = chat_manager.get_session_messages(session_id)
        recent_messages = all_messages[-MAX_HISTORY_MESSAGES:]
        
        st.session_state.messages = []
        
        if len(all_messages) > MAX_HISTORY_MESSAGES:
            st.toast(f"📚 Loaded last {MAX_HISTORY_MESSAGES} of {len(all_messages)} messages", icon="ℹ️")

        for msg in recent_messages:
            st.session_state.messages.append({
                'role': msg['role'],
                'content': msg['content'],
                'metadata': msg.get('metadata', {})
            })
        
        st.rerun()
    except Exception as e:
        logger.error(f"Error loading session {session_id}: {e}")
        st.error(f"Failed to load session: {str(e)}")

def export_chat_history():
    """Export current chat history as JSON."""
    if not st.session_state.messages:
        st.warning("No messages to export!")
        return
    
    export_data = {
        'session_id': st.session_state.current_session_id,
        'exported_at': datetime.now().isoformat(),
        'message_count': len(st.session_state.messages),
        'messages': st.session_state.messages
    }
    
    json_str = json.dumps(export_data, indent=2, default=str)
    st.download_button(
        label="📥 Download Chat JSON",
        data=json_str,
        file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        key="export_chat"
    )

def display_welcome_screen():
    """Display enhanced welcome screen with features and examples."""
    # Custom title with icon
    st.markdown("""
    <div class="welcome-container">
        <div class="welcome-title">📊 Penny Procurement Assistant</div>
        <div class="welcome-subtitle">
            Your AI-powered assistant for exploring California procurement data.<br>
            Ask questions in natural language and get instant SQL-powered insights.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick action chips
    st.markdown("### ⚡ Quick Actions")
    cols = st.columns(len(QUICK_ACTIONS))
    for idx, action in enumerate(QUICK_ACTIONS):
        with cols[idx]:
            if st.button(
                f"{action['icon']} {action['text']}", 
                key=f"quick_{idx}",
                width='stretch'
            ):
                st.session_state.trigger_query = action['query']
                st.rerun()
    
    st.markdown("---")
    
    # Features
    st.markdown("### ✨ What you can do:")
    cols = st.columns(3)
    with cols[0]:
        st.markdown("""
        <div class="feature-box">
            <strong>🔍 Natural Language Queries</strong><br>
            Ask questions in plain English
        </div>
        """, unsafe_allow_html=True)
    with cols[1]:
        st.markdown("""
        <div class="feature-box">
            <strong>📊 Instant Results</strong><br>
            Get data visualized and ready to download
        </div>
        """, unsafe_allow_html=True)
    with cols[2]:
        st.markdown("""
        <div class="feature-box">
            <strong>💬 Conversational</strong><br>
            Follow-up questions and refinements
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("### 💡 Example questions:")
    
    # Example queries in a grid
    cols = st.columns(2)
    for idx, example in enumerate(config.EXAMPLE_QUERIES[:6]):  # Limit to 6
        col = cols[idx % 2]
        with col:
            if st.button(
                example, 
                key=f"example_{idx}", 
                width='stretch',
                type="secondary"
            ):
                st.session_state.trigger_query = example
                st.rerun()
    
    # Tips section
    with st.expander("💡 Tips for better results", expanded=False):
        st.markdown("""
        - **Be specific**: Instead of "show me data", try "show me top 10 vendors by spending"
        - **Ask follow-ups**: "Can you break that down by month?" or "Show only 2024 data"
        - **Request formats**: "Give me a summary" or "Show as a table"
        - **Check the SQL**: Review generated queries to understand how data is retrieved
        - **Download results**: Export to CSV, Excel, or JSON for further analysis
        """)

def display_message(idx: int, message: Dict[str, Any]):
    """Display a single message with enhanced formatting."""
    role = message['role']
    content = message['content']
    metadata = message.get('metadata', {})
    
    with st.chat_message(role):
        # Main content
        st.markdown(content)
        
        # Assistant-specific metadata
        if role == 'assistant':
            success = metadata.get('success', True)
            sql_query = metadata.get('sql_query')
            results = metadata.get('results', [])
            confidence = metadata.get('confidence', 'medium')
            
            # Show badges for SQL queries
            if sql_query and success:
                badges_html = ""
                badges_html += render_stat_badge("Confidence", confidence.title(), 
                    "success" if confidence == "high" else "warning")
                if results:
                    badges_html += render_stat_badge("Rows", f"{len(results):,}", "info")
                st.markdown(badges_html, unsafe_allow_html=True)
                
                # Feedback buttons for SQL queries
                feedback_key = f"feedback_{idx}"
                col1, col2, col3 = st.columns([1, 1, 10])
                
                with col1:
                    thumbs_up_key = f"thumbs_up_{idx}"
                    if st.button("👍", key=thumbs_up_key, help="Good query"):
                        st.session_state.feedback_given.add(feedback_key)
                        st.session_state.toast_message = ("✅", "Thanks for your feedback!")
                        st.rerun()
                
                with col2:
                    thumbs_down_key = f"thumbs_down_{idx}"
                    if st.button("👎", key=thumbs_down_key, help="Needs improvement"):
                        st.session_state.feedback_given.add(feedback_key)
                        st.session_state.toast_message = ("📝", "Feedback recorded. We'll improve!")
                        st.rerun()
                
                with col3:
                    if feedback_key in st.session_state.feedback_given:
                        st.caption("✓ Feedback received")
            
            # Non-SQL responses
            if not sql_query and not results:
                st.caption("✨ *AI-generated response*")
            
            # SQL query display
            if sql_query:
                render_sql_query(sql_query, f"hist_{idx}")
            
            # Results table
            if results:
                render_results_table(results, f"hist_{idx}", sql_query)

async def process_user_query(user_question: str) -> Dict[str, Any]:
    """Process user query with error handling."""
    try:
        context = chat_manager.get_conversation_context(
            st.session_state.current_session_id,
            last_n=5
        )
        result = await sql_agent.process_question(user_question, context)
        return result
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        return {
            'success': False,
            'error': f"Failed to process query: {str(e)}",
            'sql_query': None,
            'results': []
        }

def handle_user_input(user_question: str):
    """Handle user input with improved UX and error handling."""
    if st.session_state.processing:
        st.warning("⏳ Please wait for the current query to complete.")
        return
    
    st.session_state.processing = True
    
    try:
        # 1. Add and display user message
        user_msg = {'role': 'user', 'content': user_question, 'metadata': {}}
        st.session_state.messages.append(user_msg)
        chat_manager.add_message(st.session_state.current_session_id, 'user', user_question)
        
        with st.chat_message("user"):
            st.markdown(user_question)
        
        # 2. Process and display assistant response
        with st.chat_message("assistant"):
            # Multi-stage progress indicator
            progress_container = st.empty()
            
            stages = [
                ("🤔", "Understanding your question..."),
                ("🔍", "Analyzing data requirements..."),
                ("⚡", "Processing..."),
                ("📊", "Preparing response...")
            ]
            
            for stage_icon, stage_text in stages[:2]:  # Show first 2 stages
                progress_container.markdown(f'<div class="query-stage">{stage_icon} {stage_text}</div>', unsafe_allow_html=True)
                time.sleep(0.3)
            
            result = run_async(process_user_query(user_question))
            
            progress_container.empty()  # Clear progress
            
            sql_query = result.get('sql_query')
            success = result.get('success', False)
            
            # Generate response text
            if success:
                explanation = result.get('explanation', 'Here are the results.')
                
                if sql_query:
                    rows = len(result.get('results', []))
                    confidence = result.get('confidence', 'medium')
                    retries = result.get('retry_attempts', 1)
                    
                    footer_parts = [f"*Retrieved {rows:,} rows*"]
                    if retries > 1:
                        footer_parts.append(f"*{retries} attempts*")
                    
                    full_response = f"{explanation}\n\n{' • '.join(footer_parts)}"
                else:
                    full_response = explanation
                    st.caption("🤖 *Conversational response (no database query needed)*")
            else:
                error_msg = result.get('error', 'An unexpected error occurred.')
                full_response = f"❌ **Unable to process your request**\n\n{error_msg}"
                st.error("The query could not be completed. Please try rephrasing or check the error details.")
            
            # Display response
            st.markdown(full_response)
            
            # Show SQL and results
            metadata = {
                'sql_query': sql_query,
                'results': result.get('results', []),
                'confidence': result.get('confidence', 'medium'),
                'success': success
            }
            
            if sql_query:
                render_sql_query(sql_query, "current")
            
            if success and metadata['results']:
                render_results_table(metadata['results'], "current", sql_query)
        
        # 3. Save assistant message
        assistant_msg = {
            'role': 'assistant',
            'content': full_response,
            'metadata': metadata
        }
        st.session_state.messages.append(assistant_msg)
        chat_manager.add_message(
            st.session_state.current_session_id,
            'assistant',
            full_response,
            metadata
        )
        
    except Exception as e:
        logger.error(f"Error handling user input: {e}", exc_info=True)
        st.error(f"An unexpected error occurred: {str(e)}")
    finally:
        st.session_state.processing = False
        st.rerun()

def sidebar_chat_management():
    """Enhanced sidebar with better session management."""
    with st.sidebar:
        st.title("💬 Chat Sessions")
        
        # New chat button
        if st.button("➕ New Chat", width='stretch', type="primary"):
            session_id = chat_manager.create_session()
            load_session(session_id)
        
        st.divider()
        
        # Sessions list
        sessions = chat_manager.get_all_sessions()
        
        if sessions:
            st.markdown("### Recent Chats")
            
            for session in sessions:
                s_id = session['session_id']
                s_name = session['session_name']
                is_current = s_id == st.session_state.current_session_id
                
                # Get message count
                messages = chat_manager.get_session_messages(s_id)
                msg_count = len(messages)
                
                # Session container - cleaner stacked layout
                with st.container():
                    # Main session button
                    button_label = format_session_title(s_name, msg_count, is_current)
                    if st.button(
                        button_label,
                        key=f"load_{s_id}",
                        disabled=is_current,
                        width='stretch',
                        type="primary" if is_current else "secondary"
                    ):
                        load_session(s_id)
                    
                    # Action buttons in a clean row - only show if not renaming
                    if not (hasattr(st.session_state, 'renaming') and st.session_state.renaming == s_id):
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✏️ Rename", key=f"ren_{s_id}", width='stretch', type="secondary"):
                                st.session_state.renaming = s_id
                                st.rerun()
                        with col2:
                            if not is_current:
                                if st.button("🗑️ Delete", key=f"del_{s_id}", width='stretch', type="secondary"):
                                    chat_manager.delete_session(s_id)
                                    st.session_state.toast_message = ("✅", "Session deleted")
                                    st.rerun()
                    
                    # Inline rename UI
                    if hasattr(st.session_state, 'renaming') and st.session_state.renaming == s_id:
                        st.markdown("**Rename Session:**")
                        new_name = st.text_input(
                            "New name:",
                            value=s_name,
                            key=f"new_name_{s_id}",
                            label_visibility="collapsed",
                            placeholder="Enter new session name..."
                        )
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("✅ Save", key=f"save_{s_id}", width='stretch', type="primary"):
                                if new_name.strip():
                                    chat_manager.rename_session(s_id, new_name.strip())
                                    del st.session_state.renaming
                                    st.session_state.toast_message = ("✅", "Session renamed")
                                    st.rerun()
                        with col_b:
                            if st.button("❌ Cancel", key=f"cancel_{s_id}", width='stretch', type="secondary"):
                                del st.session_state.renaming
                                st.rerun()
                    
                    # Spacing between sessions
                    st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)
        else:
            st.info("No chat sessions yet. Start a new chat!")
        
        st.divider()
        
        # Settings & Status
        with st.expander("⚙️ Settings & Status", expanded=False):
            st.markdown(f"**Model:** `{config.GEMINI_MODEL}`")
            
            # Database status
            if db_manager.test_connection():
                st.success("✅ Database Connected")
            else:
                st.error("❌ Database Disconnected")
            
            # Session info
            if st.session_state.messages:
                st.info(f"💬 {len(st.session_state.messages)} messages in current chat")

def main():
    """Main application loop."""
    initialize_session_state()
    
    # Show persistent toast messages FIRST before any other UI
    if st.session_state.toast_message:
        icon, message = st.session_state.toast_message
        st.toast(message, icon=icon)
        st.session_state.toast_message = None
    
    sidebar_chat_management()
    
    # Show welcome screen only if truly empty
    if not st.session_state.messages:
        display_welcome_screen()
    else:
        # Display message history - use container to prevent auto-scroll
        for idx, message in enumerate(st.session_state.messages):
            display_message(idx, message)
    
    # Handle triggered query from example
    if hasattr(st.session_state, 'trigger_query'):
        query = st.session_state.trigger_query
        del st.session_state.trigger_query
        handle_user_input(query)
        return  # Prevent double input
    
    # Chat input
    if prompt := st.chat_input(
        "Ask a question about procurement data...",
        disabled=st.session_state.processing
    ):
        handle_user_input(prompt)

if __name__ == "__main__":
    try:
        config.validate()
        main()
    except Exception as e:
        st.error(f"❌ Application Error: {str(e)}")
        logger.error(f"Fatal application error: {e}", exc_info=True)
        if config.DEBUG_MODE:
            st.exception(e)
