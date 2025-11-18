"""
Main agent entry point for ADK
This file allows ADK to discover agents
"""

from agents.discount_optimizer.agent import root_agent as discount_optimizer_agent


# Primary agent - ADK använder denna som default
root_agent = discount_optimizer_agent

# För att lägga till fler agenter i dropdown, skapa dem här:
# from agents.other_agent.agent import root_agent as other_agent
# Sedan exportera dem i __all__

# Export all agents - ADK skapar dropdown om flera agenter finns
__all__ = ["root_agent"]
