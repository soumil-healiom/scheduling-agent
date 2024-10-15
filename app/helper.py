import json
import sqlite3
import datetime
from langchain_openai import ChatOpenAI
import inspect
from agent import Agent
from dateparser import parse
import datetime

# -------------------------- Agent Initialization --------------------------

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

extract_date_instructions = [
    "You are an agent responsible for parsing strings and extracting the relevant information from them.",
    "Extract just the date from the given string",
    "Your response should be a tuple in the form on (type of date, [date 1, date 2])",
    "If the string contains a date range, return both dates",
    "Type of date can be either 'single' or 'range'",
    "The date today is " + str(datetime.datetime.now().date()),
    "The current weekday (using datetime weekday) is " + str(datetime.datetime.now().weekday())
]

date_extraction_agent = Agent(extract_date_instructions)

extract_time_instructions = [
    "You are an agent responsible for parsing strings and extracting the relevant information from them.",
    "Extract just the time from the given string",
    "Your response should be a tuple in the form on (type of time, [time 1, time 2])",
    "If the string contains a time range, return both times",
    "Type of time can be either 'single' or 'range'"
    "If no time could be determined, set the type to 'none' and return an empty list",
]

time_extraction_agent = Agent(extract_time_instructions)


# -------------------------- Helper Functions --------------------------

def extract_date(text):
    resp = eval(date_extraction_agent.call(text))
    date_type = resp[0]
    if date_type == "single":
        return parse(resp[1][0]).date()
    else:
        return False
    
def extract_time(text):
    resp = eval(time_extraction_agent.call(text))
    time_type = resp[0]
    if time_type == "single":
        return parse(resp[1][0]).time()
    else:
        return False

def get_start_api(intent, debug=False):
    if debug:
        print(f"get_start_api called with intent: {intent}")
    return intent['api_graph'][0]

def serialize_datetime_payload(payload, debug=False):
    if debug:
        print(f"serialize_datetime_payload called with payload: {payload}")
    for key, value in payload.items():
        if isinstance(value, datetime.date):
            payload[key] = value.isoformat()  
        elif isinstance(value, datetime.time):
            payload[key] = value.isoformat()  
    if debug:
        print(f"Serialized payload: {payload}")
    return payload

def cast_value(output_data_type, data_validation_response, debug=False):
    if debug:
        print(f"cast_value called with output_data_type: {output_data_type}, data_validation_response: {data_validation_response}")
    try:
        if output_data_type == "datetime.datetime":
            value = datetime.datetime.strptime(data_validation_response, "%Y-%m-%d %H:%M:%S")
        elif output_data_type == "datetime.date":
            value = extract_date(data_validation_response)
        elif output_data_type == "datetime.time":
            value = extract_time(data_validation_response)
        else:
            value = eval(output_data_type)(data_validation_response)
        if debug:
            print(f"Cast value: {value}")
        return value
    except Exception as e:
        if debug:
            print(f"Error casting value: {e}")
        raise ValueError(f"Error casting value: {e}")

def get_caller_name(debug=False):
    stack = inspect.stack()
    if debug:
        print(f"get_caller_name called. Stack length: {len(stack)}")
    if len(stack) >= 3:
        caller_frame = stack[2]
        caller_name = caller_frame.function
        if debug:
            print(f"Caller name: {caller_name}")
        return caller_name
    return None

def prompt_llm_with_instruction(instruction: str, prompt: str, debug=False):
    if debug:
        print(f"prompt_llm_with_instruction called with instruction: {instruction} and prompt: {prompt}")
    full_prompt = f"{instruction}\n\n{prompt}"
    response = llm.invoke(full_prompt).content
    if debug:
        print(f"LLM response: {response}")
    return response

def prompt_llm_with_context(context: dict, prompt: str, debug=False):
    if debug:
        print(f"prompt_llm_with_context called with context: {context} and prompt: {prompt}")
    context_str = json.dumps(context, indent=2)
    full_prompt = f"Given the following context:\n{context_str}\n\n{prompt}"
    response = llm.invoke(full_prompt).content
    if debug:
        print(f"LLM response: {response}")
    return response

def select_best_option(text: str, options: list, debug=False):
    if debug:
        print(f"select_best_option called with text: '{text}' and options: {options}")
    prompt = f"Given the following text: '{text}', which of the following options is the best match?\n\nOptions:\n"
    for idx, option in enumerate(options, 1):
        prompt += f"{idx}. {option}\n"

    prompt += "\nPlease select the best option by number or name."

    response = llm.invoke(prompt).content

    if debug:
        print(f"LLM response for select_best_option: {response}")

    selected_option = None
    for option in options:
        if option.lower() in response.lower():
            selected_option = option
            break

    if debug:
        print(f"Selected option: {selected_option}")

    return selected_option

def construct_question(json_context: dict, target_variable: str, hint: str = None, output_type: str = None, output_options: list = None, debug=False):
    if debug:
        print(f"construct_question called with json_context, (conversation) target_variable: '{target_variable}', output_type: '{output_type}', output_options: {output_options}")
    context_str = json.dumps(json_context, indent=2)

    prompt = f"You are an agent that interacts with users. Given the following context:\n{context_str}\n\n"
    prompt += f"Please construct a question to ask the user to obtain the value for '{target_variable}. Answer with just the question as if you were asking the user directly.'"

    if hint:
        prompt += f"Here is instructions on how you should handle asking this question: '{hint}'"
    
    if output_type:
        prompt += f" that is of type '{output_type}'"
    
    if output_options:
        options_str = ', '.join(output_options)
        prompt += f" and should be one of the following options: {options_str}"
        prompt += "Please list the options for the user in the question. One on each line and number them."

    response = llm.invoke(prompt).content

    # response = prompt_llm_with_instruction("print just the question from this response. if its already just a question then reprint it", response, debug=debug)

    if debug:
        print(f"Constructed question: {response}")

    return response.strip()

def interpret_response(original_question: str, output_data_type: str, output_options, user_response: str, debug=False):
    if debug:
        print(f"interpret_response called with original_question: '{original_question}', output_data_type: '{output_data_type}', output_options: {output_options}, user_response: '{user_response}'")
    if output_options is None:
        output_options = "Can be anything"
    else:
        output_options = ', '.join(map(str, output_options))

    if output_data_type == "datetime.time" or  output_data_type == "datetime.date":
        data_validation_response = user_response
    
    else:
        prompt = (
            f"Given the following question and user response, please extract the relevant value.\n\n"
            f"Question: {original_question}\n"
            f"Expected data type: {output_data_type}\n"
            f"Possible options: {output_options}\n"
            f"User response: {user_response}\n\n"
            f"Please provide the extracted value (if possible options are given, make sure that the value exists in the possible options or return 'Not applicable'):"
        )
        
        response = llm.invoke(prompt).content.strip()

        if debug:
            print(f"LLM response for interpret_response: {response}")

        data_validation_prompt = f""" An LLM has been given a task of data extraction from a string. Your job is to verify the data was extracted correctly.
        You will also be given a data type and a list of possible options for the data (can be None). Make sure that your response fits the data type and is in one of the options.
        Here is the prompt to the LLM: {prompt}
        Here is the response from the LLM: {response}
        Here is the data type: {output_data_type}
        Here are the possible options: {output_options}
        Please make sure that the response is correct and fits the data type and is in the possible options. You MUST provide a output that matches the data type exactly.
        """
        
        data_validation_response = llm.invoke(data_validation_prompt).content.strip()

    if debug:
        print(f"Data validation response: {data_validation_response}")

    try:
        value = cast_value(output_data_type, data_validation_response, debug=debug)
        if debug:
            print(f"Interpreted value: {value}")
        return value
    except Exception as e:
        if debug:
            print(f"Error in interpret_response: {e}")
        return False

def which_next(logic_block, memory):
    res ={}
    
    exec(logic_block)
    
    next_api = res["next_node"]

    if next_api:
        return next_api
    else:
        return None  