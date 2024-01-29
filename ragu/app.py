import os
import sys

from taipy.gui import Gui, State, notify, navigate
import openai
from dotenv import load_dotenv
import logging

from ragu.assistant import Assistant
from ragu.commons.page import Page
from ragu.commons.utils import get_file_name, read_pdf

# Configure logger
logging.basicConfig(format="\n%(asctime)s\n%(message)s", level=logging.INFO, force=True)

client = None
context = "The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly.\n\nHuman: Hello, who are you?\nAI: I am an AI created by OpenAI. How can I help you today? "
conversation = {}
current_user_message = ""
past_conversations = []
selected_conv = None
selected_row = [1]

knowledge_urls = ""
uploaded_files = []
uploaded_files_text = []


def on_init(state: State) -> None:
    """
    Initialize the app.

    Args:
        - state: The current state of the app.
    """
    state.context = "The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly.\n\nHuman: Hello, who are you?\nAI: I am an AI created by OpenAI. How can I help you today? "
    state.current_user_message = ""
    state.past_conversations = []
    state.selected_conv = None
    state.selected_row = [1]


def ask_assistant(state: State, current_user_message) -> None:
    """
    Update the context with the user's message and the AI's response.

    Args:
        - state: The current state of the app.
    """
    # state.context += f"Human: \n {state.current_user_message}\n\n AI:"
    
    answer = state.assistant.ask(current_user_message)
    print(answer)
    # answer = request(state, state.context).replace("\n", "")
    state.context += answer
    state.selected_row = [len(state.conversation["Conversation"]) + 1]
    return answer


def send_message(state: State) -> None:
    """
    Send the user's message to the API and update the context.

    Args:
        - state: The current state of the app.
    """
    assistant: Assistant = state.assistant

    if assistant.is_inappropriate(state.current_user_message):
        notify(state, "error", "Your query was found to violate OpenAI's content policy. Please try a different query.")
        return 
    
    conv = state.conversation._dict.copy()
    conv["Conversation"] += [state.current_user_message]
    state.conversation = conv
    user_question = state.current_user_message
    state.current_user_message = ""
    state.refresh("current_user_message")
    
    notify(state, "info", "Sending message...")
    answer = ask_assistant(state, current_user_message=user_question)
    state.current_user_message = ""
    conv = state.conversation._dict.copy()
    conv["Conversation"] += [answer]
    state.conversation = conv
    notify(state, "success", "Response received!")


def style_conv(state: State, idx: int, row: int) -> str:
    """
    Apply a style to the conversation table depending on the message's author.

    Args:
        - state: The current state of the app.
        - idx: The index of the message in the table.
        - row: The row of the message in the table.

    Returns:
        The style to apply to the message.
    """
    if idx is None:
        return None
    elif idx % 2 == 1:
        return "user_message"
    else:
        return "gpt_message"


def on_exception(state, function_name: str, ex: Exception) -> None:
    """
    Catches exceptions and notifies user in Taipy GUI

    Args:
        state (State): Taipy GUI state
        function_name (str): Name of function where exception occured
        ex (Exception): Exception
    """
    notify(state, "error", f"An error occured in {function_name}: {ex}")

def load_knowledge(state: State):

    a: Assistant = state.assistant
    urls: str = state.knowledge_urls
    files = state.uploaded_files_text

    # logging.info(f"Files looks like this: {files}")


    urls = [] if urls == "" else urls.split("\n")

    if (len(urls) == 0) and (len(files) == 0):
        notify(state, "error", "You did not input any data! Please either upload files or input links, and try again.",
               duration=5000)
        return

    a.initialize_knowledge(urls = urls, file_contents=files)
    
    state.rag_ready = True
    state.refresh("rag_ready")

    state.conversation = {
        "Conversation": [f"Hi! I am Rug. How can I help you today? I have knowledge of your uploaded files: {a.current_knowledge()}"]
    }

    state.refresh("conversation")

    notify(state, "success", "Successfully loaded knowledge into Rug.")

def load_file(state: State):
    a: Assistant = state.assistant
    logging.debug(f"Uploaded files looks like {state.uploaded_files}")

    if type(state.uploaded_files) == list:
        for file in state.uploaded_files:
            text = read_pdf(file)
            state.uploaded_files_text.append(text)
            state.assistant.add_knowledge_source(get_file_name(file))

    elif type(state.uploaded_files) == str:
        text = read_pdf(state.uploaded_files)
        state.uploaded_files_text.append(text)
        state.assistant.add_knowledge_source(get_file_name(state.uploaded_files))

    else:
        raise RuntimeError("File is not being read, please check the logs.")

    state.refresh("uploaded_files_text")
    print(text)

def reset_assistant(state: State):
    new_a = Assistant()
    state.assistant = new_a

    state.knowledge_urls = ""
    state.uploaded_files = []
    state.uploaded_files_text = []
    state.rag_ready=False
    state.conversation = {}

    state.refresh("assistant")
    state.refresh("knowledge_urls")
    state.refresh("uploaded_files")
    state.refresh("uploaded_files_text")
    state.refresh("rag_ready")
    state.refresh("conversation")

    notify(state, "success", "Rug is reset!")


past_prompts = []

homepage = """


<|layout|columns=2 4|

<|part|render=True|class_name=sidebar|
# **Build Your Own RAGs**{: .color-primary} # {: .logo-text}

#### What do you want it to know?

For example, you can input your **lecture notes**, **wikipedia articles**, **documentation for a technology** ... and many more applications!

<br/>

**Links**

<|{knowledge_urls}|input|label=URLs (one each line)|multiline|lines_shown=2|class_name=fullwidth|>

<br/>

**Files**

<|{uploaded_files}|file_selector|label=Select Files|on_action=load_file|extensions=.pdf|multiple|>

<br/>
<br/>

<|Load Knowledge|button|class_name=fullwidth plain|id=reset_app_button|on_action=load_knowledge|>
<br/>
---

#### Reset Rug

<|Reset|button|class_name=plain|id=reset_app_button|on_action=reset_assistant|>
|>


<|part|render=True|class_name=p2 align-item-bottom table|
<|{conversation}|table|style=style_conv|show_all|width=100%|selected={selected_row}|rebuild|>
<|part|class_name=card mt1|render={rag_ready}|
<|{current_user_message}|input|label=Write your message here...|on_action=send_message|class_name=fullwidth|>
|>
|>
|>
"""
def make_menu_item(page: Page) -> str:
    return page.convert_to_taipy_menu_page()

def on_menu(state, action, info):
    page = info["args"][0]
    navigate(state, to=page)

list_of_pages = [Page("home", "Home")]
rag_ready = False
"""
<br/>

<br/>

**Code by [@tommysteryy](https://github.com/tommysteryy)**

Original code can be found [here](https://github.com/xoo-creative/rag-builder).
"""

root_md = """

<|content|>

"""

pages = {
    "/": root_md,
    "home": homepage
}

# stylekit = {
#     "color_background_light": "f5efff",
#     "color_paper_light": "e5d9f2"
# }

if __name__ == "__main__":
    load_dotenv()

    if "OPENAI_API_KEY" in os.environ:
        api_key = os.environ["OPENAI_API_KEY"]
    elif len(sys.argv) > 1:
        api_key = sys.argv[1]
    else:
        raise ValueError(
            "Please provide the OpenAI API key as an environment variable OPENAI_API_KEY or as a command line argument."
        )

    client = openai.Client(api_key=api_key)

    assistant = Assistant()

    Gui(pages=pages).run(title="RAG Builder: Customize Your AI", debug=True, dark_mode=False, use_reloader=True)
