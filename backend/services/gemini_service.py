import os
import google.generativeai as genai
from dotenv import load_dotenv
import tiktoken # For token counting

load_dotenv()

class GeminiService:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        genai.configure(api_key=self.api_key)
        self.generative_model = genai.GenerativeModel('gemini-2.0-flash')
        self.embedding_model = 'models/text-embedding-004' # Or 'embedding-001' if 004 is not available/preferred

        # Initialize tiktoken for token counting (approximation for Gemini)
        # Gemini doesn't use OpenAI's tokenizers, but this can give a rough estimate
        # For precise Gemini token counts, you'd use the model's own count_tokens method
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
        except Exception:
            self.tokenizer = None # Fallback if tiktoken fails

    def count_tokens(self, text: str) -> int:
        """Counts tokens in a given text using Gemini's model method."""
        try:
            return self.generative_model.count_tokens(text).total_tokens
        except Exception as e:
            print(f"Warning: Could not get exact Gemini token count: {e}. Falling back to approximation.")
            if self.tokenizer:
                return len(self.tokenizer.encode(text))
            return len(text.split()) # Very rough estimate

    async def generate_summary(self, text: str) -> str:
        """Generates a concise summary of the given text."""
        prompt = f"Summarize the following document concisely, highlighting key points. Keep the summary to a maximum of 200 words:\n\n{text}"
        try:
            response = await self.generative_model.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(max_output_tokens=250) # Set max output tokens
            )
            return response.candidates[0].content.parts[0].text
        except Exception as e:
            print(f"Error generating summary with Gemini: {e}")
            return "Failed to generate summary."

    async def extract_entities(self, text: str) -> list[dict]:
        """Extracts entities (PERSON, ORG, LOC, DATE, MONEY) from the text."""
        prompt = f"""Extract key entities from the following text. For each entity, identify its type (PERSON, ORG, LOC, DATE, MONEY, GPE) and its exact text. Return the entities as a JSON list of objects with 'text' and 'label' keys. If no entities are found, return an empty list.

        Example Format:
        [
            {{"text": "John Doe", "label": "PERSON"}},
            {{"text": "Google", "label": "ORG"}},
            {{"text": "New York", "label": "LOC"}}
        ]

        Text:\n\n{text}
        """
        try:
            response = await self.generative_model.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(response_mime_type="application/json") # Request JSON output
            )
            # Gemini might return a string that needs parsing
            json_string = response.candidates[0].content.parts[0].text
            import json
            return json.loads(json_string)
        except Exception as e:
            print(f"Error extracting entities with Gemini: {e}")
            return []

    async def generate_answer(self, question: str, context: str) -> str:
        """Generates an answer to a question based on provided context."""
        prompt = f"""Based on the following context, answer the question. If the answer is not explicitly present in the context, state that you don't know or that the information is not available. Do not make up information.

        Context:
        {context}

        Question: {question}

        Answer:
        """
        try:
            response = await self.generative_model.generate_content_async(prompt)
            return response.candidates[0].content.parts[0].text
        except Exception as e:
            print(f"Error generating answer with Gemini: {e}")
            return "I apologize, but I couldn't generate an answer at this time."

    async def get_embedding(self, text: str) -> list[float]:
        """Generates an embedding vector for the given text."""
        try:
            response = await genai.embed_content_async(
                model=self.embedding_model,
                content=text,
                task_type="RETRIEVAL_DOCUMENT" # Or "RETRIEVAL_QUERY" for queries
            )
            return response['embedding']
        except Exception as e:
            print(f"Error generating embedding with Gemini: {e}")
            raise
