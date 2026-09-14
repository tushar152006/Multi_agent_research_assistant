import asyncio
import unittest

from backend.core.dag_engine import DAGEngine, DAGNode, NodeStatus, WorkflowContext


class TestDAGEngine(unittest.IsolatedAsyncioTestCase):
    async def test_linear_execution(self):
        engine = DAGEngine()
        output = []

        async def first(ctx):
            output.append("first")
            return 1

        async def second(ctx):
            output.append("second")
            return (await ctx.get("first")) + 1

        engine.add_node(DAGNode("first", set(), first))
        engine.add_node(DAGNode("second", {"first"}, second))

        context = await engine.execute(WorkflowContext())

        self.assertEqual(output, ["first", "second"])
        self.assertEqual(await context.get("second"), 2)

    async def test_parallel_branches(self):
        engine = DAGEngine()
        started = asyncio.Event()
        active = 0
        maximum = 0
        lock = asyncio.Lock()

        async def branch(ctx):
            nonlocal active, maximum
            async with lock:
                active += 1
                maximum = max(maximum, active)
            started.set()
            await asyncio.sleep(0.03)
            async with lock:
                active -= 1

        engine.add_node(DAGNode("a", set(), branch))
        engine.add_node(DAGNode("b", set(), branch))

        await engine.execute(WorkflowContext())
        self.assertTrue(started.is_set())
        self.assertEqual(maximum, 2)

    async def test_cycle_detection(self):
        engine = DAGEngine()

        async def action(ctx):
            return None

        engine.add_node(DAGNode("a", {"b"}, action))
        engine.add_node(DAGNode("b", {"a"}, action))

        with self.assertRaises(ValueError):
            await engine.execute(WorkflowContext())

    async def test_retry(self):
        engine = DAGEngine()
        attempts = 0

        async def action(ctx):
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise RuntimeError("temporary")
            return "ok"

        engine.add_node(DAGNode("retry", set(), action, retries=2))
        context = await engine.execute(WorkflowContext())

        self.assertEqual(attempts, 3)
        self.assertEqual(await context.get("retry"), "ok")

    async def test_timeout(self):
        engine = DAGEngine()

        async def action(ctx):
            await asyncio.sleep(0.1)

        engine.add_node(DAGNode("slow", set(), action, retries=0, timeout=0.01))

        with self.assertRaises(asyncio.TimeoutError):
            await engine.execute(WorkflowContext())

    async def test_event_emission(self):
        engine = DAGEngine()
        events = []

        async def action(ctx):
            return 42

        async def on_event(name, payload):
            events.append((name, payload))

        engine.add_node(DAGNode("eventful", set(), action))
        await engine.execute(WorkflowContext(), on_event)

        self.assertEqual(
            [name for name, _ in events],
            ["node_start", "node_done"],
        )
        self.assertEqual(events[-1][1]["status"], NodeStatus.COMPLETED.value)


if __name__ == "__main__":
    unittest.main()
