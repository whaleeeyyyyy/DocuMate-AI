import os
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import List, Dict, Any

load_dotenv()

class SupabaseService:
    def __init__(self):
        self.url: str = os.environ.get("SUPABASE_URL")
        self.key: str = os.environ.get("SUPABASE_KEY")
        if not self.url or not self.key:
            raise ValueError("Supabase URL and Key must be set in environment variables.")
        self.client: Client = create_client(self.url, self.key)

    async def upload_pdf_to_storage(self, file_name: str, file_content: bytes, user_id: str) -> str:
        """Uploads a PDF file to Supabase Storage."""
        try:
            # Store in a user-specific folder
            path_in_storage = f"documents/{user_id}/{file_name}"
            
            # The .upload() method returns an UploadResponse object
            response = self.client.storage.from_("documents").upload(path_in_storage, file_content, {"content-type": "application/pdf"})

            # --- DEBUGGING OUTPUT ---
            # These print statements will help you inspect the 'response' object
            # if you encounter further issues. You can remove them once it's working.
            print(f"DEBUG: Supabase upload response type: {type(response)}")
            print(f"DEBUG: Supabase upload response content: {response}")
            if hasattr(response, '__dict__'):
                print(f"DEBUG: Supabase upload response __dict__: {response.__dict__}")
            # --- END DEBUGGING OUTPUT ---

            # Attempt 1: Check if 'path' is a direct attribute of the response object
            # This is less common for supabase-py v2.x but good to check.
            if hasattr(response, 'path') and response.path:
                return response.path
            
            # Attempt 2: Standard for supabase-py v2.x - check for .data attribute
            # The .data attribute should contain a dictionary with the 'path' key.
            if hasattr(response, 'data') and response.data is not None:
                if isinstance(response.data, dict) and 'path' in response.data:
                    return response.data['path']
            
            # Attempt 3: If the response object itself behaves like a dictionary and has 'path'
            # (Less likely given previous errors, but for completeness)
            if isinstance(response, dict) and 'path' in response:
                return response['path']

            # If none of the above worked, raise an error with detailed info
            raise Exception(f"Failed to get path from Supabase storage upload response. "
                            f"Unexpected response structure. Type: {type(response)}, Content: {response}, "
                            f"Attributes: {response.__dict__ if hasattr(response, '__dict__') else 'N/A'}")

        except Exception as e:
            print(f"Error uploading PDF to Supabase Storage: {e}")
            raise

    async def insert_document_metadata(self, user_id: str, filename: str, storage_path: str,
                                       summary: str = None, entities: list = None, content: str = None) -> str:
        """
        Inserts document metadata into the 'documents' table.
        Now accepts `content` (full extracted text) so the frontend can fetch it directly.
        Returns the newly inserted document's ID.
        """
        try:
            payload = {
                "user_id": user_id,
                "filename": filename,
                "storage_path": storage_path,
                "summary": summary,
                "entities": entities
            }
            # Optionally include content if provided
            if content is not None:
                payload["content"] = content

            res = self.client.table('documents').insert(payload).execute()

            # Try a few response shapes depending on supabase-py version
            # common shapes: { "data": [...], "error": ... }  OR (data, count)
            document_row = None
            if isinstance(res, dict) and res.get("data"):
                # v2-ish
                data = res["data"]
                if isinstance(data, list) and len(data) > 0:
                    document_row = data[0]
            else:
                # tuple-like (data, count)
                try:
                    data, _ = res
                    if isinstance(data, list) and len(data) > 0:
                        document_row = data[0]
                except Exception:
                    # as a last resort, try attributes
                    if hasattr(res, "data") and isinstance(res.data, list) and len(res.data) > 0:
                        document_row = res.data[0]

            if document_row and document_row.get("id"):
                return document_row["id"]

            raise Exception(f"Failed to insert document metadata. Response: {res}")
        except Exception as e:
            print(f"Error inserting document metadata: {e}")
            raise

    async def get_document_by_id(self, document_id: str) -> Dict[str, Any] | None:
        """
        Returns full document row by id. If not found, returns None.
        Handles multiple response shapes returned by different supabase/pysupabase versions.
        """
        try:
            res = self.client.table("documents").select("*").eq("id", document_id).single().execute()

            # If the client returns a SingleAPIResponse (postgrest), it will have .data
            if hasattr(res, "data"):
                # res.data is usually the dict with the row
                return res.data

            # If the client returned dict-like shape
            if isinstance(res, dict) and res.get("data"):
                return res["data"]

            # If the client returned a tuple-like shape (data, count)
            try:
                data, _ = res
                if isinstance(data, dict):
                    return data
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
            except Exception:
                pass

            # As a last resort, check for attribute 'json' or similar
            if hasattr(res, "json"):
                try:
                    parsed = res.json()
                    if isinstance(parsed, dict) and parsed.get("data"):
                        return parsed["data"]
                except Exception:
                    pass

            return None
        except Exception as e:
            print(f"Error fetching document by id {document_id}: {e}")
            raise

    async def get_document_chunks(self, document_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch chunk rows for a given document_id. Returns list of chunk dicts.
        Handles multiple supabase client response shapes.
        """
        try:
            res = self.client.table("document_chunks")\
                .select("*")\
                .eq("document_id", document_id)\
                .order("chunk_index", {"ascending": True})\
                .limit(top_k)\
                .execute()

            if hasattr(res, "data"):
                return res.data if isinstance(res.data, list) else [res.data]

            if isinstance(res, dict) and res.get("data"):
                return res["data"]

            try:
                data, _ = res
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    return [data]
            except Exception:
                pass

            if hasattr(res, "json"):
                try:
                    parsed = res.json()
                    if isinstance(parsed, dict) and parsed.get("data"):
                        return parsed["data"]
                except Exception:
                    pass

            return []
        except Exception as e:
            print(f"Error fetching chunks for document {document_id}: {e}")
            raise


    async def get_document_text_path(self, document_id: str) -> str:
        """Retrieves the extracted text path for a given document ID."""
        # This method would be used if you stored extracted text in storage.
        # Currently, we're assuming extracted text is small enough to be processed directly.
        # If you re-implement storing large extracted text files, this method would be relevant.
        print("Warning: get_document_text_path is called but extracted_text is not stored in storage in current setup.")
        return None # Placeholder

    async def download_text_from_storage(self, path: str) -> str:
        """Downloads text content from Supabase Storage."""
        # This method would be used if you stored extracted text in storage.
        # Currently, we're assuming extracted text is small enough to be processed directly.
        # If you re-implement storing large extracted text files, this method would be relevant.
        print("Warning: download_text_from_storage is called but extracted_text is not stored in storage in current setup.")
        return "" # Placeholder

    async def insert_document_chunks(self, document_id: str, chunks: list[dict]):
        """Inserts document chunks with embeddings into the 'document_chunks' table."""
        try:
            # Ensure chunks have document_id and embedding
            for chunk in chunks:
                chunk['document_id'] = document_id
            data, count = self.client.table('document_chunks').insert(chunks).execute()
            return data
        except Exception as e:
            print(f"Error inserting document chunks: {e}")
            raise

    async def get_relevant_chunks(self, document_id: str, query_embedding: list, top_k: int = 5) -> list[str]:
        """Performs a vector similarity search to find relevant document chunks."""
        try:
            # IMPORTANT: This requires a Supabase RPC function named 'match_document_chunks'
            # to be created in your Supabase SQL Editor.
            # Example RPC SQL:
            # CREATE OR REPLACE FUNCTION match_document_chunks(query_embedding vector(768), match_count int, doc_id uuid)
            # RETURNS TABLE (id uuid, document_id uuid, chunk_text text, similarity float)
            # LANGUAGE plpgsql
            # AS $$
            # BEGIN
            #   RETURN QUERY
            #   SELECT
            #     document_chunks.id,
            #     document_chunks.document_id,
            #     document_chunks.chunk_text,
            #     1 - (document_chunks.embedding <=> query_embedding) AS similarity
            #   FROM document_chunks
            #   WHERE document_chunks.document_id = doc_id
            #   ORDER BY document_chunks.embedding <=> query_embedding
            #   LIMIT match_count;
            # END;
            # $$;

            data, count = self.client.rpc('match_document_chunks', {
                'query_embedding': query_embedding,
                'match_count': top_k,
                'doc_id': document_id
            }).execute()

            if data and data[1]:
                return [item['chunk_text'] for item in data[1]]
            return []
        except Exception as e:
            print(f"Error retrieving relevant chunks from Supabase: {e}")
            # Fallback or raise error
            return []

    async def save_conversation(self, user_id: str, document_id: str, user_message: str, ai_response: str):
        """Saves a conversation turn to the 'conversations' table."""
        try:
            data, count = self.client.table('conversations').insert({
                "user_id": user_id,
                "document_id": document_id,
                "user_message": user_message,
                "ai_response": ai_response
            }).execute()
            return data
        except Exception as e:
            print(f"Error saving conversation: {e}")
            raise

    async def get_user_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieves a list of document IDs and filenames for a given user."""
        try:
            data, count = self.client.table('documents').select('id, filename').eq('user_id', user_id).execute()
            if data and data[1]:
                return data[1] # data[1] contains the list of dictionaries
            return []
        except Exception as e:
            print(f"Error retrieving documents for user {user_id}: {e}")
            raise