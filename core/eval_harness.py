import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from core.db_manager import db
from core.llm_factory import get_deep_llm
from langchain_core.messages import HumanMessage, SystemMessage

class EvalHarness:
    """
    The 'Referee' layer that audits agent execution trajectories.
    Uses LLM-as-a-Judge to score performance against a 12-metric matrix.
    """
    
    def __init__(self):
        # We use the deep reasoning model for judging
        self.judge_llm = get_deep_llm(temperature=0.0, keep_alive="10m")

    async def run_eval(self, trace_id: int) -> Dict[str, Any]:
        """Loads a trace, calls the judge, and saves the score."""
        print(f"[Eval] Auditing Trajectory for Task ID: {trace_id}")
        
        # Load the trace from DB
        runs = db.execute_query(
            "SELECT agent_name, raw_trace_json FROM eval_runs WHERE id = ?",
            (trace_id,)
        )
        
        if not runs:
            return {"error": "Trace not found"}
            
        agent_name = runs[0]['agent_name']
        raw_trace = runs[0]['raw_trace_json']
        
        # Call the Judge
        result = await self._judge_trajectory(agent_name, raw_trace)
        
        # Save the results
        db.execute_query(
            """UPDATE eval_runs SET 
               total_score = ?, 
               judge_rationale = ?, 
               status = ? 
               WHERE id = ?""",
            (result['total_score'], result['rationale'], result['status'], trace_id)
        )
        
        print(f"[Eval] Score for {agent_name}: {result['total_score']}/10 ({result['status']})")
        return result

    async def _judge_trajectory(self, agent_name: str, raw_trace: str) -> Dict[str, Any]:
        """Uses the LLM to score the trace."""
        
        # Prepare the judge prompt
        system_prompt = """You are the Lead Auditor for a Multi-Agent Life-OS.
Your job is to evaluate the 'Execution Trajectory' of an agent.
You must score the agent on a scale of 1-10 across three categories:
1. Reasoning (Coherence & Philosophy)
2. Tools (Selection & Precision)
3. Output (Faithfulness & Utility)

Provide a total average score (1-10).
Provide a concise rationale for your score.
Identify if this is a 'SUCCESS' or 'FAILED' (score < 5).

Respond in JSON format:
{
  "total_score": 8.5,
  "rationale": "The agent correctly counter-argued the bear case...",
  "status": "SUCCESS"
}"""

        prompt = f"Agent Name: {agent_name}\n\nExecution Trace (JSON):\n{raw_trace}"
        
        try:
            response = await self.judge_llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt)
            ])
            
            # Extract JSON from response
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            
            return json.loads(content)
        except Exception as e:
            return {
                "total_score": 0,
                "rationale": f"Judge failed to evaluate: {e}",
                "status": "FAILED"
            }

    async def run_batch_eval(self, team: Optional[str] = None):
        """Runs evaluation on all recent 'PROCESSING' or unscored traces."""
        query = "SELECT id FROM eval_runs WHERE status = 'PROCESSING' OR total_score IS NULL"
        if team:
            query += f" AND agent_name LIKE '%{team}%'"
            
        pending = db.execute_query(query)
        print(f"[Eval] Starting batch evaluation for {len(pending)} traces...")
        
        for run in pending:
            await self.run_eval(run['id'])

# Global instance
eval_harness = EvalHarness()
