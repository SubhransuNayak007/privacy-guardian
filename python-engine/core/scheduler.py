import asyncio
from typing import Dict, Any, List, Callable, Awaitable
import time

class TaskGraph:
    """
    Defines a Directed Acyclic Graph (DAG) of detection and processing tasks.
    Each node represents a specialized model or processing step.
    """
    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
    
    def add_node(self, name: str, func: Callable[[Dict[str, Any]], Awaitable[Any]], dependencies: List[str] = None):
        """
        Adds a node to the execution graph.
        
        Args:
            name: Unique name for the task.
            func: Async function to execute. Takes a shared state dictionary.
            dependencies: List of node names that must complete before this node.
        """
        self.nodes[name] = {
            "func": func,
            "dependencies": dependencies or []
        }

class Scheduler:
    """
    Executes a TaskGraph, running independent tasks in parallel and respecting dependencies.
    """
    def __init__(self, graph: TaskGraph):
        self.graph = graph
        
    async def execute(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the graph with the given initial state (e.g. input image).
        Returns the mutated state containing all results.
        """
        state = initial_state.copy()
        completed = set()
        
        # Events to signal completion of specific tasks
        events = {name: asyncio.Event() for name in self.graph.nodes}
        
        async def worker(name: str, node: Dict[str, Any]):
            # Wait for dependencies
            for dep in node["dependencies"]:
                await events[dep].wait()
            
            # Execute
            try:
                # Pass the shared state so nodes can read/write results
                await node["func"](state)
            except Exception as e:
                state[f"{name}_error"] = str(e)
            finally:
                completed.add(name)
                events[name].set()
                
        tasks = []
        for name, node in self.graph.nodes.items():
            tasks.append(asyncio.create_task(worker(name, node)))
            
        await asyncio.gather(*tasks)
        return state
