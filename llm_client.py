import os
import json
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# --- Schemas for Structured Output ---

class MergeNode(BaseModel):
    operation: Literal["MERGE_NODE"] = "MERGE_NODE"
    label: str = Field(description="The category or type of the entity (e.g., Person, Company, Location). Use simple CamelCase.")
    name: str = Field(description="The unique name of the entity.")
    properties: Optional[Dict[str, Any]] = Field(default={}, description="Additional properties of the entity.")

class MergeRelationship(BaseModel):
    operation: Literal["MERGE_RELATIONSHIP"] = "MERGE_RELATIONSHIP"
    source_name: str = Field(description="Name of the source node.")
    target_name: str = Field(description="Name of the target node.")
    rel_type: str = Field(description="Type of the relationship (e.g., WORKS_AT, FRIEND_WITH). Use UPPER_SNAKE_CASE.")
    properties: Optional[Dict[str, Any]] = Field(default={}, description="Additional properties of the relationship.")

class UpdateRelationship(BaseModel):
    operation: Literal["UPDATE_RELATIONSHIP"] = "UPDATE_RELATIONSHIP"
    source_name: str
    target_name: str
    rel_type: str
    properties: Dict[str, Any] = Field(description="The new properties to set/update on the relationship.")

class DeleteRelationship(BaseModel):
    operation: Literal["DELETE_RELATIONSHIP"] = "DELETE_RELATIONSHIP"
    source_name: str
    target_name: str
    rel_type: str

class RerouteRelationship(BaseModel):
    operation: Literal["REROUTE_RELATIONSHIP"] = "REROUTE_RELATIONSHIP"
    source_name: str
    old_target_name: str
    new_target_name: str
    rel_type: str
    properties: Optional[Dict[str, Any]] = Field(default={})

class GraphOperations(BaseModel):
    operations: List[Dict[str, Any]] = Field(description="A list of operations to perform on the graph. Each operation must match one of the defined schemas.")
    
# --- LLM Client ---

class LLMClient:
    def __init__(self, model="google/gemini-2.5-flash"):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        self.model = os.getenv("OPENROUTER_MODEL", model)

    def extract_graph_operations(self, text: str) -> List[Dict]:
        """Analyzes text and returns a list of graph operations."""
        system_prompt = f"""
You are an expert graph database architect. Your task is to extract information from the user's input and convert it into a sequence of graph operations.

Available operations are:
1. MERGE_NODE: Create or update an entity. (Requires: label, name, optional properties).
2. MERGE_RELATIONSHIP: Create a connection between two entities. (Requires: source_name, target_name, rel_type, optional properties).
3. UPDATE_RELATIONSHIP: Change properties on an existing connection. (Requires: source_name, target_name, rel_type, properties).
4. DELETE_RELATIONSHIP: Remove a connection. (Requires: source_name, target_name, rel_type).
5. REROUTE_RELATIONSHIP: Change the target of a relationship (e.g., someone changed jobs). (Requires: source_name, old_target_name, new_target_name, rel_type, optional properties).

IMPORTANT: 
- You MUST output a JSON object containing an "operations" array.
- Each item in the array must have an "operation" field matching one of the 5 exact names above, along with its required fields.
- Always MERGE_NODE for entities before creating relationships between them!
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Text: {text}\n\nOutput JSON with graph operations:"}
                ],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            print(f"\n[DEBUG] LLM Raw Response:\n{content}\n")
            
            data = json.loads(content)
            return data.get("operations", [])
        except Exception as e:
            print(f"Error calling LLM for extraction: {e}")
            return []

    def extract_entities_for_query(self, query: str) -> List[str]:
        """Extracts just the entity names from a question to fetch graph context."""
        system_prompt = "You are a named entity recognizer. Extract a list of the exact names of entities mentioned in the user's question. Return a JSON object with a single key 'entities' containing a list of strings."
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            return data.get("entities", [])
        except Exception as e:
            print(f"Error extracting entities: {e}")
            return []

    def answer_question(self, query: str, context: List[str]) -> str:
        """Answers a user question based on the provided graph context."""
        context_str = "\\n".join(context) if context else "No relevant context found."
        system_prompt = "You are a helpful AI assistant. Answer the user's question using ONLY the provided graph context. If the context doesn't contain the answer, say you don't know."
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context:\\n{context_str}\\n\\nQuestion: {query}"}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error answering question: {e}")
            return "Sorry, I couldn't process that question."
