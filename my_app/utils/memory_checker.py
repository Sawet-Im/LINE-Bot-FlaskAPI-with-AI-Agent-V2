from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage
from typing import List, Dict, Any

class MemoryCheckerCallback(BaseCallbackHandler):
    """Dumps the final prompt's components, including chat_history."""
    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Run when LLM starts running. Prompts list contains the final prompt."""
        print("\n--- 🛑 START: FULL LLM PROMPT (w/ Memory) 🛑 ---")

        # สำหรับ Chat Model (Gemini), Prompt มักจะถูกส่งเป็น strings ใน List
        full_prompt = prompts[0] 
        print(full_prompt)

        print("--- 🛑 END: FULL LLM PROMPT 🛑 ---\n")