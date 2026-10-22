"""
AI Bug Report Analyzer
----------------------
A LangGraph pipeline powered by Gemini that turns a free-form bug
description into a structured bug report.

Workflow:
    START -> bug_analysis -> severity_detection -> root_cause -> format_report -> END
"""

import os
import sys
from typing import List, Literal, TypedDict

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

load_dotenv()

if not os.getenv("GOOGLE_API_KEY"):
    sys.exit("Error: GOOGLE_API_KEY is not set. Add it to a .env file or your environment.")

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0)


# ---------------------------------------------------------------------------
# 1. Graph state: the shared data passed between nodes
# ---------------------------------------------------------------------------
class BugState(TypedDict, total=False):
    bug_description: str      # input
    title: str                # Node 1
    affected_feature: str     # Node 1
    summary: str              # Node 1
    severity: str             # Node 2
    severity_reason: str      # Node 2
    root_causes: List[str]    # Node 3
    final_report: str         # Node 4


# ---------------------------------------------------------------------------
# 2. Structured output schemas (so Gemini returns clean, typed data)
# ---------------------------------------------------------------------------
class BugAnalysis(BaseModel):
    title: str = Field(description="Short, specific bug title (max 12 words)")
    affected_feature: str = Field(description="The feature or component affected")
    summary: str = Field(description="2-3 sentence summary of the issue")


class SeverityResult(BaseModel):
    severity: Literal["Critical", "High", "Medium", "Low"]
    reason: str = Field(description="One or two sentences justifying the severity")


class RootCauses(BaseModel):
    causes: List[str] = Field(description="3-5 plausible root causes, most likely first")


# ---------------------------------------------------------------------------
# 3. Nodes
# ---------------------------------------------------------------------------
def bug_analysis_node(state: BugState) -> BugState:
    """Node 1: extract title, affected feature, and issue summary."""
    analyzer = llm.with_structured_output(BugAnalysis)
    result = analyzer.invoke(
        "You are a QA engineer. Analyze the bug report below and extract a "
        "title, the affected feature, and a concise summary.\n\n"
        f"Bug report:\n{state['bug_description']}"
    )
    return {
        "title": result.title,
        "affected_feature": result.affected_feature,
        "summary": result.summary,
    }


def severity_detection_node(state: BugState) -> BugState:
    """Node 2: classify severity as Critical / High / Medium / Low."""
    classifier = llm.with_structured_output(SeverityResult)
    result = classifier.invoke(
        "Classify the severity of this bug using these definitions:\n"
        "- Critical: data loss, security breach, or system down; no workaround\n"
        "- High: major feature broken for many users; difficult workaround\n"
        "- Medium: feature partially impaired; reasonable workaround exists\n"
        "- Low: cosmetic or minor inconvenience\n\n"
        f"Title: {state['title']}\n"
        f"Affected feature: {state['affected_feature']}\n"
        f"Summary: {state['summary']}\n"
        f"Original description: {state['bug_description']}"
    )
    return {"severity": result.severity, "severity_reason": result.reason}


def root_cause_node(state: BugState) -> BugState:
    """Node 3: suggest possible root causes."""
    suggester = llm.with_structured_output(RootCauses)
    result = suggester.invoke(
        "You are a senior software engineer. Suggest 3-5 possible root causes "
        "for this bug, most likely first. Be specific and technical.\n\n"
        f"Title: {state['title']}\n"
        f"Affected feature: {state['affected_feature']}\n"
        f"Summary: {state['summary']}\n"
        f"Severity: {state['severity']}\n"
        f"Original description: {state['bug_description']}"
    )
    return {"root_causes": result.causes}


def format_report_node(state: BugState) -> BugState:
    """Node 4: assemble a clean, readable report (no LLM call needed)."""
    causes = "\n".join(f"  {i}. {c}" for i, c in enumerate(state["root_causes"], 1))
    line = "=" * 60
    report = (
        f"{line}\n"
        f"BUG REPORT\n"
        f"{line}\n\n"
        f"Title:             {state['title']}\n"
        f"Affected Feature:  {state['affected_feature']}\n"
        f"Severity:          {state['severity'].upper()}\n\n"
        f"Summary:\n  {state['summary']}\n\n"
        f"Severity Rationale:\n  {state['severity_reason']}\n\n"
        f"Possible Root Causes:\n{causes}\n\n"
        f"{line}"
    )
    return {"final_report": report}


# ---------------------------------------------------------------------------
# 4. Build the graph
# ---------------------------------------------------------------------------
def build_graph():
    graph = StateGraph(BugState)

    graph.add_node("bug_analysis", bug_analysis_node)
    graph.add_node("severity_detection", severity_detection_node)
    graph.add_node("root_cause", root_cause_node)
    graph.add_node("format_report", format_report_node)

    graph.add_edge(START, "bug_analysis")
    graph.add_edge("bug_analysis", "severity_detection")
    graph.add_edge("severity_detection", "root_cause")
    graph.add_edge("root_cause", "format_report")
    graph.add_edge("format_report", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# 5. CLI
# ---------------------------------------------------------------------------
def main():
    app = build_graph()

    print("AI Bug Report Analyzer (type 'quit' to exit)\n")
    while True:
        description = input("Describe the bug:\n> ").strip()
        if description.lower() in {"quit", "exit", "q"}:
            break
        if not description:
            print("Please enter a bug description.\n")
            continue

        try:
            result = app.invoke({"bug_description": description})
            print("\n" + result["final_report"] + "\n")
        except Exception as exc:
            print(f"\nSomething went wrong: {exc}\n")


if __name__ == "__main__":
    main()
