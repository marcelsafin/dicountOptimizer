"""
Main agent entry point for ADK
This file allows ADK to discover agents

NOTE: The old monolithic agent.py has been refactored into a service-based architecture.
The new ShoppingOptimizerAgent is available via the factory pattern.
"""

# The old agent.py has been removed and replaced with a service-based architecture.
# To use the shopping optimizer, use the factory:
#
# from agents.discount_optimizer.factory import create_shopping_optimizer_agent
# agent = await create_shopping_optimizer_agent()
#
# Or for ADK integration, use the agents in agents/discount_optimizer/agents/

__all__ = []
