"""
Placement Cell Assistant interaction layer (Root module).
"""
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

import backend.bot as _backend_bot

MODEL = _backend_bot.MODEL
SYSTEM_PROMPT = _backend_bot.SYSTEM_PROMPT
generate_response = _backend_bot.generate_response
messages_to_contents = _backend_bot.messages_to_contents
__all__ = ["MODEL", "SYSTEM_PROMPT", "generate_response", "messages_to_contents"]