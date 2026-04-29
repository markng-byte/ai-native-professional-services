import streamlit as st
import time
from dotenv import load_dotenv

# Set page config before ANY other Streamlit commands
st.set_page_config(page_title="AI Executive Assistant", page_icon="🤖", layout="wide")

import sys
import os
# Add the current directory to path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crewai import Crew, Process
from agents import ProfessionalServicesAgents
from tasks import ProfessionalServicesTasks
from tools.intent_classifier_tool import IntentClassifierTool
from tools.jurisdiction_compare_tool import JurisdictionCompareTool

load_dotenv()

# ==========================================
# UI Setup & Styling
# ==========================================
st.title("🤖 Command Center: Senior Executive Assistant")
st.markdown("*OneIBC AI-Native Professional Services Architecture*")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello Mark. I am your Executive Assistant. How can I help you prepare today?"}
    ]

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==========================================
# CrewAI Execution Function
# ==========================================
def execute_crewai_request(prompt: str) -> str:
    """Runs the CrewAI multi-agent workflow based on the prompt."""
    agents = ProfessionalServicesAgents()
    tasks = ProfessionalServicesTasks()

    # 1. Initialize Agents
    ea_agent = agents.executive_assistant_agent()
    orchestrator = agents.orchestrator_agent()
    researcher = agents.research_agent()

    # Equip tools
    orchestrator.tools = [IntentClassifierTool()]
    researcher.tools = [JurisdictionCompareTool()]

    # 2. Initialize Tasks
    # The EA takes the main request and delegates. We structure it sequentially for the MVP.
    ea_task = tasks.executive_synthesis_task(ea_agent, prompt)
    classification_task = tasks.intake_classification_task(orchestrator, prompt)
    
    # We mock a standard jurisdiction task if the user mentions 'compare'
    if "compare" in prompt.lower() or "bvi" in prompt.lower():
        comparison_task = tasks.jurisdiction_comparison_task(researcher, "['VG', 'KY', 'SG']")
        crew_tasks = [classification_task, comparison_task, ea_task]
    else:
        crew_tasks = [classification_task, ea_task]

    # 3. Assemble Crew
    crew = Crew(
        agents=[ea_agent, orchestrator, researcher],
        tasks=crew_tasks,
        process=Process.sequential,
        verbose=False # Keep terminal clean during UI run
    )

    # 4. Execute
    try:
        result = crew.kickoff()
        return str(result)
    except Exception as e:
        return f"⚠️ **Error executing task:**\n```\n{str(e)}\n```"

# ==========================================
# Chat Interface
# ==========================================
if prompt := st.chat_input("E.g., Compare BVI and Cayman for a new holding company..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        with st.spinner("Analyzing request and orchestrating agents..."):
            # Execute CrewAI backend
            response = execute_crewai_request(prompt)
            
            # Simulate typing stream for UX
            message_placeholder = st.empty()
            full_response = ""
            # We don't stream CrewAI natively easily, so we just display the final result instantly
            message_placeholder.markdown(response)
            
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

# Sidebar context
with st.sidebar:
    st.header("Agent Roster (Active)")
    st.success("🤖 Executive Assistant (Manager)")
    st.success("🧭 Orchestrator (Intake)")
    st.success("🔍 Research Agent (Data)")
    st.warning("🛡️ Compliance Agent (Idle)")
    st.warning("📝 Drafting Agent (Idle)")
    
    st.divider()
    st.header("Firm Context")
    st.caption("**User**: Mark Ng")
    st.caption("**Org**: OneIBC")
    st.caption("**Mode**: Command Center")
