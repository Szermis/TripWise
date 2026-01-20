from langchain_core.messages import HumanMessage
from typing import Annotated
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from .ingest_restaurants_api import query_neo4j, download_to_db
from .config import settings





URI = "bolt://neo4j:7687"
USER = "neo4j"
PASSWORD = "password123"
neo4j_graph = Neo4jGraph(url=URI, username=USER, password=PASSWORD)

llm = init_chat_model(
    "gpt-5-nano",
    api_key=settings.OPENAI_API_KEY
)

# @tool
# def check_db():
#     """Check if neo4f has any data. Returns count of restaurants or NO_RECORDS"""
#     return query_neo4j(
#         """
#         MATCH (r:Restaurant)
#         RETURN COUNT(r) AS restaurant_count;
#         """
#         # f"""
#         # MATCH (r:Restaurant)
#         # WHERE toLower(r.name) CONTAINS toLower({restaurant})
#         # RETURN r.name AS name, r.cuisine AS cuisine
#         # """
#     )
#
#
# @tool
# def fit_db(city: str) -> str:
#     """
#     Downloads data about given city and saves it in neo4j.
#
#     params:
#     city -> city name in local language like "Warszawa" or "München"
#     """
#     download_to_db(city, "")
# llm_with_tools = llm.bind_tools([check_db, fit_db])


class CityExtraction(BaseModel):
    city: str = Field(
        ...,
        description='city name in local language like "Warszawa" or "München"'
    )


class State(TypedDict):
    messages: Annotated[list, add_messages]
    user_input: str
    db_check_result: str | None
    next: str | None
    query_db_result: str | None


def check_db_node(state: State):
    result = query_neo4j(
        """
        MATCH (r:Restaurant)
        RETURN COUNT(r) AS restaurant_count;
        """
    )
    record = result[0]
    restaurant_count = record["restaurant_count"]
    if restaurant_count == 0:
        return {"db_check_result": "NO_RESULTS"}
    return {"db_check_result": "OK"}


def router(state: State):
    db_check_result = state["db_check_result"]
    if db_check_result == 'NO_RESULTS':
        return {'next': 'fit_db_node'}
    return {'next': 'query_db_node'}


def fit_db_node(state: State):
    print("Fitting neo4j database!\n\n")
    prompt = f"""
        Extract the city from this conversation:
        {state["messages"]}
        """

    result = llm.with_structured_output(CityExtraction).invoke(prompt)

    download_to_db(result.city)


def query_db_node(state: State):
    neo4j_graph.refresh_schema()

    print(neo4j_graph.schema)

    chain = GraphCypherQAChain.from_llm(
        llm, graph=neo4j_graph, verbose=True, allow_dangerous_requests=True
    )

    result = chain.invoke({"query": state['user_input']})
    print(result)
    # return {"query_db_result": result}
    return {"messages": [result['result']]}


def chatbot_node(state: State):
    return {"messages": [llm.invoke(state["messages"])]}


graph_builder = StateGraph(State)

graph_builder.add_node("check_db_node", check_db_node)
graph_builder.add_node("router", router)
graph_builder.add_node("fit_db_node", fit_db_node)
graph_builder.add_node("query_db_node", query_db_node)
graph_builder.add_node("chatbot_node", chatbot_node)

graph_builder.add_edge(START, "check_db_node")
graph_builder.add_edge("check_db_node", "router")
graph_builder.add_conditional_edges(
    "router",
    lambda state: state['next'],
    {"fit_db_node": "fit_db_node", "query_db_node": "query_db_node"}
)
graph_builder.add_edge("fit_db_node", "query_db_node")
# graph_builder.add_edge("query_db_node", "chatbot_node")
graph_builder.add_edge("query_db_node", END)

checkpointer = MemorySaver()

graph = graph_builder.compile(checkpointer=checkpointer)


def call_graph(message):
    messages = [HumanMessage(content=message)]

    try:
        state = graph.invoke(
            {"messages": messages, 'user_input': message},
            config={"configurable": {"thread_id": 1}}
        )
        messages = state["messages"]

        # print(state)
        # print(state['db_check_result'])
        # print(state['query_db_result'])
        return messages[-1].content
    except Exception as e:
        print("Exception", e)
        return '❌ ERROR'
