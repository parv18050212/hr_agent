import json
from typing import TypedDict, Annotated, Sequence
from datetime import datetime, timezone
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from datetime import datetime, timedelta # Make sure timedelta is imported
from pydantic import BaseModel

# Import our tools and database logic
from .tools.gmail import SendGmailTool
from .tools.calendar_tool import CreateCalendarEventTool
from .tools.calendar_search import FindFreeSlotsTool
from .config import settings
from .database import SessionLocal
from . import crud, schemas

# 1. Initialize Tools
tools = [
    SendGmailTool(),
    CreateCalendarEventTool(),
    FindFreeSlotsTool(),
]
tool_node = ToolNode(tools)

# 2. Define Agent State (Memory)
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], lambda x, y: x + y]
    job_id: int
    candidate_id: int
    candidate_email: str
    candidate_name: str
    proposed_start_time: str
    proposed_end_time: str

# 3. Define Model and Prompts
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.GOOGLE_API_KEY.get_secret_value(),
    convert_system_message_to_human=True
)

llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = """You are an autonomous HR Recruitment Assistant. Your goal is to process a
candidate who has been deemed a "good fit" (fit_score > 0.7) and get them
to the Human-in-the-Loop (HITL) approval step.

You have access to a set of tools to help you.

**Your workflow is as follows:**

1.  **Find a free time slot:** Use the `find_free_calendar_slot` tool.
    You must start your search from tomorrow.
    
2.  **Propose the interview:** Once you have a free slot, you must call the
    `create_pending_interview` tool. This tool is NOT in your tool list.
    It is a special function. You call it by name in your tool_call.
    **You must pass the 'start_time' and 'end_time' you received from the calendar search.**

3.  **Notify HR:** **IF AND ONLY IF** the `create_pending_interview` tool
    call was successful (it returned a "success: true" message), you must
    then use the `send_gmail` tool to email the HR manager
    (parvagarwal73@gmail.com) to notify them that an interview is pending approval.
    
4.  **If it fails:** If the `create_pending_interview` tool returns an error,
    do NOT send the email. Your job is to stop and report the error.
    
5.  **Conclude:** Once HR is notified (or if you failed), your job is done.
    Respond with a final message summarizing your actions.
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ]
)
agent_runnable = prompt | llm_with_tools

# 4. Define Graph Nodes (Actions)
def call_model(state: AgentState):
    print("\n" + "="*30)
    print("--- 1. AGENT NODE: Calling Model ---")
    messages = state["messages"]
    print(f"--- 1a. AGENT NODE: Input Messages ---\n{messages}\n")
    try:
        response = agent_runnable.invoke({"messages": messages})
        print(f"--- 2. AGENT NODE: Model Response ---\n{response}\n")
        return {"messages": [response]}
    except Exception as e:
        print(f"!!! AGENT NODE ERROR: {e} !!!")
        return {"messages": [AIMessage(content=f"Error: {e}")]} # End graph

def call_tool(state: AgentState):
    print("--- 3. TOOL NODE: Calling Tool ---")
    last_message = state["messages"][-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        print(f"--- 4. TOOL NODE: Found tool calls ---\n{last_message.tool_calls}\n")
        tool_messages = []
        for tool_call in last_message.tool_calls:
            name = tool_call["name"]
            args = tool_call["args"]
            # Custom tool (HITL)
            if name == "create_pending_interview":
                print("--- 4a. TOOL NODE: Calling custom 'create_pending_interview' ---")
                result_msg = call_create_pending_interview(state, args)
                print(f"--- 5. TOOL NODE: Custom tool result ---\n{result_msg.content}\n")
                tool_messages.append(result_msg)
            else:
                # Standard tool lookup & invoke
                print(f"--- 4b. TOOL NODE: Calling standard tool '{name}' ---")
                tool = next((t for t in tools if hasattr(t, "name") and t.name == name), None)
                if tool:
                    response = tool.invoke(args)
                    print(f"--- 5b. TOOL NODE: Standard tool result ---\n{response}\n")
                    tool_messages.append(
                        ToolMessage(
                            content=json.dumps(response),
                            tool_call_id=tool_call["id"]
                        )
                    )
                else:
                    print(f"--- 4c. TOOL NODE: Tool '{name}' not found ---")
                    tool_messages.append(
                        ToolMessage(
                            content=f"Error: Tool '{name}' not found.",
                            tool_call_id=tool_call["id"]
                        )
                    )
        return {"messages": tool_messages}
    print("--- 3a. TOOL NODE: No tool calls found. ---")
    return {}

def call_create_pending_interview(state: AgentState, args: dict):
    print("--- Calling Custom Node: create_pending_interview ---")
    db = SessionLocal()
    try:
        # --- START FIX ---
        # The LLM is sending 'interview_time' and 'interview_duration_minutes'
        # Let's handle that.
        
        start_time_str = args.get("interview_time") or args.get("start_time")
        if not start_time_str:
            raise ValueError("Missing 'start_time' or 'interview_time' argument")
            
        start_time = datetime.fromisoformat(start_time_str)

        if "end_time" in args:
            end_time = datetime.fromisoformat(args["end_time"])
        elif "interview_duration_minutes" in args:
            duration = timedelta(minutes=int(args["interview_duration_minutes"]))
            end_time = start_time + duration
        else:
            raise ValueError("Missing 'end_time' or 'interview_duration_minutes' argument")
        # --- END FIX ---

        # Create the Pydantic schema for CRUD
        interview_schema = schemas.PendingInterviewCreate(
            candidate_id=state["candidate_id"],
            job_id=state["job_id"],
            summary=f"Interview with {state['candidate_name']}",
            proposed_start_time=start_time,
            proposed_end_time=end_time
        )
        
        # Save to database
        db_interview = crud.create_pending_interview(db, interview_schema)
        
        # Update our state memory
        state["proposed_start_time"] = start_time.isoformat()
        state["proposed_end_time"] = end_time.isoformat()
        
        result = {"interview_id": db_interview.interview_id, "status": "pending", "success": True} # Add success flag
        return ToolMessage(
            content=json.dumps(result), 
            tool_call_id=args.get("tool_call_id", "custom_tool_0")
        )
    except Exception as e:
        return ToolMessage(
            content=json.dumps({"error": str(e), "success": False}), # Add success flag
            tool_call_id=args.get("tool_call_id", "custom_tool_0")
        )
    finally:
        db.close()
# 5. Define Graph Edges (Decisions)
def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "call_tool"
    return END

# 6. Build and Compile the Graph
graph = StateGraph(AgentState)
graph.add_node("agent", call_model)
graph.add_node("action", call_tool)
graph.set_entry_point("agent")
graph.add_conditional_edges(
    "agent",
    should_continue,
    {
        "call_tool": "action",
        END: END,
    },
)
graph.add_edge("action", "agent")
app = graph.compile()

def run_approval_workflow(interview_id: int):
    """
    This function is triggered by the HR approval endpoint.
    It books the interview and notifies the candidate.
    """
    print(f"--- Running Approval Workflow for Interview {interview_id} ---")
    db = SessionLocal()
    try:
        # 1. Get interview and candidate details
        interview = crud.get_pending_interview(db, interview_id)
        if not interview or interview.status != 'approved':
            print(f"Error: Interview {interview_id} not found or not in 'approved' state.")
            return

        candidate = crud.get_candidate(db, interview.candidate_id)
        if not candidate:
            print(f"Error: Candidate {interview.candidate_id} not found.")
            return

        print(f"Scheduling interview for {candidate.email}...")

        # 2. Call the CreateCalendarEventTool
        calendar_tool = CreateCalendarEventTool()
        result_json = calendar_tool.invoke({
            "summary": interview.summary,
            "start_time": interview.proposed_start_time.isoformat(),
            "end_time": interview.proposed_end_time.isoformat(),
            "attendees": [candidate.email] # You can add hr.manager@example.com here too
        })
        
        # --- START FIX ---
        # 3. Parse the tool's JSON result to get the Meet link
        print(f"Calendar Event Result: {result_json}")
        meet_link = "A Google Meet link will be in the calendar invite." # Default
        try:
            event_result = json.loads(result_json)
            if isinstance(event_result, dict) and event_result.get("meet_link"):
                meet_link = event_result.get("meet_link")
        except Exception as e:
            print(f"Could not parse calendar tool result: {e}")

        # 4. Create the new, empathetic email template
        email_tool = SendGmailTool()
        
        # Format the time nicely
        interview_time_str = interview.proposed_start_time.strftime('%A, %B %d, %Y at %I:%M %p %Z')
        
        email_body = f"""
        Subject: Congratulations! Your Interview is Scheduled.

        Hi {candidate.name},

        First of all, congratulations! We were incredibly impressed with your application and resume, and we are excited to invite you to the next step of our interview process.

        Your interview has been confirmed for:

        **Date & Time:** {interview_time_str}

        **How to join:** A Google Calendar invite has just been sent to you. Please accept it to confirm. The meeting link is also right here for your convenience:
        **Google Meet Link:** {meet_link}

        We're really looking forward to speaking with you and learning more about your projects and experience.

        If you have any questions or need to reschedule (please let us know at least 24 hours in advance), just reply to this email.

        Best of luck!

        Best regards,
        The Hiring Team
        """
        
        email_result = email_tool.invoke({
            "to": candidate.email,
            "subject": f"Interview Confirmed: {interview.summary}",
            "body": email_body
        })
        # --- END FIX ---
        
        print(f"Candidate Email Result: {email_result}")

        # 5. Update the interview status in DB
        crud.update_interview_status(db, interview_id, "scheduled")
        print(f"--- Approval Workflow for {interview_id} Complete ---")
        
    except Exception as e:
        print(f"Error in approval workflow: {e}")
        crud.update_interview_status(db, interview_id, "error")
    finally:
        db.close()

print("--- LangGraph agent compiled successfully ---")
