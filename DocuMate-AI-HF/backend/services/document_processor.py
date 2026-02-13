
import io
from pypdf import PdfReader
import re
import tiktoken # For better chunking based on tokens

class DocumentProcessor:
    def __init__(self):
        # Initialize tiktoken for token-based chunking
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
        except Exception:
            self.tokenizer = None # Fallback if tiktoken fails

    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extracts text from a PDF file."""
        reader = PdfReader(io.BytesIO(pdf_content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text

    def chunk_text(self, text: str, max_tokens: int = 500, overlap_tokens: int = 50) -> list[str]:
        """
        Splits text into chunks of a maximum token size with optional overlap.
        Uses tiktoken for more accurate token counting.
        """
        if not text:
            return []

        if not self.tokenizer:
            # Fallback to word-based chunking if tokenizer is not available
            print("Warning: tiktoken not available, falling back to word-based chunking.")
            words = text.split()
            chunks = []
            current_chunk_words = []
            for word in words:
                current_chunk_words.append(word)
                if len(current_chunk_words) > max_tokens: # Rough word count
                    chunks.append(" ".join(current_chunk_words))
                    current_chunk_words = current_chunk_words[-int(overlap_tokens/5):] # Rough overlap
            if current_chunk_words:
                chunks.append(" ".join(current_chunk_words))
            return chunks

        tokens = self.tokenizer.encode(text)
        chunks = []
        current_chunk_tokens = []

        for token in tokens:
            current_chunk_tokens.append(token)
            if len(current_chunk_tokens) >= max_tokens:
                chunks.append(self.tokenizer.decode(current_chunk_tokens))
                # Start new chunk with overlap
                current_chunk_tokens = current_chunk_tokens[-overlap_tokens:]

        if current_chunk_tokens:
            chunks.append(self.tokenizer.decode(current_chunk_tokens))

        return chunks

    def clean_text(self, text: str) -> str:
        """Basic text cleaning (remove extra whitespace, newlines)."""
        text = re.sub(r'\s+', ' ', text).strip()
        return text