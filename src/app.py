import os
import tempfile
from typing import Any, List, Tuple

from dotenv import load_dotenv
import gradio as gr
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_groq import ChatGroq

from prompts import SYSTEM_PROMPT
from tools import (
    delete_last_workout,
    get_exercise_progress,
    get_last_workout,
    log_workout,
    save_to_md_file,
    save_to_pdf_file,
    save_to_txt_file,
)

load_dotenv()

MODEL = os.environ.get("MODEL", "llama-3.3-70b-versatile")
ASSETS_DIR = os.path.join(os.getcwd(), "assets")
ARLO_ICON_PATH = os.path.join(ASSETS_DIR, "arlo.png")


def build_history_messages(
    history: List[Tuple[str, str]],
) -> List[AIMessage | HumanMessage]:
    """Build a history message list from a list of tuples.

    Args:
        history (List[Tuple[str, str]]): A list of tuples.

    Returns:
        List[AIMessage | HumanMessage]: A history message list.
    """
    messages = []
    for item in history:
        if isinstance(item, dict):
            role = item.get("role")
            content = item.get("content")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        else:
            user_msg, bot_msg = item[:2]
            messages.append(HumanMessage(content=user_msg))
            messages.append(AIMessage(content=bot_msg))
    return messages


def content_to_text(content: Any) -> str:
    """Convert a content of any type to a text string.

    Args:
        content (Any): The content to be converted.

    Returns:
        str: Content converted to text string.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(str(part) for part in content)
    return str(content)


def extract_generated_files(messages: List[Any]) -> List[str]:
    """Return the most recent tool-returned file path (if any).

    Args:
        messages (List[Any]): A list of messages.

    Returns:
        List[str]: A list of file paths.
    """
    found: list[str] = []

    for m in messages or []:
        if not isinstance(m, ToolMessage):
            continue

        # The save tool returns the file path directly
        text = content_to_text(m.content).strip()
        if text and os.path.isfile(text):
            found.append(text)

    return [found[-1]] if found else []


def chat(message: str, history: List) -> Any:
    """Entrypoint function for chat.

    Args:
        message (str): Message to send.
        history (List[Tuple[str, str]]): A list of tuples containing history messages.

    Returns:
        Any: Assistant text, or a dict with `text` and `files`.
    """
    if not os.environ.get("GROQ_API_KEY"):
        return "Missing GROQ_API_KEY environment variable."

    llm = ChatGroq(model=MODEL, temperature=0.3)

    agent = create_agent(
        model=llm,
        tools=[
            save_to_md_file,
            save_to_pdf_file,
            save_to_txt_file,
            log_workout,
            get_exercise_progress,
            get_last_workout,
            delete_last_workout,
        ],
        system_prompt=SYSTEM_PROMPT,
    )

    state_messages = build_history_messages(history)
    state_messages.append(HumanMessage(content=message))

    try:
        result = agent.invoke({"messages": state_messages})
    except Exception as e:
        return f"Unexpected error: {type(e).__name__}: {e}"

    latest_text = ""
    for m in reversed(result["messages"]):
        if isinstance(m, AIMessage):
            candidate = content_to_text(m.content).strip()
            if candidate:
                latest_text = candidate
                break

    final_text = latest_text or "Done."
    files = extract_generated_files(result.get("messages", []))

    if files:
        return {"text": final_text, "files": files}
    return final_text


demo = gr.ChatInterface(
    fn=chat,
    chatbot=gr.Chatbot(
        height=500,
        avatar_images=(
            None,
            ARLO_ICON_PATH if os.path.isfile(ARLO_ICON_PATH) else None,
        ),
    ),
    title="Arlo - Gym and Nutrition Assistant",
    description="Chat with Arlo about workouts, strength/hypertrophy programming, and healthy eating.",
    examples=[
        "Give me a 3-day full-body workout focused on strength.",
        "How many grams of protein should I aim for if I weigh 75 kg and want to get stronger?",
        "Make a simple 1-week meal plan for fat loss with high protein.",
        "What is a good push/pull/legs split for hypertrophy?",
    ],
    save_history=True,
)
demo.saved_conversations.secret = os.environ.get("GRADIO_SECRET")
demo.saved_conversations.storage_key = os.environ.get("GRADIO_STORAGE_KEY")

if __name__ == "__main__":
    gradio_temp = os.environ.get("GRADIO_TEMP_DIR") or tempfile.gettempdir()
    allowed_paths = [gradio_temp, ASSETS_DIR]
    demo.launch(
        server_port=7860,
        allowed_paths=allowed_paths,
        favicon_path=ARLO_ICON_PATH if os.path.isfile(ARLO_ICON_PATH) else None,
    )
