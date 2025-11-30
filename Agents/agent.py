import logging
import inspect
from typing import Dict, Any, List, Callable
from abc import ABC, abstractmethod
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate
from langchain_core.tools import tool, BaseTool

logger = logging.getLogger(__name__)


class Agent(ABC):    
    """
    Base Agent Class for Multi-Agent System
    This class provides a template for creating agents with specific roles,
    tools, and behaviors in a multi-agent environment.
    """
    def __init__(self, llm, config: Dict[str, Any], agent_name: str):
        """
        Initialize the base agent.
        
        Args:
            llm: LangChain LLM instance
            config: Configuration dictionary
            agent_name: Name of the agent (for logging and identification)
        """
        self.llm = llm
        self.config = config
        self.agent_name = agent_name
        self.tools = self._create_tools()
        self.agent = self._create_agent()

        logger.debug(f"{self.agent_name} initialized with {len(self.tools)} tools")
    
    @abstractmethod
    def _create_tools(self) -> List[BaseTool]:
        """
        *** subclasses must implement this ***

        Create and return the list of tools for this agent.        
        Returns:
            List of tool functions (call self._auto_wrap_tools(list_of_functions))
        """
        pass
    
    def _auto_wrap_tools(self, tool_functions: List[Callable]) -> List[BaseTool]:
        """
        Automatically wrap regular functions with @tool decorator.
        Args:
            tool_functions: List of functions to wrap
        """
        wrapped_tools = []
        
        for func in tool_functions:
            # Wrap the function with @tool decorator
            wrapped = tool(func)
            wrapped_tools.append(wrapped)
            logger.debug(f"{self.agent_name}: Auto-wrapped tool '{func.__name__}'")
        
        return wrapped_tools
    
    @abstractmethod
    def _get_system_prompt(self) -> str:
        """
        *** subclasses must implement this ***
        
        Return the system prompt that defines this agent's role and behavior.
        
        The system prompt should describe:
        - The agent's role and responsibilities
        - The workflow it should follow
        - How to use available tools
        - Expected output format
        
        Returns:
            System prompt string
        """
        pass
    
    def _create_agent(self) -> AgentExecutor:
        """
        Create the agent executor with tools and prompt.
        
        This method uses the system prompt and tools to create a LangChain
        agent executor. Override if you need custom agent behavior.
        
        Returns:
            Configured AgentExecutor instance
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=self.config.get('agents', {}).get('verbose', False),
            max_iterations=self.config.get('agents', {}).get('max_iterations', 15),
            handle_parsing_errors=True,
            return_intermediate_steps=False
        )
    
    def get_tool_names(self) -> List[str]:
        """
        Get the names of all tools available to this agent.
        
        Returns:
            List of tool names
        """
        return [t.name for t in self.tools]
    
    def get_tool_count(self) -> int:
        """
        Get the number of tools available to this agent.
        
        Returns:
            Number of tools
        """
        return len(self.tools)
    
    def get_agent_info(self) -> Dict[str, Any]:
        """
        Get information about this agent.
        
        Returns:
            Dictionary with agent information
        """
        return {
            'name': self.agent_name,
            'tool_count': self.get_tool_count(),
            'tool_names': self.get_tool_names(),
            'max_iterations': self.config.get('agents', {}).get('max_iterations', 5),
            'verbose': self.config.get('agents', {}).get('verbose', False)
        }
    
    def __str__(self) -> str:
        """String representation of the agent."""
        return f"{self.agent_name} ({self.get_tool_count()} tools)"
    
    def __repr__(self) -> str:
        """Detailed representation of the agent."""
        return f"<Agent: {self.agent_name}, Tools: {self.get_tool_names()}>"