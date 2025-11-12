"""
Main agent entry point for ADK
This file allows ADK to discover the discount_optimizer agent
"""

from agents.discount_optimizer.agent import root_agent

# Export root_agent so ADK can find it
__all__ = ['root_agent']
