import json
import os

from langchain_core.messages import HumanMessage
from typing import Annotated
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from pydantic import BaseModel, Field
from pydantic_core.core_schema import json_or_python_schema
from typing_extensions import TypedDict

from .ingest_restaurants_api import query_neo4j, download_to_db
from .config import settings

neo4j_graph = Neo4jGraph(url=settings.NEO4J_URI, username=settings.NEO4J_USER, password=settings.NEO4J_PASSWORD)

llm = init_chat_model(
    "gpt-5-nano",
    api_key=settings.OPENAI_API_KEY
)


class InputCheck(BaseModel):
    valid: bool = Field(
        ...,
        description='Represent if user input is valid.'
    )


class BooleanAnswer(BaseModel):
    result: bool = Field(
        ...,
        description='Simple boolean result.'
    )


class CityExtraction(BaseModel):
    city: str = Field(
        ...,
        description='city name in local language like "Warszawa" or "München"'
    )


class State(TypedDict):
    messages: Annotated[list, add_messages]
    user_input: str
    user_validation: str | None
    db_check_result: str | None
    next: str | None
    query_db_result: str | None


def check_input_node(state: State):
    print("CHECKING USER INPUT\n\n")
    valid = llm.with_structured_output(InputCheck).invoke(f"""
    You are food assistant validator. You need to check if user input is related to food.
    Check if this user input is valid:
    {state['user_input']}
    """).valid

    if not valid:
        print("❌ USER INPUT IS INVALID\n\n")
        return {
            "next": "end",
            "messages": ["This question is not valid. As only food related questions!"]
        }
    print("✅ USER INPUT IS VALID\n\n")
    return {
        "next": "query_db_node",
        "user_validation": "VALID",
    }


def fit_db_node(state: State):
    print("FITTING NEO4J DATABASE\n\n")
    prompt = f"""
        Extract the city from this message:
        {state["user_input"]}
        """

    result = llm.with_structured_output(CityExtraction).invoke(prompt)

    download_to_db(result.city)


def query_db_node(state: State):
    print("QUERYING TO ANSWER USER\n\n")
    neo4j_graph.refresh_schema()

    chain = GraphCypherQAChain.from_llm(
        llm,
        graph=neo4j_graph,
        validate_cypher=True,
        return_intermediate_steps=True,
        allow_dangerous_requests=True,
        verbose=True
    )

    question = state['user_input']

    result = chain.invoke({"query": question})

    print(json.dumps(result, indent=2))

    contexts = result['intermediate_steps'][1]['context']
    answer = result['result']

    try:
        dataset_files_count = len(os.listdir('./dataset'))
    except:
        dataset_files_count = 0

    path = f'./dataset/{dataset_files_count}.json'
    with open(path, 'w') as f:
        f.write(json.dumps({
            "question": question,
            "contexts": contexts,
            "answer": answer,
        }, indent=2))

    os.chmod(path, 0o777)

    print(f'RESULT: {answer}')

    do_not_know = llm.with_structured_output(BooleanAnswer).invoke(f"""
    Check if this message means "Don't know the answer":
    {answer}
    """).result

    print(f'DO NOT KNOW: {do_not_know}')

    if do_not_know:
        return {
            "messages": [answer],
            "next": "fit_db_node"
        }
    else:
        return {
            "messages": [answer],
            "next": "end"
        }


graph_builder = StateGraph(State)

graph_builder.add_node("check_input_node", check_input_node)
graph_builder.add_node("fit_db_node", fit_db_node)
graph_builder.add_node("query_db_node", query_db_node)
graph_builder.add_node("query_db_node_v2", query_db_node)

graph_builder.add_edge(START, "check_input_node")
graph_builder.add_conditional_edges(
    "check_input_node",
    lambda state: state['next'],
    {"query_db_node": "query_db_node", "end": END}
)
graph_builder.add_conditional_edges(
    "query_db_node",
    lambda state: state['next'],
{"fit_db_node": "fit_db_node", "end": END}
)
graph_builder.add_edge("fit_db_node", "query_db_node_v2")
graph_builder.add_edge("query_db_node_v2", END)

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

        return messages[-1].content
    except Exception as e:
        print("Exception", e)
        return '❌ ERROR'
