import os
from dotenv import load_dotenv
from crewai import Crew, Process

# Import agents and tasks
from agents import ProfessionalServicesAgents
from tasks import ProfessionalServicesTasks

# Import tools
from tools.intent_classifier_tool import IntentClassifierTool
from tools.jurisdiction_compare_tool import JurisdictionCompareTool

# Load environment variables
load_dotenv()

def main():
    print("==================================================")
    print("AI-Native Professional Services OS - CrewAI MVP")
    print("==================================================")
    
    # 1. Initialize Agents
    agents = ProfessionalServicesAgents()
    orchestrator = agents.orchestrator_agent()
    researcher = agents.research_agent()
    # compliance = agents.compliance_agent()
    
    # Assign tools to agents
    orchestrator.tools = [IntentClassifierTool()]
    researcher.tools = [JurisdictionCompareTool()]
    
    # 2. Initialize Tasks
    tasks = ProfessionalServicesTasks()
    
    # Example input from a user
    user_request = "Can you compare BVI and Cayman for a new holding company? I need to know the cost and tax differences."
    print(f"\n[INBOUND REQUEST] {user_request}\n")
    
    # Create the task workflow
    # Task 1: Orchestrator classifies the intent
    classification_task = tasks.intake_classification_task(orchestrator, user_request)
    
    # Task 2: Researcher executes the comparison
    # In a dynamic workflow, this would be conditionally added based on Task 1's output.
    # For this linear CrewAI demo, we chain them.
    comparison_task = tasks.jurisdiction_comparison_task(researcher, "['VG', 'KY']")
    
    # 3. Assemble the Crew
    service_crew = Crew(
        agents=[orchestrator, researcher],
        tasks=[classification_task, comparison_task],
        process=Process.sequential,
        verbose=True
    )
    
    # 4. Execute the workflow
    print("Starting execution...\n")
    result = service_crew.kickoff()
    
    print("\n==================================================")
    print("FINAL OUTPUT")
    print("==================================================")
    print(result)

if __name__ == "__main__":
    main()
