"""General career Q&A grounded in the RAG knowledge base (reduces hallucination)."""
from app.agents.base import BaseAgent
from app.ai.llm import llm
from app.core.sanitize import wrap_untrusted
from app.profile import engine as profile_engine
from app.rag.retriever import retrieve


class KnowledgeAgent(BaseAgent):
    name = "knowledge"

    def run(self, state) -> dict:
        question = state.get("message", "")
        docs = retrieve(self.db, question, k=4, min_score=0.05)
        if not docs:
            return {"answer": "I don't have enough information in my knowledge base to answer that reliably. "
                              "Try asking about your resume, skill gaps, jobs, a roadmap or interview practice.",
                    "sources": [], "grounded": False}
        sources = [d["title"] for d in docs]
        if llm.available:
            profile = self.profile(state)
            context = "\n".join(f"[{i + 1}] {d['title']}: {d['content']}" for i, d in enumerate(docs))
            system = ("You are CareerCompass, a concise career coach. Answer ONLY from the numbered context. "
                      "If the context does not contain the answer, say so. Cite sources like [1].")
            user = (f"Candidate target role: {profile.target_role or 'unknown'}\nContext:\n{context}\n"
                    f"{wrap_untrusted('QUESTION', question, 1000)}")
            ans = llm.chat(system, user, max_tokens=500)
            if ans:
                return {"answer": ans, "sources": sources, "grounded": True}
        top = docs[0]
        return {"answer": f"{top['title']}: {top['content']}", "sources": sources, "grounded": True}
