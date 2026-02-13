import json
from typing import Dict, Any, Callable

from services.supabase_service import SupabaseService
from services.hf_service import HuggingFaceService


class HuggingFaceAgentService:
    def __init__(self, supabase_service: SupabaseService, hf_service: HuggingFaceService):
        self.supabase_service = supabase_service
        self.hf_service = hf_service

        self.tools: Dict[str, Callable] = {
            "get_document_summary": self._get_document_summary_tool,
            "get_document_entities": self._get_document_entities_tool,
            "semantic_search_document": self._semantic_search_document_tool,
        }

    async def _get_document_summary_tool(self, document_id: str) -> str:
        try:
            res = await self.supabase_service.get_document_by_id(document_id)
            if res and res.get("summary"):
                return res.get("summary")
            return f"No summary found for document ID: {document_id}"
        except Exception as e:
            return f"Error retrieving summary for document ID {document_id}: {e}"

    async def _get_document_entities_tool(self, document_id: str) -> str:
        try:
            res = await self.supabase_service.get_document_by_id(document_id)
            if res and res.get("entities"):
                return json.dumps(res.get("entities"))
            return f"No entities found for document ID: {document_id}"
        except Exception as e:
            return f"Error retrieving entities for document ID {document_id}: {e}"

    async def _semantic_search_document_tool(self, document_id: str, query: str) -> list[str]:
        try:
            query_embedding = await self.hf_service.get_embedding(query)
            return await self.supabase_service.get_relevant_chunks(
                document_id, query_embedding, top_k=5
            )
        except Exception as e:
            print(f"Error performing semantic search for document ID {document_id}: {e}")
            return []

    @staticmethod
    def _format_entities(entities: list[dict]) -> str:
        if not entities:
            return "No entities found."
        lines = []
        for ent in entities:
            label = ent.get("label") or ""
            text = ent.get("text") or ""
            if text:
                lines.append(f"{label}: {text}")
        return "\n".join(lines) if lines else "No entities found."

    @staticmethod
    def _looks_like_question(query: str) -> bool:
        lowered = query.lower()
        return any(
            token in lowered
            for token in ["?", "what", "why", "how", "when", "where", "who", "which"]
        )

    async def invoke_agent(self, document_id: str, user_query: str) -> Dict[str, Any]:
        tool_calls_history = []
        response_parts = []

        query_lower = user_query.lower()
        wants_summary = "summary" in query_lower or "summarize" in query_lower
        wants_entities = "entity" in query_lower or "entities" in query_lower

        if wants_summary:
            tool_calls_history.append(
                {"tool": "get_document_summary", "args": {"document_id": document_id}}
            )
            summary = await self._get_document_summary_tool(document_id)
            response_parts.append(f"Summary:\n{summary}")

        if wants_entities:
            tool_calls_history.append(
                {"tool": "get_document_entities", "args": {"document_id": document_id}}
            )
            raw_entities = await self._get_document_entities_tool(document_id)
            try:
                entities_list = json.loads(raw_entities)
                formatted_entities = self._format_entities(entities_list)
            except Exception:
                formatted_entities = raw_entities
            response_parts.append(f"Entities:\n{formatted_entities}")

        # For general questions, use semantic search + QA
        if not response_parts or self._looks_like_question(user_query):
            tool_calls_history.append(
                {
                    "tool": "semantic_search_document",
                    "args": {"document_id": document_id, "query": user_query},
                }
            )
            chunks = await self._semantic_search_document_tool(document_id, user_query)
            if chunks:
                context = "\n\n".join(chunks)
                answer = await self.hf_service.generate_answer(user_query, context)
                response_parts.append(f"Answer:\n{answer}")
            else:
                response_parts.append(
                    "Answer:\nI couldn't find relevant information in the document."
                )

        return {
            "answer": "\n\n".join(response_parts).strip(),
            "tool_calls": tool_calls_history,
            "final_prompt": None,
        }
