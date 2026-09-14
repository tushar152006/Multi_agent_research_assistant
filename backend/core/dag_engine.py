from __future__ import annotations

import asyncio
import inspect
import logging
from dataclasses import dataclass, field
from enum import Enum
from time import monotonic
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowContext:
    """Async-safe workflow state shared by all DAG nodes."""

    results: dict[str, Any] = field(default_factory=dict)
    execution_trace: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    statuses: dict[str, NodeStatus] = field(default_factory=dict)
    errors: dict[str, BaseException] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    async def get(self, key: str, default: Any = None) -> Any:
        async with self._lock:
            return self.results.get(key, default)

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self.results[key] = value

    async def update_metadata(self, key: str, value: Any) -> None:
        async with self._lock:
            self.metadata[key] = value

    async def append_trace(self, event: dict[str, Any]) -> None:
        async with self._lock:
            self.execution_trace.append(event)

    async def set_status(self, name: str, status: NodeStatus) -> None:
        async with self._lock:
            self.statuses[name] = status

    async def set_error(self, name: str, error: BaseException) -> None:
        async with self._lock:
            self.errors[name] = error


@dataclass(slots=True)
class DAGNode:
    name: str
    dependencies: set[str]
    action: Callable[[WorkflowContext], Awaitable[Any]]
    retries: int = 2
    timeout: float = 300.0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Node name cannot be empty")
        if self.retries < 0:
            raise ValueError("retries must be non-negative")
        if self.timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if not callable(self.action):
            raise TypeError("action must be callable")


class DAGEngine:
    def __init__(self) -> None:
        self._nodes: dict[str, DAGNode] = {}

    def add_node(self, node: DAGNode) -> None:
        if node.name in self._nodes:
            raise ValueError(f"Duplicate node name: {node.name}")
        self._nodes[node.name] = node

    def _validate(self) -> list[str]:
        node_names = set(self._nodes)
        for node in self._nodes.values():
            unknown = node.dependencies - node_names
            if unknown:
                raise ValueError(
                    f"Node {node.name!r} has unknown dependencies: {sorted(unknown)}"
                )

        indegree = {name: len(node.dependencies) for name, node in self._nodes.items()}
        dependents: dict[str, set[str]] = {name: set() for name in self._nodes}

        for name, node in self._nodes.items():
            for dependency in node.dependencies:
                dependents[dependency].add(name)

        ready = [name for name, count in indegree.items() if count == 0]
        order: list[str] = []

        while ready:
            current = ready.pop()
            order.append(current)
            for dependent in dependents[current]:
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    ready.append(dependent)

        if len(order) != len(self._nodes):
            raise ValueError("DAG contains a circular dependency")

        return order

    async def _emit(
        self,
        on_event: Callable[[str, dict[str, Any]], Awaitable[None]] | None,
        event_name: str,
        payload: dict[str, Any],
    ) -> None:
        if on_event is None:
            return

        result = on_event(event_name, payload)
        if inspect.isawaitable(result):
            await result

    async def _run_node(
        self,
        node: DAGNode,
        context: WorkflowContext,
        on_event: Callable[[str, dict[str, Any]], Awaitable[None]] | None,
    ) -> None:
        await context.set_status(node.name, NodeStatus.RUNNING)
        started_at = monotonic()

        await self._emit(
            on_event,
            "node_start",
            {"node": node.name, "dependencies": sorted(node.dependencies)},
        )

        last_error: BaseException | None = None

        for attempt in range(node.retries + 1):
            try:
                result = await asyncio.wait_for(node.action(context), node.timeout)
                await context.set(node.name, result)
                await context.set_status(node.name, NodeStatus.COMPLETED)

                event = {
                    "node": node.name,
                    "status": NodeStatus.COMPLETED.value,
                    "attempt": attempt + 1,
                    "duration": monotonic() - started_at,
                }
                await context.append_trace(event)
                await self._emit(on_event, "node_done", event)
                return
            except asyncio.CancelledError:
                raise
            except Exception as error:
                last_error = error
                if attempt >= node.retries:
                    break

                delay = 2**attempt
                await self._emit(
                    on_event,
                    "node_progress",
                    {
                        "node": node.name,
                        "attempt": attempt + 1,
                        "retry_in": delay,
                        "error": repr(error),
                    },
                )
                await asyncio.sleep(delay)

        assert last_error is not None
        await context.set_status(node.name, NodeStatus.FAILED)
        await context.set_error(node.name, last_error)

        event = {
            "node": node.name,
            "status": NodeStatus.FAILED.value,
            "attempts": node.retries + 1,
            "duration": monotonic() - started_at,
            "error": repr(last_error),
        }
        await context.append_trace(event)
        await self._emit(on_event, "node_error", event)
        raise last_error

    async def execute(
        self,
        context: WorkflowContext,
        on_event: Callable[[str, dict[str, Any]], Awaitable[None]] | None = None,
    ) -> WorkflowContext:
        self._validate()

        for name in self._nodes:
            await context.set_status(name, NodeStatus.PENDING)

        pending = set(self._nodes)
        completed: set[str] = set()

        while pending:
            ready = [
                name
                for name in pending
                if self._nodes[name].dependencies <= completed
            ]

            if not ready:
                raise RuntimeError("DAG cannot make progress")

            tasks = [
                asyncio.create_task(
                    self._run_node(self._nodes[name], context, on_event)
                )
                for name in ready
            ]

            try:
                await asyncio.gather(*tasks)
            except Exception:
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

                for name in pending:
                    if name not in ready:
                        await context.set_status(name, NodeStatus.SKIPPED)
                raise

            completed.update(ready)
            pending.difference_update(ready)

        return context
