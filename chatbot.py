import streamlit as st
import sqlite3
from datetime import date, datetime
import plotly.express as px
import html
import streamlit.components.v1 as components
import pandas as pd
import re

from langchain_core.messages import HumanMessage

from multiagent import app as chatbot_responder

from utils.db_utils import *



# Set page config for wide layout
st.set_page_config(page_title="Personal Expense Tracker", layout="wide", page_icon="💸")

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'user' not in st.session_state:
    st.session_state.user = None
if 'show_success' not in st.session_state:
    st.session_state.show_success = False
if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = [
        {"sender": "system", "message": "Hello! I'm your expense tracking assistant. How can I help you today?"}
    ]

# Initialize database
init_db()

# Custom CSS for better styling
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Main app title
st.markdown('<h1 class="main-header">💸 Personal Expense Tracker</h1>', unsafe_allow_html=True)

# LOGIN PAGE
if st.session_state.page == 'login':
    st.markdown('<div class="form-header"><h2>Login to Your Account</h2><p>Welcome back! Please sign in to continue</p></div>', unsafe_allow_html=True)
    
    with st.form("login_form", clear_on_submit=True):
        email = st.text_input("📧 Email Address", placeholder="Enter your email")
        password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
        
        col1, col2 = st.columns(2)
        with col1:
            login_button = st.form_submit_button("🚀 Login", use_container_width=True)
        with col2:
            register_button = st.form_submit_button("📝 Register", use_container_width=True)
    
    if login_button:
        if email and password:
            user = authenticate_user(email, password)
            if user:
                st.session_state.user = {
                    'user_id': user[0],
                    'first_name': user[1],
                    'last_name': user[2],
                    'email': email
                }
                st.session_state.page = 'dashboard'
                st.rerun()
            else:
                st.markdown('<div class="error-message">❌ Invalid email or password. Please try again.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="error-message">⚠️ Please fill in all fields.</div>', unsafe_allow_html=True)
    
    if register_button:
        st.session_state.page = 'register'
        st.rerun()

# REGISTER PAGE
elif st.session_state.page == 'register':
    st.markdown('<div class="form-header"><h2>Create Your Account</h2><p>Join us to start tracking your expenses</p></div>', unsafe_allow_html=True)
    
    with st.form("register_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("👤 First Name", placeholder="Enter first name")
        with col2:
            last_name = st.text_input("👤 Last Name", placeholder="Enter last name")
        
        email = st.text_input("📧 Email Address", placeholder="Enter your email")
        password = st.text_input("🔒 Password", type="password", placeholder="Create a password")
        
        col1, col2 = st.columns(2)
        with col1:
            register_submit = st.form_submit_button("✅ Create Account", use_container_width=True)
        with col2:
            back_to_login = st.form_submit_button("⬅️ Back to Login", use_container_width=True)
    
    if register_submit:
        if first_name and last_name and email and password:
            if register_user(first_name, last_name, email, password):
                st.markdown('<div class="success-message">🎉 Registration successful! You can now login with your credentials.</div>', unsafe_allow_html=True)
                st.balloons()
                
                # Auto redirect to login after 2 seconds
                st.markdown("Redirecting to login page...")
                st.session_state.page = 'login'
                st.rerun()
            else:
                st.markdown('<div class="error-message">❌ Email already exists. Please use a different email address.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="error-message">⚠️ Please fill in all fields.</div>', unsafe_allow_html=True)
    
    if back_to_login:
        st.session_state.page = 'login'
        st.rerun()

# DASHBOARD PAGE
elif st.session_state.page == 'dashboard' and st.session_state.user:
    # Get current date and day
    current_date = datetime.now()
    day_name = current_date.strftime("%A")
    formatted_date = current_date.strftime("%B %d, %Y")
    
    # Header with welcome message and logout
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f'<div class="welcome-header"><h2>Welcome back, {st.session_state.user["first_name"]}! 👋</h2><p>Today is {day_name}, {formatted_date}</p><p>Ready to track your expenses?</p></div>', unsafe_allow_html=True)
    with col2:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user = None
            st.session_state.page = 'login'
            st.rerun()

    # Main layout - Two columns
    left_col, right_col = st.columns([1, 1])
    
    # LEFT COLUMN
    with left_col:
        # Financial Snapshot Section
        st.markdown("## 📊 Financial Snapshot")
        
        # Get budget settings and expenses
        monthly_budget, savings_goal, actual_savings = get_budget_settings(st.session_state.user['user_id'])
        total_expenses = get_total_expenses(st.session_state.user['user_id'])
        remaining_budget = monthly_budget - total_expenses
        
        # Calculate savings progress
        savings_progress = (actual_savings / savings_goal * 100) if savings_goal > 0 else 0
        
        # Create financial snapshot cards
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                label="💰 Monthly Budget",
                value=f"${monthly_budget:,.2f}",
                help="Your total monthly budget"
            )
            st.write(" ")
            st.metric(
                label="💸 Total Expenses",
                value=f"${total_expenses:,.2f}",
                help="Total expenses logged this month"
            )
        
        with col2:
            st.metric(
                label="💵 Remaining Budget",
                value=f"${remaining_budget:,.2f}",
                delta=f"${remaining_budget:,.2f}" if remaining_budget >= 0 else f"-${abs(remaining_budget):,.2f}",
                help="Budget remaining for this month"
            )
            st.metric(
                label="🎯 Savings Progress",
                value=f"{savings_progress:.1f}%",
                delta=f"${actual_savings:,.2f} of ${savings_goal:,.2f}",
                help="Progress toward your savings goal"
            )
        
        # Progress bar for savings
        if savings_goal > 0:
            progress_percentage = min(savings_progress / 100, 1.0)
            st.progress(progress_percentage, text=f"Savings Goal Progress: {savings_progress:.1f}%")

        # Budget Settings Section
        st.markdown("## ⚙️ Budget Settings")
        
        with st.expander("💡 Update Your Financial Goals", expanded=False):
            with st.form("budget_settings_form"):
                st.markdown("### Set Your Financial Parameters")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    new_monthly_budget = st.number_input(
                        "💰MonthlyBudget($)",
                        min_value=0.0,
                        value=float(monthly_budget),
                        format="%.2f",
                        help="Set your total monthly budget"
                    )
                
                with col2:
                    new_savings_goal = st.number_input(
                        "🎯 Savings Goal ($)",
                        min_value=0.0,
                        value=float(savings_goal),
                        format="%.2f",
                        help="Set your savings target"
                    )
                
                with col3:
                    new_actual_savings = st.number_input(
                        "💎 Actual Savings ($)",
                        min_value=0.0,
                        value=float(actual_savings),
                        format="%.2f",
                        help="How much you've actually saved"
                    )
                
                update_settings = st.form_submit_button("🔄 Update Settings", use_container_width=True)
                
                if update_settings:
                    update_budget_settings(
                        st.session_state.user['user_id'],
                        new_monthly_budget,
                        new_savings_goal,
                        new_actual_savings
                    )
                    st.success("✅ Budget settings updated successfully!")
                    st.rerun()

        # Add New Expense Section
        st.markdown("## 💰 Add New Expense")
        
        with st.expander("Add the expense", expanded=False):
            with st.form("expense_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    amount = st.number_input("💵 Amount ($)", min_value=0.0, format="%.2f", help="Enter the expense amount")
                    category = st.selectbox("📂 Category", ["Food", "Transport", "Bills", "Shopping", "Entertainment", "Healthcare", "Other"])
                    date_input = st.date_input("📅 Date", value="today")
                
                with col2:
                    payment_method = st.selectbox("💳 Payment Method", ["Cash", "Credit Card", "Debit Card", "Online Transfer", "Mobile Payment", "Other"])
                    location = st.text_input("📍 Location (Optional)", placeholder="Where was this expense?")
                    description = st.text_input("📝 Description (Optional)", placeholder="Add a note about this expense")
                
                recurring = st.checkbox("🔄 Recurring Expense", help="Check if this is a recurring expense")
                
                submit_expense = st.form_submit_button("➕ Add Expense", use_container_width=True)
        
        if submit_expense:
            if amount > 0:
                add_expense(
                    st.session_state.user['user_id'],
                    amount,
                    category,
                    date_input.isoformat(),
                    description,
                    recurring,
                    location,
                    payment_method
                )
                st.success(f"✅ Expense of ${amount:.2f} added successfully!")
                st.balloons()
                st.rerun()
            else:
                st.error("⚠️ Please enter a valid amount greater than 0.")

        # Logged Expenses Section
        st.markdown("## 📋 Logged Expenses")
        
        all_expenses = get_all_expenses(st.session_state.user['user_id'])
        
        if all_expenses:
            # Show expenses with pagination
            expenses_per_page = 10
            total_expenses_count = len(all_expenses)
            
            # Pagination controls
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                page_number = st.selectbox(
                    "Select Page",
                    range(1, (total_expenses_count // expenses_per_page) + 2),
                    index=0,
                    help=f"Total expenses: {total_expenses_count}"
                )
            
            # Calculate start and end indices
            start_idx = (page_number - 1) * expenses_per_page
            end_idx = start_idx + expenses_per_page
            expenses_to_show = all_expenses[start_idx:end_idx]
            
            # Display expenses
            for expense in expenses_to_show:
                expense_id, amount, category, date, description, recurring, location, payment_method = expense
                
                # recurring_text = "🔄 Recurring" if recurring else ""
                # location_text = f"📍 {location}" if location else ""
                # description_text = description if description else "No description"
                description_text = str(description) if pd.notna(description) and description else "No description"
                location_text = f"📍 {location}" if pd.notna(location) and location else ""
                recurring_text = "🔄 Recurring" if recurring else ""
                
                st.markdown(f"""
                <div class="expense-entry">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-size: 1.2rem; font-weight: bold; color: #dc3545;">${amount:.2f}</span>
                            <span style="background: #667eea; color: white; padding: 0.2rem 0.5rem; border-radius: 12px; font-size: 0.8rem; margin-left: 0.5rem;">{category}</span>
                        </div>
                        <div style="text-align: right; font-size: 0.9rem; color: #6c757d;">
                            📅 {date} | 💳 {payment_method}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📝 No expenses logged yet. Start adding some expenses!")

    # RIGHT COLUMN
    with right_col:
        # This Week at a Glance Section
        st.markdown("## 📅 This Week at a Glance")
        
        # Get weekly data
        weekly_expenses = get_weekly_expenses(st.session_state.user['user_id'])
        weekly_categories = get_weekly_category_summary(st.session_state.user['user_id'])
        top_weekly_expenses = get_top_weekly_expenses(st.session_state.user['user_id'])
        
        if weekly_expenses:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("###### 📊 Top Categories This Week")
                
                if weekly_categories:
                    # Prepare data for pie chart
                    categories = [row[0] for row in weekly_categories]
                    amounts = [row[1] for row in weekly_categories]
                    
                    # Create pie chart
                    fig = px.pie(
                        values=amounts,
                        names=categories,
                        title="Expense Distribution by Category",
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    fig.update_layout(
                        height=300,
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("📝 No expenses recorded this week yet.")
            
            with col2:
                st.markdown("###### 💰 Top Expenses This Week")
                
                if top_weekly_expenses:
                    for expense in top_weekly_expenses:
                        amount, category, date, description, location = expense
                        
                        # Format the expense display
                        st.markdown(f"""
                        <div class="expense-item">
                            <div>
                                <span class="expense-amount">${amount:.2f}</span>
                                <span class="expense-category">{category}</span>
                            </div>
                            <div class="expense-details">
                                <div style="font-size: 0.9rem; color: #6c757d;">
                                    📅 {date}
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("📝 No expenses recorded this week yet.")
        
        # Weekly Summary Cards
        if weekly_expenses:
            total_weekly_amount = sum([expense[1] for expense in weekly_expenses])
            weekly_expense_count = len(weekly_expenses)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    label="💸 Total This Week",
                    value=f"${total_weekly_amount:.2f}",
                    help="Total amount spent this week"
                )
            with col2:
                st.metric(
                    label="📊 Number of Expenses",
                    value=f"{weekly_expense_count}",
                    help="Number of expenses recorded this week"
                )

        

        # AI Assistant Chatbot Section
        # Initialize chat message history
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []

        # Page title
        st.markdown("## 🤖 AI Expense Assistant")

        # CSS for chatbot layout
        with open("chat.css") as f:
            chat_css = f"<style>{f.read()}</style>"


        # HTML container for chat messages
        chat_html = '<div class="chatbot-container">'
        for msg in st.session_state.chat_messages:
            sender_class = 'user-message' if msg['sender'] == 'user' else 'system-message'
            sender_label = 'You' if msg['sender'] == 'user' else 'Assistant'
            msg_html = f"""
            <div class="chat-message {sender_class}">
                <strong>{sender_label}:</strong> {html.escape(msg['message'])}
            </div>
            """
            chat_html += msg_html
        chat_html += '</div>'

        # Render the CSS and chat messages in a proper HTML block
        components.html(chat_css + chat_html, height=500, scrolling=True)

        # Input area
        col1, col2 = st.columns([4, 1])
        with col1:
            user_input = st.text_input(
                "Type your message...",
                key="chat_input",
                placeholder="Ask about your expenses, budgeting tips, etc.",
                label_visibility="collapsed"
            )
        with col2:
            send_button = st.button("📤 Send", use_container_width=True)

        # Process user input
        if send_button and user_input:
            # Add user message
            st.session_state.chat_messages.append({
                "sender": "user",
                "message": user_input
            })

            ############ Chatbot ################
            config = {"configurable": {"thread_id": "multi-agent-thread-1"}}
            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "current_agent": "none",
                "agent_context": {}
            }
            agent_result = chatbot_responder.invoke(initial_state, config=config)
            # Add placeholder assistant response
            #response = "Functionality Coming Soon!!!!!!!!!"
            # To handle sql statements:
            if agent_result["messages"][-1].content.startswith("Here is the SQL statement:"):
                match = re.search(r"VALUES\s*\((.*?)\)", agent_result["messages"][-1].content, re.IGNORECASE | re.DOTALL)
                try:
                    values_str = match.group(1)
                    # Split the values while handling quoted strings properly
                    pattern = r"""
                        '(?:\\'|[^'])*'     |  # Single quoted string
                        "(?:\\"|[^"])*"     |  # Double quoted string
                        [^,]+                  # Non-quoted value
                    """
                    raw_values = re.findall(pattern, values_str, re.VERBOSE)
                    # Strip and clean values
                    cleaned_values = [val.strip().strip(',') for val in raw_values]

                    # Convert to Python values (remove quotes and cast types)
                    def clean(val):
                        val = val.strip()
                        if val.lower() == "null":
                            return None
                        elif val.lower() == "current_date":
                            from datetime import date
                            return date.today()
                        elif val.startswith(("'", '"')) and val.endswith(("'", '"')):
                            return val[1:-1]
                        elif '.' in val:
                            return float(val)
                        else:
                            try:
                                return int(val)
                            except ValueError:
                                return val
                            
                    parsed_values = list(map(clean, cleaned_values))
                    (
                        user_id_agent,
                        amount_agent,
                        category_agent,
                        date_agent,
                        description_agent,
                        recurring_agent,
                        location_agent,
                        payment_method_agent
                    ) = parsed_values

                    add_expense(st.session_state.user['user_id'],
                    amount_agent,
                    category_agent,
                    date_agent,
                    description_agent,
                    recurring_agent,
                    location_agent,
                    payment_method_agent)

                    response = "Transaction added successfully!!!"

                except:
                    response = "Transaction cannot be added due to internal error."

            else:
                response = agent_result["messages"][-1].content
            st.session_state.chat_messages.append({
                "sender": "system",
                "message": response
            })

            # Clearing input and rerun to display new messages
            st.rerun()


# Logout functionality if user session expires or page not found
else:
    st.session_state.user = None
    st.session_state.page = 'login'
    st.rerun()