from llm_client import LLMClient
from graph_db import GraphDB
import logging

logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self):
        self.llm = LLMClient()
        self.db = GraphDB()
        
    def add_memory(self, text: str):
        """Processes new text, extracts operations, and updates the graph."""
        logger.info(f"Adding memory: '{text}'")
        operations = self.llm.extract_graph_operations(text)
        
        if not operations:
            logger.warning("No operations extracted from the text.")
            return

        batch_data = []
        
        for op in operations:
            op_type = op.get("operation")
            
            if op_type == "MERGE_NODE":
                props = op.get("properties", {})
                safe_label = "".join(c for c in op.get("label", "Entity") if c.isalnum()) or "Entity"
                query = f"MERGE (n:`{safe_label}` {{name: $name}}) SET n += $props"
                batch_data.append((op_type, query, {"name": op.get("name"), "props": props}))
                logger.info(f"Queued Node: {op.get('name')}")
                
            elif op_type == "MERGE_RELATIONSHIP":
                props = op.get("properties", {})
                safe_rel = "".join(c for c in op.get("rel_type", "RELATED") if c.isalnum() or c == '_').upper()
                query = f"MATCH (a {{name: $s}}) MATCH (b {{name: $t}}) MERGE (a)-[r:`{safe_rel}`]->(b) SET r += $props"
                batch_data.append((op_type, query, {"s": op.get("source_name"), "t": op.get("target_name"), "props": props}))
                logger.info(f"Queued Rel: {op.get('source_name')} -[{op.get('rel_type')}]-> {op.get('target_name')}")
                
            elif op_type == "UPDATE_RELATIONSHIP":
                props = op.get("properties", {})
                safe_rel = "".join(c for c in op.get("rel_type", "RELATED") if c.isalnum() or c == '_').upper()
                query = f"MATCH (a {{name: $s}})-[r:`{safe_rel}`]->(b {{name: $t}}) SET r += $props"
                batch_data.append((op_type, query, {"s": op.get("source_name"), "t": op.get("target_name"), "props": props}))
                logger.info(f"Queued Update: {op.get('source_name')} -[{op.get('rel_type')}]-> {op.get('target_name')}")
                
            elif op_type == "DELETE_RELATIONSHIP":
                safe_rel = "".join(c for c in op.get("rel_type", "RELATED") if c.isalnum() or c == '_').upper()
                query = f"MATCH (a {{name: $s}})-[r:`{safe_rel}`]->(b {{name: $t}}) DELETE r"
                batch_data.append((op_type, query, {"s": op.get("source_name"), "t": op.get("target_name")}))
                logger.info(f"Queued Delete: {op.get('source_name')} -[{op.get('rel_type')}]-> {op.get('target_name')}")
                
            elif op_type == "REROUTE_RELATIONSHIP":
                props = op.get("properties", {})
                safe_rel = "".join(c for c in op.get("rel_type", "RELATED") if c.isalnum() or c == '_').upper()
                # Delete old
                batch_data.append(("DELETE", f"MATCH (a {{name: $s}})-[r:`{safe_rel}`]->(b {{name: $t}}) DELETE r", {"s": op.get("source_name"), "t": op.get("old_target_name")}))
                # Merge new
                batch_data.append(("MERGE", f"MATCH (a {{name: $s}}) MATCH (b {{name: $nt}}) MERGE (a)-[r:`{safe_rel}`]->(b) SET r += $props", {"s": op.get("source_name"), "nt": op.get("new_target_name"), "props": props}))
                logger.info(f"Queued Reroute: from {op.get('old_target_name')} to {op.get('new_target_name')}")
                
        if batch_data:
            self.db.execute_batch(batch_data)
            logger.info("Successfully executed all operations to Neo4j in a single transaction!")
                
    def ask(self, question: str) -> str:
        """Answers a question based on graph context."""
        logger.info(f"Question: '{question}'")
        entities = self.llm.extract_entities_for_query(question)
        logger.info(f"Extracted entities: {entities}")
        
        context = self.db.get_context(entities)
        logger.info(f"Graph context retrieved: {context}")
        
        answer = self.llm.answer_question(question, context)
        return answer
        
    def cleanup(self):
        self.db.close()
