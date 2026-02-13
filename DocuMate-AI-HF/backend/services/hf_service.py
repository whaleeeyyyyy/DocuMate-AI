import os
import asyncio
from typing import List

import httpx
from dotenv import load_dotenv

load_dotenv()


class HuggingFaceService:
    def __init__(self):
        self.api_token = os.environ.get("HF_API_TOKEN")
        if not self.api_token:
            raise ValueError("HF_API_TOKEN environment variable not set.")

        self.base_url = os.environ.get(
            "HF_API_BASE_URL", "https://api-inference.huggingface.co/models"
        ).rstrip("/")

        # Models are configurable via environment variables
        self.summary_model = os.environ.get(
            "HF_SUMMARY_MODEL", "facebook/bart-large-cnn"
        )
        self.qa_model = os.environ.get("HF_QA_MODEL", "deepset/roberta-base-squad2")
        self.embedding_model = os.environ.get(
            "HF_EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2"
        )
        self.ner_model = os.environ.get("HF_NER_MODEL", "dslim/bert-base-NER")

        self.timeout = float(os.environ.get("HF_TIMEOUT", "60"))
        self.max_retries = int(os.environ.get("HF_MAX_RETRIES", "3"))

        # Input size guards to reduce 413/timeout errors on hosted inference
        self.summary_max_chars = int(os.environ.get("HF_SUMMARY_MAX_CHARS", "12000"))
        self.ner_max_chars = int(os.environ.get("HF_NER_MAX_CHARS", "12000"))
        self.qa_max_chars = int(os.environ.get("HF_QA_MAX_CHARS", "8000"))

    async def _post(self, model: str, payload: dict) -> dict | list:
        url = f"{self.base_url}/{model}"
        headers = {"Authorization": f"Bearer {self.api_token}"}

        # Ensure we wait for cold-started models unless explicitly disabled
        options = payload.get("options", {})
        options.setdefault("wait_for_model", True)
        payload["options"] = options

        last_error = None
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for _ in range(self.max_retries):
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 503:
                    try:
                        data = response.json()
                        if isinstance(data, dict) and "estimated_time" in data:
                            await asyncio.sleep(min(10, float(data["estimated_time"])) )
                            continue
                    except Exception:
                        pass
                if response.status_code >= 400:
                    last_error = response.text
                    response.raise_for_status()
                return response.json()

        raise RuntimeError(
            f"Hugging Face inference failed after retries. Last error: {last_error}"
        )

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        if not text:
            return ""
        if len(text) <= max_chars:
            return text
        return text[:max_chars]

    @staticmethod
    def _clean_entity_text(text: str) -> str:
        if not text:
            return ""
        cleaned = text.replace("##", "").replace("▁", "").strip()
        return cleaned

    @staticmethod
    def _map_entity_label(label: str) -> str:
        if not label:
            return "MISC"
        label_upper = label.upper()
        mapping = {
            "PER": "PERSON",
            "PERSON": "PERSON",
            "ORG": "ORG",
            "LOC": "LOC",
            "GPE": "GPE",
            "DATE": "DATE",
            "MONEY": "MONEY",
        }
        return mapping.get(label_upper, label_upper)

    async def generate_summary(self, text: str) -> str:
        text = self._truncate(text, self.summary_max_chars)
        if not text:
            return ""

        payload = {
            "inputs": text,
            "parameters": {
                "max_length": 200,
                "min_length": 40,
                "do_sample": False,
            },
        }
        try:
            response = await self._post(self.summary_model, payload)
            if isinstance(response, list) and response:
                return (
                    response[0].get("summary_text")
                    or response[0].get("generated_text")
                    or ""
                ).strip()
            if isinstance(response, dict) and "summary_text" in response:
                return str(response["summary_text"]).strip()
        except Exception as e:
            print(f"Error generating summary with Hugging Face: {e}")
        return "Failed to generate summary."

    async def extract_entities(self, text: str) -> list[dict]:
        text = self._truncate(text, self.ner_max_chars)
        if not text:
            return []

        payload = {
            "inputs": text,
            "parameters": {
                "aggregation_strategy": "simple",
            },
        }
        try:
            response = await self._post(self.ner_model, payload)
            if not isinstance(response, list):
                return []

            entities = []
            for item in response:
                label = self._map_entity_label(
                    item.get("entity_group") or item.get("entity")
                )
                word = self._clean_entity_text(item.get("word") or item.get("text"))
                if not word:
                    continue
                entities.append(
                    {
                        "text": word,
                        "label": label,
                        "start": item.get("start"),
                        "end": item.get("end"),
                    }
                )
            return entities
        except Exception as e:
            print(f"Error extracting entities with Hugging Face: {e}")
            return []

    async def generate_answer(self, question: str, context: str) -> str:
        if not question:
            return "Please provide a question."

        context = self._truncate(context or "", self.qa_max_chars)
        if not context:
            return (
                "I couldn't find relevant information in the document to answer your question."
            )

        payload = {
            "inputs": {
                "question": question,
                "context": context,
            }
        }
        try:
            response = await self._post(self.qa_model, payload)
            if isinstance(response, list) and response:
                response = response[0]

            if isinstance(response, dict):
                answer = (response.get("answer") or "").strip()
                score = response.get("score")
                if answer and (score is None or score >= 0.2):
                    return answer
        except Exception as e:
            print(f"Error generating answer with Hugging Face: {e}")

        return (
            "I couldn't find relevant information in the document to answer your question."
        )

    async def get_embedding(self, text: str) -> List[float]:
        if not text:
            return []

        payload = {"inputs": text}
        response = await self._post(self.embedding_model, payload)

        # Response can be a list of floats or list of token vectors
        if isinstance(response, list):
            if response and isinstance(response[0], float):
                return response

            if response and isinstance(response[0], list):
                # If nested (token embeddings), mean-pool across tokens
                first_item = response[0]
                if first_item and isinstance(first_item[0], list):
                    # If batched, take the first batch entry
                    response = response[0]

                if response and isinstance(response[0], float):
                    return response

                if response and isinstance(response[0], list) and response[0]:
                    dim = len(response[0])
                    pooled = [0.0] * dim
                    for vec in response:
                        for i, val in enumerate(vec):
                            pooled[i] += float(val)
                    count = float(len(response))
                    return [val / count for val in pooled]

        raise ValueError("Unexpected embedding response shape from Hugging Face")

    async def health_check(self) -> bool:
        try:
            _ = await self.get_embedding("ping")
            return True
        except Exception as e:
            print(f"Hugging Face health check failed: {e}")
            return False
