import json
from typing import Any, Dict, List, Optional
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from core.trajectory_logger import trajectory_logger
from core.task_manager import current_task_id

class TrajectoryCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler that automatically logs LLM calls to the trajectory logger.
    """
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> Any:
        self.last_prompt = prompts[0] if prompts else ""

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        task_id = current_task_id.get()
        if not task_id:
            return # Not running within a queued task
            
        agent_name = kwargs.get("tags", ["Unknown Agent"])[0]
        model_name = kwargs.get("model_name", "Unknown Model")
        
        for generations in response.generations:
            for generation in generations:
                trajectory_logger.log_llm_call(
                    task_id=task_id,
                    agent_name=agent_name,
                    model_name=model_name,
                    prompt=self.last_prompt,
                    response=generation.text
                )

# Global callback instance
trajectory_callback = TrajectoryCallbackHandler()
