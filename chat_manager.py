import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

load_dotenv()

class ChatManager:
    def __init__(self, model="google/gemini-2.5-flash", k=5):
        self.llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            model=os.getenv("OPENROUTER_MODEL", model)
        )
        self.k = k
        self.history = []
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an intelligent, conversational AI memory agent.\n"
                       "You receive the user's input and some context retrieved from your graph memory.\n"
                       "Provide a natural, conversational response to the user. "
                       "If they asked a question, answer it using ONLY the provided context. "
                       "If they just told you something, acknowledge it warmly.\n"
                       "Context from Memory:\n{context}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}")
        ])
        
        self.chain = self.prompt | self.llm

    def chat(self, user_input: str, context: list[str]) -> str:
        """Generates a conversational response using the provided context."""
        context_str = "\n".join(context) if context else "No relevant context found."
        
        response = self.chain.invoke({
            "input": user_input,
            "context": context_str,
            "chat_history": self.history
        })
        
        response_text = response.content
        
        # Save to memory
        self.history.append(HumanMessage(content=user_input))
        self.history.append(AIMessage(content=response_text))
        
        # Keep only the last K interactions (K * 2 messages)
        if len(self.history) > self.k * 2:
            self.history = self.history[-(self.k * 2):]
            
        return response_text

