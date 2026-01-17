from langchain_core.messages import HumanMessage
from typing import Annotated

from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from .config import settings
from langchain.chat_models import init_chat_model

llm = init_chat_model(
    "gpt-5-nano",
    api_key=settings.OPENAI_API_KEY
)


class State(TypedDict):
    messages: Annotated[list, add_messages]


def chatbot(state: State):
    return {"messages": [llm.invoke(state["messages"])]}


graph_builder = StateGraph(State)

graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

checkpointer = MemorySaver()

graph = graph_builder.compile(checkpointer=checkpointer)


def call_graph(message):
    messages = [HumanMessage(content=message)]

    try:
        state = graph.invoke(
            {"messages": messages},
            config={"configurable": {"thread_id": 1}}
        )
        messages = state["messages"]
        return messages[-1].content
    except Exception as e:
        print(e)
        return '❌ ERROR'
