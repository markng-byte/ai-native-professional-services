import os
from crewai import Agent
from langchain_anthropic import ChatAnthropic

# Initialize the Anthropic Claude model
# We use Claude 3 Opus or Sonnet depending on the task complexity
llm = ChatAnthropic(model_name="claude-3-opus-20240229")

class ProfessionalServicesAgents:
    def executive_assistant_agent(self):
        """
        L5/L6 Executive Assistant (Command Center): Translates executive intent
        and synthesizes outputs from sub-agents.
        """
        return Agent(
            role='Senior Executive Assistant',
            goal='Act as the Command Center for Mark Ng, translating high-level executive requests into orchestrated tasks and synthesizing complex data into structured briefs.',
            backstory=(
                "You are the Senior Executive Assistant and Command Center for Mark Ng at OneIBC. "
                "You sit at the top of an AI-Native architecture. You do not perform raw data entry "
                "or compliance checks yourself; instead, you command specialist agents "
                "(Orchestrator, Research, Compliance) to do the heavy lifting, and you synthesize their outputs. "
                "You always produce structured outputs, using tables over prose when appropriate."
            ),
            allow_delegation=True,
            verbose=True,
            llm=llm
        )

    def orchestrator_agent(self):
        """
        L5 Orchestrator Agent: Central router/planner that classifies intents
        and delegates to specialists.
        """
        return Agent(
            role='Orchestrator and Intake Officer',
            goal='Accurately classify incoming client requests, identify the required client context, and delegate the task to the correct specialist agent.',
            backstory=(
                "You are the central router for an AI-native professional services firm. "
                "You do not execute compliance checks or draft documents yourself. "
                "Your job is to understand what the user wants, gather the initial client profile, "
                "and pass a well-structured task to the Research, Compliance, or Drafting agent. "
                "You have access to the intent classifier and client lookup tools."
            ),
            allow_delegation=True,
            verbose=True,
            llm=llm
        )

    def research_agent(self):
        """
        L5 Research Agent: Handles jurisdiction comparisons and regulatory lookups.
        """
        return Agent(
            role='Research Specialist',
            goal='Provide accurate, well-sourced comparisons of jurisdictions and regulatory frameworks.',
            backstory=(
                "You are the Research Specialist. Your job is to query the firm's GraphRAG knowledge base "
                "to compare corporate jurisdictions (e.g., BVI vs Cayman) across dimensions like cost, "
                "tax, substance requirements, and banking access. "
                "You always cite your sources and flag any data that you are not highly confident about."
            ),
            allow_delegation=False,
            verbose=True,
            llm=llm
        )

    def compliance_agent(self):
        """
        L5 Compliance Agent: High-risk executor handling sanctions, UBOs, and conflict checks.
        """
        return Agent(
            role='Compliance Officer',
            goal='Perform rigorous AML/KYC checks, identify UBOs, and detect conflicts of interest.',
            backstory=(
                "You are the strict Compliance Officer. You operate the high-risk compliance gates. "
                "You NEVER auto-approve a sanctions match. You ALWAYS require human review for complex UBO chains. "
                "Your job is to run the screening tools and return detailed, structured results for human sign-off."
            ),
            allow_delegation=False,
            verbose=True,
            llm=llm
        )
