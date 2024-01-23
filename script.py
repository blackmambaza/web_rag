"""
web_rag -- RAG from the web -- extention for textgen-webui
Retrieve web data and optionally summarize it, then insert into context.
uses links browser which must be installed.
only tested on linux

TODO:
* use substitution variable for query in url instead of adding at end
* instead of sending whole query, send from keyword to period, then remove from query.
  Prompt: Research super bowl. When is the super bowl?
   -- "super bowl" sent. prompt is "When is the super bowl".
* "Research" key: saves to string in params,
  "Analyse" key: summarizes, then saves
  "Examine" key: doesnt save query, doesn't use saved string, only puts results in context
  "Scan" key: like Examine, but summarized
  "Get" key: followed by url, other params are ignored. saves to context.
  "Summarize" key: like Get, but summarized
  
  Put results in saved string (editable!), then always added to context until cleared
  Results of multiple requests accumulate in string until cleared.
* Clear Research button
* summarize: use chat.generate_chat_prompt on "summarize the following:"+ query-results
  before storing in research string
* button array for multiple keyword/url pairs
"""

import gradio as gr
import pickle
from modules import chat, shared
from modules.chat import generate_chat_prompt
import os
import urllib.parse


try:
    with open('saved_data.pkl', 'rb') as f:
        params = pickle.load(f)
except FileNotFoundError:
    params = {
        "display_name": "Web RAG",
        "activate": False,
        "url":    "https://www.duckduckgo.com/?q=",
        "start":  "[ Next Page > ]",
        "end":    "\n6.   ",
        "space":  "",
        "key":    "www,",
    }
    params.update( {
            "end":   "\n6.   ",
    })

def get_search_context(url, query):
    query = urllib.parse.quote_plus(query)
    if len(params['space']) > 0:
      query.replace("+", params['space'])
    print(f"get_search_context: {url} + {query}")
    search_context = os.popen('links -dump ' + url + query).read()
    start = search_context.find(params['start'])
    if start < 0:
      start = 0
    else:
      start = start + 15
    search_context = search_context[start:]
    end = search_context.find(params['end'])
    if end < 0:
      end = 5000
    search_context = search_context[:end]
    print(f"search_context:\n{search_context}")
    return search_context

def custom_generate_chat_prompt(user_input, state, **kwargs):
    """
    Only used in chat mode.
    """
    user_prompt = user_input
    if params['activate']:
        if user_prompt.startswith(params['key']):
            user_prompt = user_input[4:].strip()
            #search_context = "\nJonn Jonze is the president of Frubaz Corp.\n"
            search_context = get_search_context(params['url'], user_prompt)
            state['context'] = search_context + state['context']
    result = chat.generate_chat_prompt(user_prompt, state, **kwargs)
    return result


def ui():
    """
    Gets executed when the UI is drawn. Custom gradio elements and
    their corresponding event handlers should be defined here.

    To learn about gradio components, check out the docs:
    https://gradio.app/docs/
    """
    with gr.Accordion("Web RAG"):
        with gr.Row():
          activate = gr.Checkbox(value=params['activate'], label='Activate Web RAG')
          clear = gr.Button("Clear Research", elem_classes='refresh-button')
        url = gr.Textbox(value=params['url'], label='Retrieval URL')
        with gr.Row():
            key = gr.Textbox(value=params['key'], label="Key: Text at start of prompt to invoke RAG")
            start = gr.Textbox(value=params['start'], label='Start: Retrieved data capture starts when this text is found')
            end = gr.Textbox(value=params['end'], label='End: Retrieved data capture ends when this text is found')
            space = gr.Textbox(value=params['space'], label="Space: After URL-encoding the query, substitute this for '+'")

    def save():
        with open('saved_data.pkl', 'wb') as f:
            pickle.dump(params, f)
    def update_activate(x):
        params.update({'activate': x})
        save()
    def update_url(x):
        params.update({'url': x})
        save()
    def update_start(x):
        params.update({'start': x})
        save()
    def update_end(x):
        params.update({'end': x})
        save()
    def update_space(x):
        params.update({'space': x})
        save()
    def update_key(x):
        params.update({'key': x})
        save()
    def button_clicked(button_input):
        return f"You clicked the '{button_input}' button."

    clear.click(button_clicked, clear, None)
    activate.change(update_activate, activate, None)
    key.change(update_key, key, None)
    url.change(update_url, url, None)
    start.change(update_start, start, None)
    end.change(update_end, end, None)
    space.change(update_space, space, None)
