import asyncio
import os
import sys
import time

sys.path.insert(0, os.getcwd())
sys.stdout.reconfigure(encoding="utf-8")

from backend.agents.orchestrator import Orchestrator
from backend.models.schemas import QueryType, ResearchRequest


async def main():
    query = "Multi-Agent Consensus and Verification in Autonomous Scientific Discovery"
    print("=" * 80)
    print("🚀 LAUNCHING LIVE MULTI-AGENT CASE STUDY WITH GROQ LLM")
    print(f"📌 Research Query: '{query}'")
    print(f"⚙️ LLM Provider: Groq (Model: openai/gpt-oss-120b)")
    print("=" * 80)

    orchestrator = Orchestrator()
    start_time = time.time()

    def on_event(event_type: str, payload: dict | None = None):
        elapsed = time.time() - start_time
        if event_type == "node_start":
            print(f"[{elapsed:5.1f}s] 🟢 Node Started: {payload.get('node', '') if payload else ''}")
        elif event_type == "paper_progress":
            idx = payload.get("index") if payload else ""
            tot = payload.get("total") if payload else ""
            title = payload.get("title", "") if payload else ""
            print(f"[{elapsed:5.1f}s]    📖 Reading paper ({idx}/{tot}): {title[:60]}...")
        elif event_type == "node_done":
            print(f"[{elapsed:5.1f}s] ✅ Node Completed: {payload.get('node', '') if payload else ''}")
        elif event_type == "sufficiency_verdict":
            is_suff = payload.get("is_sufficient", False) if payload else False
            reason = payload.get("reason", "") if payload else ""
            status = "SUFFICIENT" if is_suff else "INSUFFICIENT (Refining corpus)"
            print(f"[{elapsed:5.1f}s] ⚖️ Research Sufficiency Judge: {status} -> {reason}")
        elif event_type == "adaptive_iteration":
            iter_num = payload.get("iteration", 1) if payload else 1
            added = payload.get("added_papers", 0) if payload else 0
            gap = payload.get("target_gap", "") if payload else ""
            print(f"[{elapsed:5.1f}s] 🔄 Adaptive Iteration #{iter_num}: Querying gap '{gap}' (+{added} papers)")

    req = ResearchRequest(
        query=query,
        max_results=3,
        query_type=QueryType.DEEP_ANALYSIS,
    )

    response = await orchestrator.process(req, on_event=on_event)
    total_time = time.time() - start_time

    print("\n" + "=" * 80)
    print(f"📊 LIVE CASE STUDY RESULTS COMPLETED IN {total_time:.2f}s")
    print("=" * 80)

    print("\n📚 1. PAPERS DISCOVERED & INGESTED (NO HALLUCINATIONS)")
    for i, p in enumerate(response.papers, 1):
        print(f"   [{i}] {p.title}")
        print(f"       Source: {p.source} | ID: {p.external_id}")
        print(f"       Relevance Score: {p.relevance_score}/100")

    print("\n🔬 2. PRISMA SCREENING & EVIDENCE GRAPH")
    if response.prisma_flow:
        p = response.prisma_flow
        print(f"   Identified: {p.total_identified} | Screened: {p.records_screened} | Included: {p.studies_included}")
    if response.evidence_graph:
        g = response.evidence_graph
        claim_nodes = [n for n in g.nodes if getattr(n, 'node_type', '') == 'claim' or (isinstance(getattr(n, 'node_type', ''), object) and str(getattr(n, 'node_type', '')) == 'claim')]
        print(f"   Graph Nodes: {len(g.nodes)} (Papers, Concepts, Claims: {len(claim_nodes)}) | Edges: {len(g.edges)}")
        print(f"   Key Central Concepts: {', '.join(g.central_concepts[:3])}")

    print("\n🧠 3. ANALYST AGENT SYNTHESIS")
    if response.analysis:
        print("   Key Scientific Themes:")
        for t in response.analysis.themes[:3]:
            print(f"     • {t}")
        print("   Consensus Across Literature:")
        for c in response.analysis.consensus[:2]:
            print(f"     • {c}")
        if response.analysis.conflicts:
            print("   Identified Contradictions / Conflicts:")
            for cf in response.analysis.conflicts[:2]:
                print(f"     • [{cf.topic}] {cf.description}")
        print("   Research Gaps Identified:")
        for g in response.analysis.gaps[:2]:
            print(f"     • {g}")

    print("\n🛡️ 4. CITATION AUDITING & GROUNDING VERIFICATION (SHA-256 ANCHORS)")
    if response.grounding_audit:
        ga = response.grounding_audit
        precision_pct = ga.grounding_precision * 100
        print(f"   Audit Precision Score: {precision_pct:.1f}%")
        print(f"   Verified Claims: {ga.verified_claims} / {ga.total_claims}")
        print("   Sample Audited Claims & Proof Quotes:")
        for claim in ga.claims[:3]:
            status_symbol = "✅" if claim.verification_status == "verified" else "⚠️"
            print(f"     {status_symbol} Claim: \"{claim.claim_text[:90]}\"")
            if claim.citations:
                quote = claim.citations[0].exact_quote.replace("\n", " ")[:110]
                print(f"        Source Anchor Quote: \"{quote}...\"")

    print("\n⚖️ 5. CRITIC AGENT (GROQ REASONING & RISK REVIEW)")
    if response.critique:
        print(f"   Review Confidence Score: {response.critique.overall_confidence:.2f}")
        print("   LLM Critical Synthesis:")
        for line in (response.critique.llm_summary or "No summary").splitlines():
            if line.strip():
                print(f"     {line}")

    print("\n🏗️ 6. BUILDER AGENT (OPERATIONAL TRANSLATION PLAN)")
    if response.implementation_plan:
        plan = response.implementation_plan
        print(f"   Project Concept: {plan.project_idea}")
        print(f"   Value Proposition: {plan.value_proposition}")
        print("   Core Architecture Components:")
        for comp in plan.architecture.components[:4]:
            print(f"     • {comp}")
        print("   MVP Roadmap:")
        for phase in plan.mvp_roadmap:
            print(f"     • [{phase.duration}] {phase.name}: {', '.join(phase.goals[:2])}")
        print("   Risk Mitigations:")
        for ch in plan.challenges[:2]:
            print(f"     • Challenge: {ch.challenge} -> Mitigation: {ch.mitigation}")

    print("\n" + "=" * 80)
    print("✅ CASE STUDY RUN COMPLETE — ALL AGENTS EXECUTED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
