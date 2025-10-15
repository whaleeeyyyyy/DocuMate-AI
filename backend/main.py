import os
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Path
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import List

# Import services and models
from services.supabase_service import SupabaseService
from services.gemini_service import GeminiService
from services.document_processor import DocumentProcessor
from services.gemini_agent_service import GeminiAgentService # NEW: Import the agent service
from models.requests import QuestionRequest, SemanticSearchRequest, UploadPDFResponse, Entity, AgentQueryRequest, AgentQueryResponse, DocumentListItem

# Load environment variables
load_dotenv()

app = FastAPI(
    title="DocuMate AI Backend",
    description="FastAPI backend for DocuMate AI, integrating Gemini and Supabase.",
    version="0.1.0",
)

# --- CORS Configuration ---
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    # Add your production frontend URL here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Service Initialization ---
# These services are initialized once when the FastAPI app starts
supabase_service = SupabaseService()
gemini_service = GeminiService()
document_processor = DocumentProcessor()
gemini_agent_service = GeminiAgentService(supabase_service, gemini_service) # NEW: Initialize agent service

# --- Dependency for User ID (Placeholder for Auth) ---
async def get_current_user_id():
    """
    Placeholder for user authentication. In a production app, this would
    extract the user ID from a JWT token in the Authorization header.
    """
    dummy_id = os.getenv("DUMMY_USER_ID")
    if not dummy_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DUMMY_USER_ID not set in .env for testing. Please configure it."
        )
    return dummy_id

# --- API Endpoints ---

@app.post("/upload-pdf", response_model=UploadPDFResponse, summary="Upload and Process PDF Document")
async def upload_pdf(
    file: UploadFile = File(..., description="The PDF file to upload and process."),
    user_id: str = Depends(get_current_user_id) # Get user ID from auth
):
    """
    Uploads a PDF document, extracts its text, generates a summary,
    identifies key entities, and prepares it for intelligent Q&A and search.
    All data is stored securely in Supabase.
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file name provided.")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed.")

    try:
        pdf_content = await file.read()
        
        # 1. Extract text from PDF
        extracted_text = document_processor.extract_text_from_pdf(pdf_content)
        cleaned_text = document_processor.clean_text(extracted_text)

        # 2. Upload original PDF to Supabase Storage
        storage_path = await supabase_service.upload_pdf_to_storage(file.filename, pdf_content, user_id)
        
        # 3. Generate Summary and Entities using Gemini concurrently
        # This speeds up the response by running AI tasks in parallel
        summary_task = gemini_service.generate_summary(cleaned_text)
        entities_task = gemini_service.extract_entities(cleaned_text)
        
        summary, raw_entities = await asyncio.gather(summary_task, entities_task)

        # 4. Process raw entities to include start/end positions for frontend highlighting
        processed_entities: List[Entity] = []
        for ent in raw_entities:
            text_to_find = ent.get("text")
            label = ent.get("label")
            if text_to_find and label:
                # Find first occurrence for start/end. This is a basic approach.
                # For more robust NER, consider a dedicated library or more advanced Gemini prompting.
                start_idx = cleaned_text.find(text_to_find)
                if start_idx != -1:
                    processed_entities.append(Entity(
                        text=text_to_find,
                        label=label,
                        start=start_idx,
                        end=start_idx + len(text_to_find)
                    ))
                else:
                    processed_entities.append(Entity(text=text_to_find, label=label))

        # 5. Insert document metadata (including summary and entities) into Supabase DB
        document_id = await supabase_service.insert_document_metadata(
            user_id=user_id,
            filename=file.filename,
            storage_path=storage_path,
            summary=summary,
            entities=[e.model_dump(mode='json') for e in processed_entities] # Store as JSONB
        )

        # 6. Chunk text and generate embeddings for RAG and Semantic Search
        chunks = document_processor.chunk_text(cleaned_text)
        chunk_data_to_insert = []
        for i, chunk_text in enumerate(chunks):
            embedding = await gemini_service.get_embedding(chunk_text)
            chunk_data_to_insert.append({
                "chunk_index": i,
                "chunk_text": chunk_text,
                "embedding": embedding
            })
        await supabase_service.insert_document_chunks(document_id, chunk_data_to_insert)

        return UploadPDFResponse(
            document_id=document_id,
            extracted_text=cleaned_text,
            summary=summary,
            entities=processed_entities
        )

    except Exception as e:
        print(f"Error during PDF upload and processing: {e}")
        # Re-raise as HTTPException to send a proper error response to the client
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process PDF: {e}"
        )

@app.post("/ask-question", summary="Ask a Question about a Document (Direct RAG)")
async def ask_question(
    request: QuestionRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Answers a natural language question about the content of a specific document.
    Utilizes Retrieval Augmented Generation (RAG) for accurate, context-aware answers.
    This endpoint uses a direct RAG approach without the agent's reasoning loop.
    """
    try:
        # 1. Get embedding for the user's question
        query_embedding = await gemini_service.get_embedding(request.question)

        # 2. Retrieve relevant document chunks using vector search from Supabase
        # This is where the 'match_document_chunks' RPC function is called
        relevant_chunks = await supabase_service.get_relevant_chunks(request.document_id, query_embedding)
        
        if not relevant_chunks:
            return {"answer": "I couldn't find relevant information in the document to answer your question. Please try rephrasing or asking a different question."}

        # Combine relevant chunks into a single context string for Gemini
        context = "\n\n".join(relevant_chunks)

        # 3. Generate answer using Gemini, grounded in the retrieved context
        answer = await gemini_service.generate_answer(request.question, context)

        # 4. Save conversation history for future reference
        await supabase_service.save_conversation(user_id, request.document_id, request.question, answer)

        return {"answer": answer}

    except Exception as e:
        print(f"Error during question answering: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to answer question: {e}"
        )

@app.post("/semantic-search", summary="Perform Semantic Search within a Document")
async def semantic_search(
    request: SemanticSearchRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Performs a semantic search within a document based on a natural language query.
    Returns text snippets that are semantically similar to the query.
    """
    try:
        # 1. Get embedding for the search query
        query_embedding = await gemini_service.get_embedding(request.query)

        # 2. Retrieve relevant document chunks using vector search from Supabase
        # For semantic search, we might want more chunks (e.g., top_k=10) than for Q&A context
        relevant_chunks = await supabase_service.get_relevant_chunks(request.document_id, query_embedding, top_k=10)
        
        if not relevant_chunks:
            return {"results": ["No relevant results found for your query in this document."]}

        return {"results": relevant_chunks}

    except Exception as e:
        print(f"Error during semantic search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform semantic search: {e}"
        )

@app.post("/agent-query", response_model=AgentQueryResponse, summary="Ask a Complex Query using Gemini Agent with Tools")
async def agent_query(
    request: AgentQueryRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Processes a complex user query using a Gemini agent that can decide to use
    various tools (e.g., get summary, get entities, semantic search) to formulate an answer.
    """
    try:
        # The agent service handles the entire interaction loop with Gemini and tools
        agent_response = await gemini_agent_service.invoke_agent(request.document_id, request.query)
        
        # Optionally save the agent's final answer to conversation history
        await supabase_service.save_conversation(user_id, request.document_id, request.query, agent_response['answer'])

        return AgentQueryResponse(
            answer=agent_response['answer'],
            tool_calls=agent_response.get('tool_calls'),
            final_prompt=str(agent_response.get('final_prompt')) # Convert history to string for response
        )
    except Exception as e:
        print(f"Error during agent query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process agent query: {e}"
        )

@app.get("/check-gemini", summary="Check Gemini API Status")
async def check_gemini_status():
    """
    Checks if the Gemini API is accessible and functional by making a small test call.
    """
    try:
        # Attempt a very simple, low-cost text generation
        test_prompt = "Say 'hello' in one word."
        response = await gemini_service.generative_model.generate_content_async(
            test_prompt,
            generation_config={"max_output_tokens": 5} # Keep it very short
        )
        # Check if a response was received and has content
        if response and response.candidates and response.candidates[0].content.parts[0].text:
            return {"status": "ok", "message": "Gemini API is working correctly.", "test_response": response.candidates[0].content.parts[0].text.strip()}
        else:
            raise Exception("Gemini API returned an empty or unexpected response.")
    except Exception as e:
        print(f"Gemini API check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gemini API check failed: {e}. Please check your API key and network connection."
        )
    
@app.get("/documents", response_model=List[DocumentListItem], summary="List User's Documents")
async def list_user_documents(
    user_id: str = Depends(get_current_user_id)
):
    """
    Retrieves a list of all documents uploaded by the current user,
    including their ID and filename (title).
    """
    try:
        documents = await supabase_service.get_user_documents(user_id)
        return [DocumentListItem(id=doc['id'], filename=doc['filename']) for doc in documents]
    except Exception as e:
        print(f"Error listing documents for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve documents: {e}"
        )
    
from fastapi import Path

@app.get("/documents/{document_id}", summary="Get document details by ID")
async def get_document_details(
    document_id: str = Path(..., description="Document UUID"),
    user_id: str = Depends(get_current_user_id),
):
    """
    Return full document details (id, filename, content/extracted_text, summary, entities).
    Includes extra logging and a fallback to assemble preview from chunks.
    """
    try:
        print(f"[DEBUG] GET /documents/{document_id} requested by user_id={user_id}")

        # Prefer a helper if present
        doc = None
        if hasattr(supabase_service, "get_document_by_id"):
            try:
                doc = await supabase_service.get_document_by_id(document_id)
                print(f"[DEBUG] supabase_service.get_document_by_id returned: {type(doc)} {str(doc)[:500]}")
            except Exception as e:
                print(f"[ERROR] supabase_service.get_document_by_id raised: {e}")

        # Fallback: query raw if helper not available or returned None
        if not doc:
            try:
                res = supabase_service.client.table("documents").select("*").eq("id", document_id).single().execute()
                print(f"[DEBUG] raw supabase query result type: {type(res)}")
                # log repr of result cautiously (trim long output)
                print(f"[DEBUG] raw supabase query content (truncated): {str(res)[:1000]}")
                # Try common shapes
                if isinstance(res, dict) and res.get("data"):
                    doc = res["data"]
                else:
                    try:
                        data, _ = res
                        if isinstance(data, dict):
                            doc = data
                        elif isinstance(data, list) and len(data) > 0:
                            doc = data[0]
                    except Exception:
                        if hasattr(res, "data"):
                            doc = res.data
            except Exception as e:
                print(f"[ERROR] raw supabase query raised: {e}")

        if not doc:
            # Not found — return 404 with helpful debug note
            print(f"[DEBUG] Document {document_id} not found in database.")
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

        # If we have a row, try to get the content field or assemble from chunks
        content_field = doc.get("content") or doc.get("extracted_text") or doc.get("text") or ""
        if not content_field:
            # try to reconstruct preview from chunks (best-effort)
            try:
                chunks = []
                if hasattr(supabase_service, "get_document_chunks"):
                    chunks = await supabase_service.get_document_chunks(document_id, top_k=10)
                    print(f"[DEBUG] fetched {len(chunks)} chunks via helper")
                else:
                    # raw fallback
                    res_chunks = supabase_service.client.table("document_chunks").select("chunk_text").eq("document_id", document_id).order("chunk_index", {"ascending": True}).limit(10).execute()
                    print(f"[DEBUG] raw chunks query result type: {type(res_chunks)}")
                    # parse shapes
                    if isinstance(res_chunks, dict) and res_chunks.get("data"):
                        chunks = res_chunks["data"]
                    else:
                        try:
                            data, _ = res_chunks
                            chunks = data
                        except Exception:
                            if hasattr(res_chunks, "data"):
                                chunks = res_chunks.data
                if chunks:
                    preview = "\n\n".join([c.get("chunk_text") or c.get("text") or "" for c in chunks])
                    content_field = preview[:20000]
            except Exception as e:
                print(f"[ERROR] failed to assemble preview from chunks: {e}")

        # Normalize and return
        return {
            "id": doc.get("id"),
            "filename": doc.get("filename"),
            "extracted_text": content_field or "",
            "summary": doc.get("summary") or "",
            "entities": doc.get("entities") or []
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Unexpected error in get_document_details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch document details: {e}")
