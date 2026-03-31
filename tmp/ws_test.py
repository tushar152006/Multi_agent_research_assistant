import asyncio
import json
import websockets


async def test():
    uri = "ws://localhost:8000/ws/research"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({
            "query": "transformer models for NLP",
            "max_results": 3,
            "query_type": "deep_analysis",
        }))
        print("Sent query — waiting for events...")
        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=180)
            frame = json.loads(msg)
            event = frame.get("event")
            data = frame.get("data", {})

            if event in ("agent_start", "agent_done"):
                print(f"  [{event}] {data}")
            elif event == "done":
                report = data
                # Write full report to file for inspection
                with open("tmp/ws_result.json", "w") as f:
                    json.dump(report, f, indent=2)

                print(f"\n=== DONE ===")
                print(f"  session_id     : {report.get('session_id')}")
                print(f"  papers         : {len(report.get('papers', []))}")
                print(f"  reader_outputs : {len(report.get('reader_outputs', []))}")
                analysis = report.get("analysis") or {}
                print(f"  themes         : {analysis.get('themes', [])}")
                print(f"  gaps           : {len(analysis.get('gaps', []))} items")
                critique = report.get("critique") or {}
                print(f"  review_mode    : {critique.get('review_mode')}")
                print(f"  llm_summary    : {str(critique.get('llm_summary', ''))[:120]}")
                print(f"  critiques      : {len(critique.get('critiques', []))} items")
                impl = report.get("implementation_plan") or {}
                print(f"  project_idea   : {str(impl.get('project_idea', ''))[:120]}")
                print(f"  value_prop     : {str(impl.get('value_proposition', ''))[:120]}")
                print(f"\nFull report written to tmp/ws_result.json")
                break
            elif event == "error":
                print(f"ERROR: {data}")
                break


asyncio.run(test())
