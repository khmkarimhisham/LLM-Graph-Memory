import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class GraphDB:
    def __init__(self, uri=None, user=None, password=None):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        
    def close(self):
        self.driver.close()
        
    def execute_query(self, query, parameters=None):
        with self.driver.session() as session:
            try:
                result = session.run(query, parameters)
                return [record for record in result]
            except Exception as e:
                logger.error(f"Failed to execute query: {e}")
                return None
                
    def execute_batch(self, operations_data):
        """Executes multiple graph operations in a single transaction for high performance."""
        def _tx_func(tx):
            for op, query, params in operations_data:
                try:
                    tx.run(query, params)
                except Exception as e:
                    logger.error(f"Failed in batch op {op}: {e}")
        with self.driver.session() as session:
            session.execute_write(_tx_func)
                
    def merge_node(self, label, name, properties=None):
        """Creates or updates a node."""
        props = properties or {}
        # Ensure label is alphanumeric to avoid injection
        safe_label = "".join(c for c in label if c.isalnum()) or "Entity"
        
        query = f"""
        MERGE (n:`{safe_label}` {{name: $name}})
        SET n += $props
        RETURN n
        """
        return self.execute_query(query, {"name": name, "props": props})
        
    def merge_relationship(self, source_name, target_name, rel_type, properties=None):
        """Creates a relationship between two existing nodes if it doesn't exist."""
        props = properties or {}
        safe_rel_type = "".join(c for c in rel_type if c.isalnum() or c == '_').upper()
        
        query = f"""
        MATCH (a {{name: $source_name}})
        MATCH (b {{name: $target_name}})
        MERGE (a)-[r:`{safe_rel_type}`]->(b)
        SET r += $props
        RETURN r
        """
        return self.execute_query(query, {"source_name": source_name, "target_name": target_name, "props": props})
        
    def update_relationship(self, source_name, target_name, rel_type, properties):
        """Modifies properties of an existing relationship."""
        safe_rel_type = "".join(c for c in rel_type if c.isalnum() or c == '_').upper()
        
        query = f"""
        MATCH (a {{name: $source_name}})-[r:`{safe_rel_type}`]->(b {{name: $target_name}})
        SET r += $props
        RETURN r
        """
        return self.execute_query(query, {"source_name": source_name, "target_name": target_name, "props": properties})
        
    def delete_relationship(self, source_name, target_name, rel_type):
        """Removes a relationship completely."""
        safe_rel_type = "".join(c for c in rel_type if c.isalnum() or c == '_').upper()
        
        query = f"""
        MATCH (a {{name: $source_name}})-[r:`{safe_rel_type}`]->(b {{name: $target_name}})
        DELETE r
        """
        return self.execute_query(query, {"source_name": source_name, "target_name": target_name})
        
    def reroute_relationship(self, source_name, old_target_name, new_target_name, rel_type, properties=None):
        """Deletes an old relationship and creates a new one to a different target."""
        self.delete_relationship(source_name, old_target_name, rel_type)
        return self.merge_relationship(source_name, new_target_name, rel_type, properties)
        
    def get_context(self, entities):
        """Retrieves 1-hop neighbors for a list of entity names."""
        if not entities:
            return []
            
        query = """
        MATCH (a)-[r]->(b)
        WHERE a.name IN $entities OR b.name IN $entities
        RETURN a.name AS source, type(r) AS rel_type, b.name AS target, properties(r) AS rel_props
        LIMIT 50
        """
        records = self.execute_query(query, {"entities": entities})
        if not records:
            return []
        
        context = []
        for record in records:
            rel_str = f"{record['source']} -[{record['rel_type']}]-> {record['target']}"
            if record['rel_props']:
                rel_str += f" (Properties: {record['rel_props']})"
            context.append(rel_str)
            
        return context

    def clear_database(self):
        """Utility to wipe the DB for testing."""
        self.execute_query("MATCH (n) DETACH DELETE n")
