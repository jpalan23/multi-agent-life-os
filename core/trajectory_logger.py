import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from core.db_manager import db

class TrajectoryLogger:
    """
    Instruments LLM calls to capture the reasoning path (Trajectory).
    Saves traces to the eval_runs table for future auditing and V5 optimization.
    """
    
    @staticmethod
    def log_llm_call(task_id: int, agent_name: str, model_name: str, prompt: str, response: str, tools_used: List[Dict[str, Any]] = None):
        """Logs a single LLM interaction within a task trajectory."""
        # For now, we'll store individual calls in a JSON list within the trace
        # In a more advanced version, we'd have a separate 'trajectory_steps' table
        
        # Fetch current trace if exists, or start new
        existing = db.execute_query("SELECT raw_trace_json FROM eval_runs WHERE id = ?", (task_id,))
        
        trace = []
        if existing and existing[0]['raw_trace_json']:
            trace = json.loads(existing[0]['raw_trace_json'])
            
        step = {
            "timestamp": datetime.now().isoformat(),
            "agent_name": agent_name,
            "model": model_name,
            "prompt": prompt,
            "response": response,
            "tools": tools_used or []
        }
        trace.append(step)
        
        # Update or Insert into eval_runs
        # Note: In this simple version, we use task_id as the primary link
        db.execute_query(
            "INSERT OR REPLACE INTO eval_runs (id, agent_name, raw_trace_json, status) VALUES (?, ?, ?, ?)",
            (task_id, agent_name, json.dumps(trace), 'PROCESSING')
        )

# Global instance
trajectory_logger = TrajectoryLogger()
