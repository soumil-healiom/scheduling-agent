import json
import sqlite3
from langchain_openai import ChatOpenAI
import inspect

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

def get_start_api(intent):
    return intent['api_graph'][0]['api_name']

def get_caller_name():
    # Get the current stack frames
    stack = inspect.stack()
    
    # Check if there is a caller function in the stack
    if len(stack) >= 3:
        caller_frame = stack[2]
        caller_name = caller_frame.function
        return caller_name
    return None

def prompt_llm_with_context(context: dict, prompt: str):
    context_str = json.dumps(context, indent=2)
    prompt = f"Given the following context:\n{context_str}\n\n{prompt}"
    response = llm.invoke(prompt).pretty_repr()
    return response

def select_best_option(text: str, options: list):
    prompt = f"Given the following text: '{text}', which of the following options is the best match?\n\nOptions:\n"
    for idx, option in enumerate(options, 1):
        prompt += f"{idx}. {option}\n"

    prompt += "\nPlease select the best option by number or name."

    response = llm.invoke(prompt).pretty_repr()

    selected_option = None
    for option in options:
        if option.lower() in response.lower():
            selected_option = option
            break

    return selected_option

def construct_question(json_context: dict, target_variable: str, output_type: str = None, output_options: list = None):
    context_str = json.dumps(json_context, indent=2)

    prompt = f"Given the following context:\n{context_str}\n\n"

    prompt += f"Please construct a question to ask the user to obtain the value for '{target_variable}'"
    
    if output_type:
        prompt += f" that is of type '{output_type}'"
    
    if output_options:
        options_str = ', '.join(output_options)
        prompt += f" and should be one of the following options: {options_str}"
    
    prompt += "."

    response = llm.invoke(prompt).pretty_repr()

    return response.strip()

def interpret_response(original_question: str, output_data_type: str, output_options, user_response: str, mistaken_response=None):
    if output_options is None:
        output_options = "Can be anything"
    else:
        output_options = ', '.join(output_options)
    
    
    # TODO - Add a check for mistaken_response and ask the user to provide the correct response if the response is incorrect.
    # TODO - implement a conifidence score to check the LLM's confidence in the response. Set a threshold to ask for user confirmation
    prompt = (
        f"Given the following question and user response, please extract the relevant value.\n\n"
        f"Question: {original_question}\n"
        f"Expected data type: {output_data_type}\n"
        f"Possible options: {output_options}\n"
        f"User response: {user_response}\n\n"
        f"Please provide the extracted value (if possible options are given, make sure that the value exists in the possible options or return 'Not applicable'):"
    )
    
    response = llm.predict(prompt).strip()
    
    if output_data_type == "number":
        print(response)
        try:
            value = float(response)
            return value
        except ValueError:
            return "Invalid response: Unable to extract a valid number."
    
    elif output_data_type == "string":
        return response
    
    elif output_data_type == "list":
        for option in output_options:
            if option.lower() in response.lower():
                return option
        return "Invalid response: Expected one of the options."
    
    else:
        return "Invalid output data type specified."