import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from core.db_manager import db

class TaskQueueManager:
    """
    Manages a strictly sequential task queue for the Multi-Agent Life-OS.
    Ensures Zero-Concurrency to protect local hardware resources.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskQueueManager, cls).__new__(cls)
            cls._instance.queue = asyncio.PriorityQueue()
            cls._instance.is_running = False
            cls._instance.handlers = {}
        return cls._instance

    def register_handler(self, task_type: str, handler: Callable):
        """Registers a function to handle a specific task type."""
        self.handlers[task_type] = handler

    async def add_task(self, task_type: str, payload: Dict[str, Any], priority: int = 2):
        """
        Adds a task to the persistent database and the in-memory priority queue.
        Priority levels: 0 (Highest) to 3 (Lowest).
        """
        task_id = db.execute_query(
            "INSERT INTO task_queue (task_type, priority, payload_json) VALUES (?, ?, ?)",
            (task_type, priority, json.dumps(payload))
        )
        
        # In-memory queue item: (priority, timestamp, task_id, task_type, payload)
        # Using timestamp as a secondary sort key for FIFO within the same priority.
        await self.queue.put((priority, datetime.now().timestamp(), task_id, task_type, payload))
        print(f"[Queue] Task Added: {task_type} (ID: {task_id}, Priority: {priority})")
        return task_id

    async def start_worker(self):
        """Starts the background worker to process tasks sequentially."""
        if self.is_running:
            return
        
        self.is_running = True
        print("[Queue] Sequential Worker Started.")
        
        while self.is_running:
            try:
                # Wait for the next task
                priority, timestamp, task_id, task_type, payload = await self.queue.get()
                
                print(f"[Queue] Processing Task {task_id}: {task_type}")
                
                # Update status to PROCESSING
                db.execute_query(
                    "UPDATE task_queue SET status = 'PROCESSING', started_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), task_id)
                )
                
                handler = self.handlers.get(task_type)
                if handler:
                    try:
                        # Execute the handler (must be an async function)
                        await handler(payload)
                        
                        # Update status to COMPLETED
                        db.execute_query(
                            "UPDATE task_queue SET status = 'COMPLETED', completed_at = ? WHERE id = ?",
                            (datetime.now().isoformat(), task_id)
                        )
                        print(f"[Queue] Task {task_id} COMPLETED.")
                    except Exception as e:
                        print(f"[Queue] Task {task_id} FAILED: {e}")
                        db.execute_query(
                            "UPDATE task_queue SET status = 'FAILED', error_message = ? WHERE id = ?",
                            (str(e), task_id)
                        )
                else:
                    print(f"[Queue] No handler registered for task type: {task_type}")
                    db.execute_query(
                        "UPDATE task_queue SET status = 'FAILED', error_message = 'No handler registered' WHERE id = ?",
                        (task_id,)
                    )
                
                # Mark task as done in the queue
                self.queue.task_done()
                
            except Exception as e:
                print(f"[Queue] Worker Error: {e}")
                await asyncio.sleep(1)

    async def stop_worker(self):
        """Stops the worker loop."""
        self.is_running = False

    async def restore_pending_tasks(self):
        """Restores pending tasks from the database upon startup."""
        pending_tasks = db.execute_query(
            "SELECT * FROM task_queue WHERE status = 'PENDING' OR status = 'PROCESSING' ORDER BY priority ASC, created_at ASC"
        )
        for task in pending_tasks:
            # Re-queue processing tasks as pending since they might have crashed
            await self.queue.put((
                task['priority'], 
                datetime.fromisoformat(task['created_at']).timestamp(), 
                task['id'], 
                task['task_type'], 
                json.loads(task['payload_json'])
            ))
        if pending_tasks:
            print(f"[Queue] Restored {len(pending_tasks)} tasks from database.")

# Global instance
task_manager = TaskQueueManager()
