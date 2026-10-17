"""Official DeepSeek Harness SDK adapter; no mock or unsafe-profile fallback."""
from .executor import HarnessError, capabilities, execute_assignment
__all__ = ['HarnessError', 'capabilities', 'execute_assignment']
