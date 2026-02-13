import os
import json
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv
from typing import List, Dict, Any, Callable

# Import services that the agent's tools will interact with
from services.supabase_service import SupabaseService
from services.gemini_service import GeminiService # For embeddings if needed by tools

load_dotenv()

class GeminiAgentService:
    def __init__(self, supabase_service: SupabaseService, gemini_service: GeminiService):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        genai.configure(api_key=self.api_key)
        
        # Use a model that supports function calling
        self.model = genai.GenerativeModel('gemini-2.0-flash') # gemini-pro supports function calling
        
        self.supabase_service = supabase_service
        self.gemini_service = gemini_service
        
        # Define the tools the agent can use
        self.tools: Dict[str, Callable] = {
            "get_document_summary": self._get_document_summary_tool,
            "get_document_entities": self._get_document_entities_tool,
            "semantic_search_document": self._semantic_search_document_tool,
            # Add other general tools if needed, e.g., calculator, wikipedia, etc.
            # For DocuMate AI, we focus on document-specific tools.
        }
        
        # Register tools with the Gemini model
        self._register_tools_with_model()

    def _register_tools_with_model(self):
        """Registers the Python functions as tools for the Gemini model."""
        # Define the tool schemas for Gemini
        tool_schemas = [
            genai.protos.FunctionDeclaration(
                name="get_document_summary",
                description="Retrieves the pre-generated summary of a specific document.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "document_id": genai.protos.Schema(type=genai.protos.Type.STRING, description="The unique ID of the document.")
                    },
                    required=["document_id"]
                )
            ),
            genai.protos.FunctionDeclaration(
                name="get_document_entities",
                description="Retrieves the pre-generated named entities (PERSON, ORG, LOC, DATE, MONEY, GPE) from a specific document.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "document_id": genai.protos.Schema(type=genai.protos.Type.STRING, description="The unique ID of the document.")
                    },
                    required=["document_id"]
                )
            ),
            genai.protos.FunctionDeclaration(
                name="semantic_search_document",
                description="Performs a semantic search within a document to find relevant text sections based on a query.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "document_id": genai.protos.Schema(type=genai.protos.Type.STRING, description="The unique ID of the document."),
                        "query": genai.protos.Schema(type=genai.protos.Type.STRING, description="The search query or question to find relevant sections.")
                    },
                    required=["document_id", "query"]
                )
            ),
        ]
        
        # Configure the model to use these tools
        self.model = genai.GenerativeModel('gemini-pro', tools=tool_schemas)

    # --- Tool Implementations (wrappers around existing services) ---
    async def _get_document_summary_tool(self, document_id: str) -> str:
        """Retrieves the summary of a document from Supabase."""
        try:
            data, count = await self.supabase_service.client.table('documents').select('summary').eq('id', document_id).single().execute()
            if data and data[1] and data[1]['summary']:
                return data[1]['summary']
            return f"No summary found for document ID: {document_id}"
        except Exception as e:
            return f"Error retrieving summary for document ID {document_id}: {e}"

    async def _get_document_entities_tool(self, document_id: str) -> str:
        """Retrieves the entities of a document from Supabase."""
        try:
            data, count = await self.supabase_service.client.table('documents').select('entities').eq('id', document_id).single().execute()
            if data and data[1] and data[1]['entities']:
                # Return as a JSON string for Gemini to parse
                return json.dumps(data[1]['entities'])
            return f"No entities found for document ID: {document_id}"
        except Exception as e:
            return f"Error retrieving entities for document ID {document_id}: {e}"

    async def _semantic_search_document_tool(self, document_id: str, query: str) -> str:
        """Performs semantic search on document chunks and returns relevant text."""
        try:
            query_embedding = await self.gemini_service.get_embedding(query)
            relevant_chunks = await self.supabase_service.get_relevant_chunks(document_id, query_embedding, top_k=5)
            if relevant_chunks:
                return "Relevant sections:\n" + "\n---\n".join(relevant_chunks)
            return f"No relevant sections found for query '{query}' in document ID: {document_id}"
        except Exception as e:
            return f"Error performing semantic search for document ID {document_id}: {e}"

    # --- Agent Execution Logic ---
    async def invoke_agent(self, document_id: str, user_query: str) -> Dict[str, Any]:
        """
        Invokes the Gemini agent to process a user query, potentially using tools.
        """
        chat = self.model.start_chat(history=[])
        
        # Initial message from the user
        response = await chat.send_message_async(user_query)
        
        tool_calls_history = []

        # Loop to handle tool calls
        while True:
            if response.candidates and response.candidates[0].content.parts:
                part = response.candidates[0].content.parts[0]
                
                # Check if Gemini wants to call a tool
                if part.function_call:
                    tool_call = part.function_call
                    tool_name = tool_call.name
                    tool_args = {k: v for k, v in tool_call.args.items()} # Convert protobuf map to dict

                    print(f"Agent decided to call tool: {tool_name} with args: {tool_args}")
                    tool_calls_history.append({"tool": tool_name, "args": tool_args})

                    if tool_name in self.tools:
                        try:
                            # Pass document_id to tools that need it
                            if 'document_id' in tool_args:
                                tool_args['document_id'] = document_id # Ensure document_id is passed
                            
                            # Execute the tool
                            tool_output = await self.tools[tool_name](**tool_args)
                            print(f"Tool '{tool_name}' output: {tool_output[:100]}...") # Print first 100 chars
                            
                            # Send tool output back to Gemini
                            response = await chat.send_message_async(
                                genai.protos.Part(
                                    function_response=genai.protos.FunctionResponse(
                                        name=tool_name,
                                        response={
                                            "content": tool_output
                                        }
                                    )
                                )
                            )
                        except Exception as e:
                            error_message = f"Error executing tool '{tool_name}': {e}"
                            print(error_message)
                            response = await chat.send_message_async(
                                genai.protos.Part(
                                    function_response=genai.protos.FunctionResponse(
                                        name=tool_name,
                                        response={
                                            "content": error_message
                                        }
                                    )
                                )
                            )
                    else:
                        error_message = f"Agent tried to call unknown tool: {tool_name}"
                        print(error_message)
                        response = await chat.send_message_async(error_message) # Send error back to Gemini
                else:
                    # Gemini provided a final text response
                    final_answer = part.text
                    print(f"Agent final answer: {final_answer}")
                    return {
                        "answer": final_answer,
                        "tool_calls": tool_calls_history,
                        "final_prompt": chat.history # You can inspect the full chat history
                    }
            else:
                # No candidates or content parts, something went wrong or model finished without text
                print("Gemini agent finished without a clear text response or tool call.")
                return {
                    "answer": "I couldn't process that request fully. Please try again.",
                    "tool_calls": tool_calls_history,
                    "final_prompt": chat.history
                }
            
            # Prevent infinite loops in case Gemini gets stuck
            if len(chat.history) > 20: # Arbitrary limit for safety
                print("Agent loop exceeded maximum iterations.")
                return {
                    "answer": "I'm having trouble processing this request. The conversation became too long.",
                    "tool_calls": tool_calls_history,
                    "final_prompt": chat.history
                }