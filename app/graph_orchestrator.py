
import json
from operator import add
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END

from app.orchestrator import (
    client,
    MODEL,
    TOOLS,
    AVAILABLE_FUNCTIONS,
    compact_tool_result,
    SYSTEM_PROMPT,
)


# =====================================================
# CONFIGURATION
# =====================================================

MAX_TOOL_ROUNDS = 10

# Tools whose complete results must be preserved.
FULL_RESULT_TOOLS = {
    "workforce_overview",
    "project_staffing_analysis",
    "project_workforce_risks",
    "employee_workload_analysis",
}


# =====================================================
# LANGGRAPH SHARED STATE
# =====================================================

class NexoraState(TypedDict):
    messages: Annotated[list, add]
    iteration: int
    answer: str


# =====================================================
# SUPERVISOR / LLM NODE
# =====================================================

def assistant_node(state: NexoraState):

    # Stop if the maximum tool-call rounds are reached.
    if state["iteration"] >= MAX_TOOL_ROUNDS:

        message = {
            "role": "assistant",
            "content": (
                "The agent reached its tool-call limit. "
                "Please try a more specific question."
            ),
        }

        return {
            "messages": [message],
            "answer": message["content"],
        }

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *state["messages"],
        ],
        tools=TOOLS,
        tool_choice="auto",
        max_tokens=1500,
        temperature=0,
    )

    assistant_message = response.choices[0].message

    message_data = assistant_message.model_dump(
        exclude_none=True
    )

    # If Groq requests tools, return the tool calls
    # to the LangGraph execution flow.
    if assistant_message.tool_calls:

        return {
            "messages": [message_data],
            "iteration": state["iteration"] + 1,
        }

    # Otherwise, return the final response.
    answer = (
        assistant_message.content
        or "No response generated."
    )

    return {
        "messages": [message_data],
        "answer": answer,
    }


# =====================================================
# TOOL EXECUTION NODE
# =====================================================

def tool_node(state: NexoraState):

    last_message = state["messages"][-1]

    tool_messages = []

    for tool_call in last_message.get("tool_calls", []):

        function_name = tool_call["function"]["name"]

        try:
            arguments = json.loads(
                tool_call["function"].get("arguments") or "{}"
            )

        except json.JSONDecodeError:

            tool_messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps({
                    "error": "Invalid JSON arguments supplied by the LLM."
                }),
            })

            continue

        if function_name not in AVAILABLE_FUNCTIONS:

            result = {
                "error": "Unknown tool",
                "tool": function_name,
            }

        else:

            try:
                # Execute the existing Nexora database service.
                raw_result = AVAILABLE_FUNCTIONS[
                    function_name
                ](**arguments)

                # Preserve complete results for selected tools.
                if function_name in FULL_RESULT_TOOLS:

                    result = raw_result

                else:

                    # Compress other large outputs to control
                    # Groq token consumption.
                    result = compact_tool_result(
                        raw_result,
                        max_records=1
                    )

            except Exception as error:

                result = {
                    "error": str(error),
                    "tool": function_name,
                }

        tool_messages.append({
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": json.dumps(
                result,
                default=str
            ),
        })

    return {
        "messages": tool_messages
    }


# =====================================================
# CONDITIONAL ROUTING
# =====================================================

def route_after_assistant(state: NexoraState):

    last_message = state["messages"][-1]

    if last_message.get("tool_calls"):
        return "tools"

    return "end"


# =====================================================
# BUILD NEXORA LANGGRAPH
# =====================================================

builder = StateGraph(NexoraState)

# Register graph nodes.
builder.add_node(
    "assistant",
    assistant_node
)

builder.add_node(
    "tools",
    tool_node
)

# Initial execution.
builder.add_edge(
    START,
    "assistant"
)

# Conditional routing after LLM response.
builder.add_conditional_edges(
    "assistant",
    route_after_assistant,
    {
        "tools": "tools",
        "end": END,
    }
)

# Return tool results to the supervisor.
builder.add_edge(
    "tools",
    "assistant"
)

# Compile graph.
nexora_graph = builder.compile()


# =====================================================
# PUBLIC NEXORA GRAPH INTERFACE
# =====================================================

def ask_nexora_graph(question: str) -> str:

    if not question or not question.strip():
        return "Please enter a valid question."

    initial_state = {
        "messages": [
            {
                "role": "user",
                "content": question.strip(),
            }
        ],
        "iteration": 0,
        "answer": "",
    }

    result = nexora_graph.invoke(initial_state)

    return result.get(
        "answer",
        "No response generated."
    )
