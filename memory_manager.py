from llm_client import LLMClient
from graph_db import GraphDB
import logging

logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self):
        self.llm = LLMClient()
        self.db = GraphDB()
        
    def chat(self, user_input: str) -> str:
        """Handles a natural conversation, extracting memories and answering questions."""
        logger.info(f"User Input: '{user_input}'")
        
        # 1. Quickly extract any entities mentioned to pull memory context
        entities = self.llm.extract_entities_for_query(user_input)
        context = self.db.get_context(entities) if entities else []
        if context:
            logger.info(f"Pulled context for {entities}: {len(context)} facts.")
        
        # 2. Let the LLM process the input (extract operations AND generate a conversational response)
        result = self.llm.process_input(user_input, context)
        
        operations = result.get("operations", [])
        response_text = result.get("response", "I'm sorry, I couldn't process that.")
        
        # 3. Apply any operations
        batch_data = []
        for op in operations:
            op_type = op.get("operation")
            
            if op_type == "MERGE_NODE":
                props = op.get("properties", {})
                safe_label = "".join(c for c in op.get("label", "Entity") if c.isalnum()) or "Entity"
                query = f"MERGE (n:`{safe_label}` {{name: $name}}) SET n += $props"
                batch_data.append((op_type, query, {"name": op.get("name"), "props": props}))
                
            elif op_type == "MERGE_RELATIONSHIP":
                props = op.get("properties", {})
                safe_rel = "".join(c for c in op.get("rel_type", "RELATED") if c.isalnum() or c == '_').upper()
                query = f"MATCH (a {{name: $s}}) MATCH (b {{name: $t}}) MERGE (a)-[r:`{safe_rel}`]->(b) SET r += $props"
                batch_data.append((op_type, query, {"s": op.get("source_name"), "t": op.get("target_name"), "props": props}))
                
            elif op_type == "UPDATE_RELATIONSHIP":
                props = op.get("properties", {})
                safe_rel = "".join(c for c in op.get("rel_type", "RELATED") if c.isalnum() or c == '_').upper()
                query = f"MATCH (a {{name: $s}})-[r:`{safe_rel}`]->(b {{name: $t}}) SET r += $props"
                batch_data.append((op_type, query, {"s": op.get("source_name"), "t": op.get("target_name"), "props": props}))
                
            elif op_type == "DELETE_RELATIONSHIP":
                safe_rel = "".join(c for c in op.get("rel_type", "RELATED") if c.isalnum() or c == '_').upper()
                query = f"MATCH (a {{name: $s}})-[r:`{safe_rel}`]->(b {{name: $t}}) DELETE r"
                batch_data.append((op_type, query, {"s": op.get("source_name"), "t": op.get("target_name")}))
                
            elif op_type == "REROUTE_RELATIONSHIP":
                props = op.get("properties", {})
                safe_rel = "".join(c for c in op.get("rel_type", "RELATED") if c.isalnum() or c == '_').upper()
                batch_data.append(("DELETE", f"MATCH (a {{name: $s}})-[r:`{safe_rel}`]->(b {{name: $t}}) DELETE r", {"s": op.get("source_name"), "t": op.get("old_target_name")}))
                batch_data.append(("MERGE", f"MATCH (a {{name: $s}}) MATCH (b {{name: $nt}}) MERGE (a)-[r:`{safe_rel}`]->(b) SET r += $props", {"s": op.get("source_name"), "nt": op.get("new_target_name"), "props": props}))
                
        if batch_data:
            self.db.execute_batch(batch_data)
            logger.info(f"Successfully stored {len(operations)} new facts in memory!")
            
        return response_text
        
    def cleanup(self):
        self.db.close()
