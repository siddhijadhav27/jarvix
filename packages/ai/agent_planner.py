"""
Agent Task Planner for Jarvix - Step 3
Handles multi-step tasks like:
- "Buy ETH if BTC drops below 90k and message me"
- "Monitor SOL price every hour and alert me if it pumps"
- "Set a stop loss for my BTC at 85k and notify me if triggered"
"""

import json
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class StepType(Enum):
    MONITOR = "monitor"           # Watch a price/condition
    CONDITION = "condition"       # If/else check
    ACTION = "action"             # Execute trade/send message
    NOTIFY = "notify"             # Send notification
    WAIT = "wait"                 # Wait for time/condition
    FETCH_DATA = "fetch_data"     # Get price/data


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PlanStep:
    """Single step in an agent task plan"""
    step_number: int
    step_type: str
    description: str
    parameters: Dict[str, Any]
    depends_on: Optional[List[int]] = None
    status: str = "pending"
    result: Optional[Any] = None


@dataclass
class AgentTask:
    """A multi-step agent task"""
    task_id: str
    user_id: str
    original_message: str
    steps: List[PlanStep]
    status: str = "pending"
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class AgentPlanner:
    """Plans and executes multi-step agent tasks"""
    
    def __init__(self):
        self.active_tasks: Dict[str, AgentTask] = {}
    
    def parse_task(self, message: str, user_id: str) -> Optional[AgentTask]:
        """
        Parse a natural language message into a structured agent task.
        Returns None if message is not an agent task.
        """
        msg_lower = message.lower()
        
        # Check if this is an agent task
        has_condition = bool(re.search(r'\b(if|when|then|after|before|once|whenever)\b', msg_lower))
        has_monitor = bool(re.search(r'\b(monitor|watch|track|wait for|keep an eye on)\b', msg_lower))
        has_multi_action = bool(re.search(r'\b(and then|also|additionally|and message|and notify|and alert)\b', msg_lower))
        has_schedule = bool(re.search(r'\b(every|hourly|daily|weekly|at \d+|schedule)\b', msg_lower))
        
        if not (has_condition or has_monitor or has_multi_action or has_schedule):
            return None
        
        # Parse the task
        steps = []
        step_num = 1
        
        # Extract crypto symbols
        symbols = re.findall(r'\b(btc|eth|sol|ada|doge|xrp|dot|link|avax|matic|bnb)\b', msg_lower)
        symbols = [s.upper() for s in symbols]
        
        # Extract price targets
        price_matches = re.findall(r'(\d+[\d,]*(?:\.\d+)?)\s*(k|thousand)?', msg_lower)
        prices = []
        for match in price_matches:
            num = match[0].replace(',', '')
            if match[1] in ['k', 'thousand']:
                num = float(num) * 1000
            else:
                num = float(num)
            prices.append(num)
        
        # Extract time intervals
        time_match = re.search(r'every\s+(\d+)?\s*(hour|minute|day|week)', msg_lower)
        interval = None
        if time_match:
            interval_num = int(time_match.group(1)) if time_match.group(1) else 1
            interval_unit = time_match.group(2)
            interval = f"{interval_num} {interval_unit}{'s' if interval_num > 1 else ''}"
        
        # Build steps based on message patterns
        
        # Pattern: "Buy X if Y drops below Z"
        if has_condition and 'buy' in msg_lower and symbols:
            # Step 1: Monitor price
            target_symbol = symbols[1] if len(symbols) > 1 else symbols[0]
            target_price = prices[0] if prices else None
            
            steps.append(PlanStep(
                step_number=step_num,
                step_type=StepType.FETCH_DATA.value,
                description=f"Fetch current price of {target_symbol}",
                parameters={"symbol": target_symbol}
            ))
            step_num += 1
            
            steps.append(PlanStep(
                step_number=step_num,
                step_type=StepType.CONDITION.value,
                description=f"Check if {target_symbol} price {'drops below' if 'below' in msg_lower else 'rises above'} ${target_price:,.0f}" if target_price else f"Check {target_symbol} price condition",
                parameters={
                    "symbol": target_symbol,
                    "condition": "below" if 'below' in msg_lower else "above",
                    "target_price": target_price,
                    "depends_on": step_num - 1
                }
            ))
            step_num += 1
            
            # Step 3: Execute buy
            buy_symbol = symbols[0]
            steps.append(PlanStep(
                step_number=step_num,
                step_type=StepType.ACTION.value,
                description=f"Execute buy order for {buy_symbol}",
                parameters={
                    "action": "buy",
                    "symbol": buy_symbol,
                    "depends_on": step_num - 1
                }
            ))
            step_num += 1
        
        # Pattern: "Monitor X and alert me if..."
        elif has_monitor and symbols:
            monitor_symbol = symbols[0]
            
            steps.append(PlanStep(
                step_number=step_num,
                step_type=StepType.MONITOR.value,
                description=f"Monitor {monitor_symbol} price{' every ' + interval if interval else ''}",
                parameters={
                    "symbol": monitor_symbol,
                    "interval": interval or "1 hour"
                }
            ))
            step_num += 1
            
            if prices:
                steps.append(PlanStep(
                    step_number=step_num,
                    step_type=StepType.CONDITION.value,
                    description=f"Alert when price reaches ${prices[0]:,.0f}",
                    parameters={
                        "symbol": monitor_symbol,
                        "target_price": prices[0],
                        "condition": "above" if 'above' in msg_lower or 'pump' in msg_lower else "below"
                    }
                ))
                step_num += 1
            
            steps.append(PlanStep(
                step_number=step_num,
                step_type=StepType.NOTIFY.value,
                description=f"Send notification to user",
                parameters={"message": f"{monitor_symbol} price alert triggered!"}
            ))
            step_num += 1
        
        # Pattern: "Set stop loss for X at Y"
        elif 'stop loss' in msg_lower or 'stop-loss' in msg_lower and symbols:
            symbol = symbols[0]
            stop_price = prices[0] if prices else None
            
            steps.append(PlanStep(
                step_number=step_num,
                step_type=StepType.MONITOR.value,
                description=f"Monitor {symbol} price for stop loss",
                parameters={"symbol": symbol}
            ))
            step_num += 1
            
            steps.append(PlanStep(
                step_number=step_num,
                step_type=StepType.CONDITION.value,
                description=f"Check if {symbol} drops to ${stop_price:,.0f}" if stop_price else f"Check {symbol} stop loss condition",
                parameters={
                    "symbol": symbol,
                    "condition": "below",
                    "target_price": stop_price
                }
            ))
            step_num += 1
            
            steps.append(PlanStep(
                step_number=step_num,
                step_type=StepType.ACTION.value,
                description=f"Execute stop loss sell for {symbol}",
                parameters={"action": "sell", "symbol": symbol}
            ))
            step_num += 1
            
            steps.append(PlanStep(
                step_number=step_num,
                step_type=StepType.NOTIFY.value,
                description="Notify user of stop loss trigger",
                parameters={"message": f"Stop loss triggered for {symbol}!"}
            ))
            step_num += 1
        
        # Generic multi-step fallback
        else:
            steps.append(PlanStep(
                step_number=step_num,
                step_type=StepType.FETCH_DATA.value,
                description="Analyze market conditions",
                parameters={}
            ))
            step_num += 1
            
            steps.append(PlanStep(
                step_number=step_num,
                step_type=StepType.CONDITION.value,
                description="Evaluate conditions",
                parameters={}
            ))
            step_num += 1
            
            steps.append(PlanStep(
                step_number=step_num,
                step_type=StepType.ACTION.value,
                description="Execute requested action",
                parameters={}
            ))
            step_num += 1
        
        # Create task
        import uuid
        from datetime import datetime
        
        task = AgentTask(
            task_id=str(uuid.uuid4())[:8],
            user_id=user_id,
            original_message=message,
            steps=steps,
            status=TaskStatus.PENDING.value,
            created_at=datetime.now().isoformat()
        )
        
        self.active_tasks[task.task_id] = task
        return task
    
    def get_plan_summary(self, task: AgentTask) -> str:
        """Generate a human-readable summary of the plan"""
        steps_text = []
        for step in task.steps:
            status_emoji = "⏳" if step.status == "pending" else "✅" if step.status == "completed" else "❌"
            steps_text.append(f"{status_emoji} Step {step.step_number}: {step.description}")
        
        return f"""📋 Task Plan (ID: {task.task_id})

📝 Original Request: "{task.original_message}"

🔢 Steps:
{chr(10).join(steps_text)}

⏳ Status: {task.status}

Shall I execute this plan, sir?"""
    
    def execute_step(self, task_id: str, step_number: int) -> Dict[str, Any]:
        """Execute a single step of a task"""
        task = self.active_tasks.get(task_id)
        if not task:
            return {"success": False, "error": "Task not found"}
        
        step = next((s for s in task.steps if s.step_number == step_number), None)
        if not step:
            return {"success": False, "error": "Step not found"}
        
        # Mark as running
        step.status = TaskStatus.RUNNING.value
        
        # Simulate execution (in production, this would call actual services)
        # TODO: Integrate with real trading APIs, notification services, etc.
        
        step.status = TaskStatus.COMPLETED.value
        step.result = {"executed": True, "timestamp": "2024-01-01T00:00:00"}
        
        return {
            "success": True,
            "step": step_number,
            "result": step.result
        }
    
    def execute_plan(self, task_id: str) -> Dict[str, Any]:
        """Execute all steps of a plan sequentially"""
        task = self.active_tasks.get(task_id)
        if not task:
            return {"success": False, "error": "Task not found"}
        
        task.status = TaskStatus.RUNNING.value
        results = []
        
        for step in task.steps:
            result = self.execute_step(task_id, step.step_number)
            results.append(result)
            
            if not result["success"]:
                task.status = TaskStatus.FAILED.value
                return {
                    "success": False,
                    "task_id": task_id,
                    "failed_at_step": step.step_number,
                    "results": results
                }
        
        task.status = TaskStatus.COMPLETED.value
        return {
            "success": True,
            "task_id": task_id,
            "results": results
        }
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a task"""
        task = self.active_tasks.get(task_id)
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "status": task.status,
            "total_steps": len(task.steps),
            "completed_steps": sum(1 for s in task.steps if s.status == "completed"),
            "steps": [
                {
                    "number": s.step_number,
                    "type": s.step_type,
                    "description": s.description,
                    "status": s.status
                }
                for s in task.steps
            ]
        }


# Global planner instance
_planner = None

def get_planner() -> AgentPlanner:
    """Get or create global agent planner"""
    global _planner
    if _planner is None:
        _planner = AgentPlanner()
    return _planner


async def plan_agent_task(message: str, user_id: str) -> Dict[str, Any]:
    """
    Main entry point for agent task planning.
    Parses message, creates plan, returns summary.
    """
    planner = get_planner()
    
    # Try to parse as agent task
    task = planner.parse_task(message, user_id)
    
    if not task:
        return {
            "is_agent_task": False,
            "response": "That doesn't appear to be a multi-step task, sir. Shall I process it as a regular command?"
        }
    
    # Return plan summary for user confirmation
    summary = planner.get_plan_summary(task)
    
    return {
        "is_agent_task": True,
        "task_id": task.task_id,
        "plan_summary": summary,
        "steps_count": len(task.steps),
        "response": f"I've prepared a {len(task.steps)}-step plan for you, sir.\n\n{summary}"
    }


async def execute_agent_task(task_id: str) -> Dict[str, Any]:
    """Execute a planned agent task"""
    planner = get_planner()
    return planner.execute_plan(task_id)


async def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get status of an agent task"""
    planner = get_planner()
    status = planner.get_task_status(task_id)
    
    if not status:
        return {"success": False, "error": "Task not found"}
    
    return {"success": True, **status}
