import os
import sys

from taipy.gui import Gui, State, notify, navigate
import openai
from dotenv import load_dotenv
import logging

from rag_builder.assistant import Assistant
from rag_builder.commons.page import Page
from rag_builder.commons.utils import read_pdf

# Configure logger
logging.basicConfig(format="\n%(asctime)s\n%(message)s", level=logging.DEBUG, force=True)

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


def request(state: State, prompt: str) -> str:
    """
    Send a prompt to the GPT-3 API and return the response.

    Args:
        - state: The current state of the app.
        - prompt: The prompt to send to the API.

    Returns:
        The response from the API.
    """
    response = state.client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": f"{prompt}",
            }
        ],
        model="gpt-3.5-turbo",
    )
    return response.choices[0].message.content


def update_context(state: State) -> None:
    """
    Update the context with the user's message and the AI's response.

    Args:
        - state: The current state of the app.
    """
    # state.context += f"Human: \n {state.current_user_message}\n\n AI:"
    answer = state.assistant.ask(state.current_user_message)
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
    notify(state, "info", "Sending message...")
    answer = update_context(state)
    conv = state.conversation._dict.copy()
    conv["Conversation"] += [state.current_user_message, answer]
    state.current_user_message = ""
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


def reset_chat(state: State) -> None:
    """
    Reset the chat by clearing the conversation.

    Args:
        - state: The current state of the app.
    """
    state.past_conversations = state.past_conversations + [
        [len(state.past_conversations), state.conversation]
    ]
    state.conversation = {
        "Conversation": ["Who are you?", "Hi! I am GPT-3. How can I help you today?"]
    }
    gui: Gui = state.get_gui()
    page_index = len(state.list_of_pages)
    page_name = f"New_Conversation_{page_index}"
    page_path = f"conversation_{page_index}"
    gui.add_page(page_path, homepage)
    state.list_of_pages.append(Page(page_path, page_name))

    state.refresh("list_of_pages")



def tree_adapter(item: list) -> [str, str]:
    """
    Converts element of past_conversations to id and displayed string

    Args:
        item: element of past_conversations

    Returns:
        id and displayed string
    """
    identifier = item[0]
    if len(item[1]["Conversation"]) > 3:
        return (identifier, item[1]["Conversation"][2][:50] + "...")
    return (item[0], "Empty conversation")

def load_knowledge(state: State):

    a: Assistant = state.assistant
    urls: str = state.knowledge_urls
    files = state.uploaded_files_text

    logging.info(f"Files looks like this: {files}")


    urls = [] if urls == "" else urls.split(";")

    if (len(urls) == 0) and (len(files) == 0):
        notify(state, "error", "You did not input any data! Please either upload files or input links, and try again.",
               duration=5000)
        return

    a.initialize_knowledge(urls = urls, file_contents=files)
    
    state.rag_ready = True
    state.refresh("rag_ready")

    state.conversation = {
        "Conversation": [f"Hi! I am Rug. How can I help you today? I have knowledge of {a.current_knowledge()}"]
    }

    state.refresh("conversation")

    notify(state, "success", "Agent now knows about the presidential statement!")

def load_file(state: State):
    a: Assistant = state.assistant
    logging.info(f"Uploaded files looks like {state.uploaded_files}")

    if type(state.uploaded_files) == list:
        for file in state.uploaded_files:
            text = read_pdf(file)
            state.uploaded_files_text.append(text)

            filename = os.path.basename(file)
            state.assistant.add_knowledge_source(filename)

    elif type(state.uploaded_files) == str:
        text = read_pdf(state.uploaded_files)
        state.uploaded_files_text.append(text)

        filename = os.path.basename(state.uploaded_files)
        state.assistant.add_knowledge_source(filename)

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

    state.refresh("assistant")
    state.refresh("knowledge_urls")
    state.refresh("uploaded_files")
    state.refresh("uploaded_files_text")
    state.refresh("rag_ready")

    notify(state, "success", "Agent now forgotten about the knowledge you uploaded!")


# def select_conv(state: State, var_name: str, value) -> None:
#     """
#     Selects conversation from past_conversations

#     Args:
#         state: The current state of the app.
#         var_name: "selected_conv"
#         value: [[id, conversation]]
#     """
#     state.conversation = state.past_conversations[value[0][0]][1]
#     state.context = "The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly.\n\nHuman: Hello, who are you?\nAI: I am an AI created by OpenAI. How can I help you today? "
#     for i in range(2, len(state.conversation["Conversation"]), 2):
#         state.context += f"Human: \n {state.conversation['Conversation'][i]}\n\n AI:"
#         state.context += state.conversation["Conversation"][i + 1]
#     state.selected_row = [len(state.conversation["Conversation"]) + 1]


past_prompts = []

homepage = """


<|layout|columns=2 4|

<|part|render=True|class_name=sidebar|
# **Build Your Own RAGs**{: .color-primary} # {: .logo-text}

#### What do you want it to know?

**Links**

<|{knowledge_urls}|input|label=URLs (separated by ';')|multiline|lines_shown=2|class_name=fullwidth|>

<br/>

**Files**

<|{uploaded_files}|file_selector|label=Select File|on_action=load_file|extensions=.csv,.pdf|multiple|>

<br/>
<br/>

<|Load Knowledge|button|class_name=fullwidth plain|id=reset_app_button|on_action=load_knowledge|>
<br/>
---
<br/>
<|Clear Knowledge|button|class_name=fullwidth plain|id=reset_app_button|on_action=reset_assistant|>
|>


<|part|render={rag_ready}|class_name=p2 align-item-bottom table|
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

    Gui(pages=pages).run(debug=True, dark_mode=True, use_reloader=True)
