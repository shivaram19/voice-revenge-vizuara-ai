"""
Abstract Tool Interface + Tool Registry
OCP: Register new tools without modifying core service code.
Ref: OpenAI (2023). Function Calling API [^13].
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional


@dataclass
class ToolResult:
    """Standardized tool execution result."""
    success: bool
    message: str          # Voice-formatted response
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class Tool(ABC):
    """
    Abstract base for all receptionist tools.
    Each tool is self-contained: schema definition + execution + formatting.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name used in function-calling schema."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM function-calling."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON Schema parameters object."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with parsed arguments."""
        pass

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function-calling format [^13]."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters.get("properties", {}),
                    "required": self.parameters.get("required", []),
                },
            },
        }


class ToolRegistry:
    """
    Registry for tools. Satisfies OCP: add tools without modifying
    the receptionist service core.

    Usage:
        registry = ToolRegistry()
        registry.register(FindContractorTool(db))
        registry.register(BookAppointmentTool(db))
        schemas = registry.schemas()  # For LLM
        result = await registry.execute("find_contractor", {"query": "plumbing"})
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> "ToolRegistry":
        """Register a tool. Chainable."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool
        return self

    def unregister(self, name: str) -> "ToolRegistry":
        """Remove a tool. Chainable."""
        self._tools.pop(name, None)
        return self

    def get(self, name: str) -> Optional[Tool]:
        """Retrieve a tool by name."""
        return self._tools.get(name)

    def schemas(self) -> List[Dict[str, Any]]:
        """Return all tool schemas for LLM function-calling."""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    async def execute(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute a tool by name with arguments."""
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(
                success=False,
                message=f"Tool '{name}' not found.",
                error="unknown_tool",
            )
        try:
            return await tool.execute(**arguments)
        except Exception as e:
            return ToolResult(
                success=False,
                message="I'm sorry, I encountered an error while processing your request.",
                error=str(e),
            )

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)


# References
# [^13]: OpenAI. (2023). Function Calling API Documentation.
