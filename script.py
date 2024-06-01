"""
web_rag -- RAG from the web -- extention for textgen-webui
Retrieve web data and optionally summarize it, then insert into context.
uses links browser which must be installed.
only tested on linux

TODO:
* ?instead of sending whole query, send from keyword to period, then remove from query.
  Prompt: Research super bowl. When is the super bowl?
   -- "super bowl" sent. prompt is "When is the super bowl".
* "Research" key: saves to string in params,
  "Analyse" key: summarizes, then saves
  "Examine" key: doesnt save query, doesn't use saved string, only puts results in context
  "Scan" key: like Examine, but summarized
  "Summarize" key: like Get, but summarized
  
* summarize: use chat.generate_chat_prompt on "summarize the following:"+ query-results
  before storing in research string
* button array for multiple keyword/url pairs

WIP:

DONE:
*  "Get" key: followed by url(s). saves to context.
   prompt: Get https://www.wikipedia.org/wiki/Charles_Martel 
  Put results in saved string (editable!), then always added to context until cleared
  Results of multiple requests accumulate in string until cleared.
* Clear Research button
* use substitution variable for query in url instead of adding at end
"""

import gradio as gr
import pickle
from modules import chat, shared
from modules.chat import generate_chat_prompt
import os
import urllib.parse

# Load or initialize parameters
try:
    with open('web_rag_data.pkl', 'rb') as f:
        params = pickle.load(f)
except FileNotFoundError:
    params = {
        "display_name": "Web RAG",
        "activate": False,
        "get_key": "get",
        "url": "https://lite.duckduckgo.com/lite/?q=%q",
        "start": "[ Next Page > ]",
        "end": "\n6.   ",
        "max": "5000",
        "auto_key": "web,",
        "data": "",
    }
params.update({
    "get_key": "get",
    "auto_key": "web,",
})

# Function to retrieve search context from the web
def get_search_context(url, query):
    if len(query) > 0:
        print(f"query={query}")
        query = urllib.parse.quote_plus(query)
        if '%q' in url:
            url = url.replace('%q', query)
    print(f"get_search_context: url={url}")
    search_context = os.popen('links -dump ' + url).read()
    if len(params['start']) > 0:
        start = search_context.find(params['start'])
        start = start + len(params['start']) if start >= 0 else 0
        search_context = search_context[start:]
    if len(params['end']) > 0:
        end = search_context.find(params['end'])
        end = end if end >= 0 else int(params['max'])
    else:
        end = int(params['max'])
    search_context = search_context[:end]
    return search_context

# Function to save parameters to a file
def save():
    with open('web_rag_data.pkl', 'wb') as f:
        pickle.dump(params, f)

# Custom prompt generator for chat
def custom_generate_chat_prompt(user_input, state, **kwargs):
    user_prompt = user_input
    if params['activate']:
        retrieved = ""
        parts = user_prompt.split(" ", 1)
        if len(parts) > 1:
            key = parts[0].lower()
            if key == params['auto_key'].lower():
                user_prompt = parts[1].strip()
                retrieved = get_search_context(params['url'], user_prompt)
            elif key == params['get_key'].lower():
                url = parts[1].strip()
                retrieved = get_search_context(url, "")
                total = len(retrieved) + len(params['data'])
                user_prompt = f'Say "Retrieved {len(retrieved)} characters." and "Total is {total}".'
        data = params['data'] + retrieved
        if len(retrieved) > 0:
            print(f"Retrieved {len(retrieved)}, total: {len(data)}")
            params.update({'data': data})
            save()
        context = data + state.get('context', '')
        state.update({'context': context})
    result = chat.generate_chat_prompt(user_prompt, state, **kwargs)
    return result

# UI definition
def ui():
    with gr.Accordion("Web Retrieval-Augmented Generation - Retrieve data from web pages and insert into context", open=True):
        activate = gr.Checkbox(value=params['activate'], label='Activate Web RAG')
        with gr.Accordion("Keys for Prompt Start", open=True):
            with gr.Row():
                with gr.Column():
                    key = gr.Textbox(value=params['auto_key'], label="AUTO: Key text for Auto-RAG.")
                    url = gr.Textbox(value=params['url'], label='URL template: %q will be replaced by the prompt')
                get_key = gr.Textbox(value=params['get_key'], label="DIRECT: Key text for direct page retrieval.")
        with gr.Row():
            start = gr.Textbox(value=params['start'], label='Start: Data capture starts after this text.')
            end = gr.Textbox(value=params['end'], label='End: Data capture ends before this text.')
            maxchars = gr.Number(value=params['max'], label='Max characters to retrieve if end text not found.')
        with gr.Accordion("Edit Retrieved Data", open=True):
            with gr.Row():
                edit = gr.Button("Show Data")
                clear = gr.Button("Clear Data")
            retrieved = gr.Textbox(value=params['data'], label='Retrieved data')

    def update_activate(x):
        params.update({'activate': x})
        save()

    def update_get_key(x):
        params.update({'get_key': x})
        save()

    def update_maxchars(x):
        params.update({'max': x})
        save()

    def update_start(x):
        params.update({'start': x})
        save()

    def update_end(x):
        params.update({'end': x})
        save()

    def update_url(x):
        params.update({'url': x})
        save()

    def update_key(x):
        params.update({'auto_key': x})
        save()

    def clear_clicked():
        params.update({'data': ""})
        save()
        return ""

    def edit_clicked():
        return params['data']

    def update_retrieved(x):
        params.update({'data': x})
        save()

    activate.change(update_activate)
    get_key.change(update_get_key)
    url.change(update_url)
    maxchars.change(update_maxchars)
    key.change(update_key)
    start.change(update_start)
    end.change(update_end)
    clear.click(clear_clicked, outputs=retrieved)
    edit.click(edit_clicked, outputs=retrieved)
    retrieved.change(update_retrieved)

ui()
