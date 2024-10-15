from helper import *
from api import create_app
import json
import datetime
import requests
from langchain_openai import ChatOpenAI
from agent import Agent
import os
import argparse

# ----------------- Initialize Agents -----------------
# Main user-facing agent
user_initial_instructions = [
    "You are Sam, a Clinic Appointment Scheduling service for a medical clinic.",
    "You can help users schedule a new appointment or reschedule an existing appointment.",
    "Whenever appropriate, mention that the user may choose to quit the service at any time."
]

user_agent = Agent(user_initial_instructions)

# Helper agent for internal logic
helper_initial_instructions = [
    "You are a background AI agent that assists with processing and interpretation of data.",
    "You do not directly interact with the user but help in understanding and preparing data."
]

helper_agent = Agent(helper_initial_instructions)

# ----------------- Constants / Globals -----------------

config = {
    "CONTEXT": {},
    "INSTRUCTIONS": [
        "You are Sam, a Clinic Appointment Scheduling service for a medical clinic.",
        "You can help users schedule a new appointment or reschedule an existing appointment.",
        "Whenever appropriate, mention that the user may choose to quit the service at any time."
    ],
    "AVAILABLE_APIS": {
        "schedule_api": {
            "api_name": "schedule visit",
            "api_path": "api.healion.com/practice_mgmt/schedule",
            "json_arguments": {
                "first name": None,
                "last name": None,
                "reason_for_visit": None,
                "date": None,
                "time_start": None,
                "provider": None
            },
            "json_arguments_schema": {
                "first name": "str",
                "last name": "str",
                "reason_for_visit": "str",
                "date": "datetime.date",
                "time_start": "datetime.time",
                "provider": "str"
            },
            "json_arguments_options": {
                "first name": None,
                "last name": None,
                "reason_for_visit": None,
                "date": None,
                "time_start": None,
                "provider": None
            },
            "json_arguments_expected_format": {
                "first name": "John",
                "last name": "Doe",
                "reason_for_visit": "checkup",
                "date": "2024-07-23",
                "time_start": "09:00:00",
                "provider": "Rishabh Shah"
            },
            "json_arguments_hints": {
                "first name": "You will guide the user through some basic information before selecting a provider to schedule with, starting with their name.",
                "last name": None,
                "reason_for_visit": None,
                "date": None,
                "time_start": None,
                "provider": None
            }
        },
        "reschedule_api": {
            "api_name": "reschedule visit",
            "api_path": "api.healion.com/practice_mgmt/reschedule",
            "json_arguments": {
                "first name": None,
                "last name": None,
                "reason_for_reschedule": None,
                "new_date": None,
                "new_date_end": None,
            },
            "json_arguments_schema": {
                "first name": "str",
                "last name": "str",
                "reason_for_visit": "str",
                "date": "datetime.date",
                "time_start": "datetime.time",
                "duration": "datetime.time",
            },
            "json_arguments_options": {
                "first name": None,
                "last name": None,
                "reason_for_reschedule": None,
                "new_date": None,
                "new_date_end": None,
            },
            "json_arguments_expected_format": {
                "first name": "John",
                "last name": "Doe",
                "reason_for_visit": "checkup",
                "date": "2024-07-23",
                "time_start": "09:00:00",
                "duration": "00:30:00"
            },
            "json_arguments_hints": {
                "first name": "What is your first name?",
                "last name": "What is your last name?",
                "reason_for_reschedule": "What is the reason for rescheduling the appointment?",
                "new_date": "What is the new date for the appointment?",
                "new_date_end": "What is the new end time for the appointment?"
            }
        },
        "provider_availability_api": {
            "api_name": "check provider availability",
            "api_path": "https://hetzner-cpu-1.healiom-service.com/backend/dev/api/v1/provider_availability",
            "json_arguments": {
                "start_date": None,
                "number_of_days": None,
                "start_time": "00:00",
                "end_time": "23:59",
            },
            "json_arguments_schema": {
                "start_date": "datetime.date",
                "number_of_days": "int",
                "start_time": "datetime.time",
                "end_time": "datetime.time",
            },
            "json_arguments_options": {
                "start_date": None,
                "number_of_days": None,
                "start_time": None,
                "end_time": None,
            },
            "json_arguments_example": {
                "start_date": "2024-08-02",
                "number_of_days": 7,
                "start_time": "02:30",
                "end_time": "23:00"
            },
            "json_arguments_expected_format": {
                "start_date": "2024-08-02",
                "number_of_days": 7,
                "start_time": "02:30",
                "end_time": "23:00"
            },
            "json_arguments_hints": {
                "start_date": "You will now guide the user through a search for providers in a given time window. Please provide the start date for the search",
                "number_of_days": "Ask the user to provide the number of days beyond the start date to search for",
                "start_time": "Ask the user to provide the start time for when you want to see available providers",
                "end_time": "Ask the user to provide the end time for when you want to see available providers"
            }
        }
    },
    "INTENTS": [
        {
            "name": "schedule appointment",
            "alt_names": ["make a visit"],
            "logic_graph": {
                "start": "PROVIDER_AVAILABILITY_NODE",
                "nodes": {
                    "PROVIDER_AVAILABILITY_NODE": {
                        "type": "api",
                        "api_to_call": "provider_availability_api",
                        "next_node": "PROVIDER_AVAILABILITY_NODE_B"
                    },
                    "PROVIDER_AVAILABILITY_NODE_B": {
                        "type": "logic",
                        "logic_block": """
if memory['intent'] == "schedule appointment":
    res["next_node"] = "SCHEDULE_APPOINTMENT_NODE"
else:
    res["next_node"] = "RESCHEDULE_APPOINTMENT_NODE"
                            """
                    },
                    "SCHEDULE_APPOINTMENT_NODE" : {
                        "type": "api",
                        "api_to_call": "schedule_api",
                        "next_node": None
                    },
                    "RESCHEDULE_APPOINTMENT_NODE" : {
                        "type": "api",
                        "api_to_call": "reschedule_api",
                        "next_node": None
                    }
                }
            } 
        },
        {
            "name": "reschedule appointment",
            "alt_names": ["reschedule visit"],
            "logic_graph": {
                "start": "PROVIDER_AVAILABILITY_NODE",
                "nodes": {
                    "PROVIDER_AVAILABILITY_NODE": {
                        "type": "api",
                        "api_to_call": "provider_availability_api",
                        "next_node": "PROVIDER_AVAILABILITY_NODE_B"
                    },
                    "PROVIDER_AVAILABILITY_NODE_B": {
                        "type": "logic",
                        "logic_block": """
if memory['intent'] == "schedule appointment":
    res["next_node"] = "SCHEDULE_APPOINTMENT_NODE"
else:
    res["next_node"] = "RESCHEDULE_APPOINTMENT_NODE"
                            """
                    },
                    "SCHEDULE_APPOINTMENT_NODE" : {
                        "type": "api",
                        "api_to_call": "schedule_api",
                        "next_node": None
                    },
                    "RESCHEDULE_APPOINTMENT_NODE" : {
                        "type": "api",
                        "api_to_call": "reschedule_api",
                        "next_node": None
                    }
                }
            }
        },
    ],
}

CONTEXT = {}

AVAILABLE_APIS = {
    "schedule_api": {
        "api_name": "schedule visit",
        "api_path": "api.healion.com/practice_mgmt/schedule",
        "json_arguments": {
            "first name": None,
            "last name": None,
            "reason_for_visit": None,
            "date": None,
            "time_start": None,
            "provider": None
        },
        "json_arguments_schema": {
            "first name": "str",
            "last name": "str",
            "reason_for_visit": "str",
            "date": "datetime.date",
            "time_start": "datetime.time",
            "provider": "str"
        },
        "json_arguments_options": {
            "first name": None,
            "last name": None,
            "reason_for_visit": None,
            "date": None,
            "time_start": None,
            "provider": None
        },
        "json_arguments_expected_format": {
            "first name": "John",
            "last name": "Doe",
            "reason_for_visit": "checkup",
            "date": "2024-07-23",
            "time_start": "09:00:00",
            "provider": "Rishabh Shah"
        },
        "json_arguments_hints": {
            "first name": "You will guide the user through some basic information before selecting a provider to schedule with, starting with their name.",
            "last name": None,
            "reason_for_visit": None,
            "date": None,
            "time_start": None,
            "provider": None
        }
    },
    "reschedule_api": {
        "api_name": "reschedule visit",
        "api_path": "api.healion.com/practice_mgmt/reschedule",
        "json_arguments": {
            "first name": None,
            "last name": None,
            "reason_for_reschedule": None,
            "new_date": None,
            "new_date_end": None,
        },
        "json_arguments_schema": {
            "first name": "str",
            "last name": "str",
            "reason_for_visit": "str",
            "date": "datetime.date",
            "time_start": "datetime.time",
            "duration": "datetime.time",
        },
        "json_arguments_options": {
            "first name": None,
            "last name": None,
            "reason_for_reschedule": None,
            "new_date": None,
            "new_date_end": None,
        },
        "json_arguments_expected_format": {
            "first name": "John",
            "last name": "Doe",
            "reason_for_visit": "checkup",
            "date": "2024-07-23",
            "time_start": "09:00:00",
            "duration": "00:30:00"
        },
        "json_arguments_hints": {
            "first name": "What is your first name?",
            "last name": "What is your last name?",
            "reason_for_reschedule": "What is the reason for rescheduling the appointment?",
            "new_date": "What is the new date for the appointment?",
            "new_date_end": "What is the new end time for the appointment?"
        }
    },
    "provider_availability_api": {
        "api_name": "check provider availability",
        "api_path": "https://hetzner-cpu-1.healiom-service.com/backend/dev/api/v1/provider_availability",
        "json_arguments": {
            "start_date": None,
            "number_of_days": None,
            "start_time": "00:00",
            "end_time": "23:59",
        },
        "json_arguments_schema": {
            "start_date": "datetime.date",
            "number_of_days": "int",
            "start_time": "datetime.time",
            "end_time": "datetime.time",
        },
        "json_arguments_options": {
            "start_date": None,
            "number_of_days": None,
            "start_time": None,
            "end_time": None,
        },
        "json_arguments_example": {
            "start_date": "2024-08-02",
            "number_of_days": 7,
            "start_time": "02:30",
            "end_time": "23:00"
        },
        "json_arguments_expected_format": {
            "start_date": "2024-08-02",
            "number_of_days": 7,
            "start_time": "02:30",
            "end_time": "23:00"
        },
        "json_arguments_hints": {
            "start_date": "You will now guide the user through a search for providers in a given time window. Please provide the start date for the search",
            "number_of_days": "Ask the user to provide the number of days beyond the start date to search for",
            "start_time": "Ask the user to provide the start time for when you want to see available providers",
            "end_time": "Ask the user to provide the end time for when you want to see available providers"
        }
    }
}

INTENTS = [
    {
        "name": "schedule appointment",
        "alt_names": ["make a visit"],
        "logic_graph": {
            "start": "PROVIDER_AVAILABILITY_NODE",
            "nodes": {
                "PROVIDER_AVAILABILITY_NODE": {
                    "type": "api",
                    "api_to_call": AVAILABLE_APIS["provider_availability_api"],
                    "next_node": "PROVIDER_AVAILABILITY_NODE_B"
                },
                "PROVIDER_AVAILABILITY_NODE_B": {
                    "type": "logic",
                    "logic_block": """
if memory['intent'] == "schedule appointment":
    res["next_node"] = "SCHEDULE_APPOINTMENT_NODE"
else:
    res["next_node"] = "RESCHEDULE_APPOINTMENT_NODE"
                        """
                },
                "SCHEDULE_APPOINTMENT_NODE" : {
                    "type": "api",
                    "api_to_call": AVAILABLE_APIS["schedule_api"],
                    "next_node": None
                },
                "RESCHEDULE_APPOINTMENT_NODE" : {
                    "type": "api",
                    "api_to_call": AVAILABLE_APIS["reschedule_api"],
                    "next_node": None
                }
            }
        } 
    },
    {
        "name": "reschedule appointment",
        "alt_names": ["reschedule visit"],
        "logic_graph": {
            "start": "PROVIDER_AVAILABILITY_NODE",
            "nodes": {
                "PROVIDER_AVAILABILITY_NODE": {
                    "type": "api",
                    "api_to_call": AVAILABLE_APIS["provider_availability_api"],
                    "next_node": "PROVIDER_AVAILABILITY_NODE_B"
                },
                "PROVIDER_AVAILABILITY_NODE_B": {
                    "type": "logic",
                    "logic_block": """
if memory['intent'] == "schedule appointment":
    res["next_node"] = "SCHEDULE_APPOINTMENT_NODE"
else:
    res["next_node"] = "RESCHEDULE_APPOINTMENT_NODE"
                        """
                },
                "SCHEDULE_APPOINTMENT_NODE" : {
                    "type": "api",
                    "api_to_call": AVAILABLE_APIS["schedule_api"],
                    "next_node": None
                },
                "RESCHEDULE_APPOINTMENT_NODE" : {
                    "type": "api",
                    "api_to_call": AVAILABLE_APIS["reschedule_api"],
                    "next_node": None
                }
            }
        }
    },
]


conversation_stack = []
message_id = 1

options = ["Schedule New Appointment", "Reschedule an Existing Appointment", "Not Applicable"]

conversation_stack.append({
    "id": 0,
    "actor": "system",
    "message_type": "memory_instructions",
    "content": "You are Sam. You are a Clinic Appointment Scheduling service for a medical clinic. We can help you schedule a new appointment or reschedule an existing appointment. Whenever you believe it is appropriate, mention that the user may choose to quit the service at any time by just saying so."
})

# ----------------- Helper Functions -----------------

def fill_data_from_context(context, data, debug=False):
    if debug:
        print(f"fill_data_from_context called with context: {context}, data: {data}")
    
    data_json_string = json.dumps(data, indent=2)

    llm_prompt = f"""
    Given the following data payload, see if you can extract any fields from the context that are missing in the data. If you find any, return them in dictionary form. Leave fields that are already filled the same.
    For example, if the context contains "My name is John and I want to schedule an appointment since I've been ill" and the data is  
    {{
            "first name": None,
            "last name": Jones,
            "reason_for_visit": illness,
            "date": None,
            "time_start": None,
            "duration": None,
        }}
    then you should return {{"first name": "John", 
                            "last name": "Jones",
                            "reason_for_visit": "checkup"
                            }}
    Here is the data payload:
    {data_json_string}
    """

    llm_output = llm.invoke(llm_prompt).content.strip() 

    llm_output = llm_output.strip()
    
    if not llm_output:
        return data

    try:
        extracted_data = json.loads(llm_output)

        for key in extracted_data:
            data[key] = extracted_data[key]
    except json.JSONDecodeError as e:
        if debug:
            print(f"Error extracting data from context: {e}")
        pass
    except Exception as e:
        if debug:
            print(f"Unexpected error: {e}")

    if debug:
        print(f"Data after filling from context: {data}")

    return data

def check_quit(debug=False):
    llm_prompt = """
    Given the following context, check if the user has decided to quit the service. Look out for any key terms such as 'leave'. If they have, respond with 1. If they have not, respond with 0. Response must be a number. 
    """
    
    llm_output = prompt_llm_with_context(conversation_stack[-1], llm_prompt)
    
    if '1' in llm_output:
        if debug:
            print("User decided to quit the service.")
        print("Thank you for using our Clinic Appointment Scheduling service. Have a great day!")
        return True
    else:
        return False

def record_interaction(actor, content, intent=None, debug=False):
    global message_id

    # if debug:
    #     print(f"record_context called with actor: {actor}, content: {content}, intent: {intent}")

    # set message type
    if actor == 'system':
        message_type = 'system_message'
    elif actor == 'user':
        message_type = 'user_message'
    else:
        message_type = None

    conversation_stack.append({
        "message_id": message_id,
        "actor": actor,
        "message_type": message_type,
        "content": content,
        "in_response_to": message_id - 1 if message_id > 0 else None,
        "intent": intent,
        "from_control_function": get_caller_name(debug=debug),
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    message_id += 1

    if debug:
        print(f"Updated conversation stack with latest message.")

# ----------------- Main Functions -----------------

def intent_loop(debug=False):
    # welcome_message = """Hey I'm Sam. Thanks for stopping by! I'm a Clinic Appointment Scheduling service for my medical clinic. I can help you schedule a new appointment or reschedule an existing appointment. How can I help?"""
    welcome_message = user_agent.call("Given your instructions, generate an intro message to greet the user and explain the service.")

    if debug:
        print("intent_loop started.")
    
    record_interaction('system', welcome_message, debug=debug)
    
    curr_resp = input(welcome_message + '\n')
    print()
    record_interaction('user', curr_resp, debug=debug)

    while True:
        if check_quit(debug=debug):
            user_intent = None
            break

        best_option = select_best_option(curr_resp, options, debug=debug)

        if best_option == 'Schedule New Appointment':
            curr_message = "Great, let's schedule a new appointment"
            record_interaction('system', curr_message, debug=debug)
            user_intent = INTENTS[0]
            break
            # curr_message = "It sounds like you would like to schedule a new appointment. Is this correct?"
            # record_interaction('system', curr_message, debug=debug)
            
            # curr_resp = input(curr_message + '\n')
            # print()
            # record_interaction('user', curr_resp, debug=debug)

            # llm_prompt = """
            # Given the following context, check if the user has double confirmed that they would like to schedule a new appointment. If they have, respond with 1. If they have not, respond with 0. Only respond with a number.
            # """
            
            # llm_output = prompt_llm_with_context([curr_resp, conversation_stack[-2]], llm_prompt, debug=debug)

            # if '1' in llm_output:
            #     curr_message = "Great, let's schedule a new appointment"
            #     record_interaction('system', curr_message, debug=debug)
            #     user_intent = INTENTS[0]
            #     break
            # else:
            #     curr_message = "What would you like to do instead?"
            #     record_interaction('system', curr_message, debug=debug)
            #     curr_resp = input(curr_message + '\n')
            #     print()
            #     record_interaction('user', curr_resp, debug=debug)
            #     continue

        elif best_option == 'Reschedule an Existing Appointment':
            curr_message = "Great, let's reschedule an existing appointment"
            record_interaction('system', curr_message, debug=debug)
            user_intent = INTENTS[1]
            # curr_message = "It sounds like you would like to reschedule an existing appointment. Is this correct?"
            # record_interaction('system', curr_message, debug=debug)
            
            # curr_resp = input(curr_message + '\n')
            # print()
            # record_interaction('user', curr_resp, debug=debug)

            # llm_prompt = """
            # Given the following context, check if the user has double confirmed that they would like to reschedule an existing appointment. If they have, respond with 1. If they have not, respond with 0. Only respond with a number 
            # """
            
            # llm_output = prompt_llm_with_context([curr_resp, conversation_stack[-2]], llm_prompt, debug=debug)  
            
            # if '1' in llm_output:
            #     curr_message = "Great, let's reschedule an existing appointment"
            #     record_interaction('system', curr_message, debug=debug)
            #     user_intent = INTENTS[1]
            #     break
            # else:
            #     curr_message = "What would you like to do instead?"
            #     record_interaction('system', curr_message, debug=debug)
            #     curr_resp = input(curr_message + '\n')
            #     print()
            #     record_interaction('user', curr_resp, debug=debug)
            #     continue

        elif best_option == 'Not Applicable':
            llm_prompt = """
            Given the following context, respond with a message that acknowledges the user's response but reiterates that we are a clinic scheduling service.
            """
            
            llm_output = user_agent.call(llm_prompt)  
            curr_message = llm_output
            record_interaction('system', curr_message, debug=debug)
            
            curr_resp = input(curr_message + '\n')
            print()
            record_interaction('user', curr_resp, debug=debug)

            if check_quit(debug=debug):
                user_intent = None
                break
            else:
                continue

    if debug:
        print(f"Intent loop finished. User intent: {user_intent}")

    return user_intent

def data_gathering_loop(api, debug=False):
    payload = api['json_arguments']

    if debug:
        print(f"data_gathering_loop started for API: {api['api_name']}. Initial payload: {payload}")

    # if api['api_name'] != "check provider availability":
        # payload = fill_data_from_context(conversation_stack, payload, debug=debug)
        # payload = fill_data_from_context(CONTEXT, payload, debug=debug)

    # iterate through all the payload fields that are not empty
    for key in payload:
        if payload[key] is None:
            # construct a question to ask the user
            output_options = api['json_arguments_options'][key]
            question = construct_question(json_context=conversation_stack, target_variable=key, hint=api['json_arguments_hints'][key], output_options=output_options, debug=debug)
            record_interaction('system', question, debug=debug)

            # question = user_agent.call(question)

            while True:
                response = input(question + '\n')
                print()
                record_interaction('user', response, debug=debug)

                interpretation = interpret_response(question, api['json_arguments_schema'][key], output_options, response, debug=debug)
                if debug:
                    print(f"Interpretation: {interpretation}")
                if interpretation:
                    if debug:
                        print(f"Interpreted response: {interpretation}")
                    payload[key] = interpretation
                    CONTEXT[key] = interpretation
                    break
                else:
                    print("I couldn't interpret the response. Please try again.")
                    prompt = "The user was just asked a question and we couldn't interpret the response. Please suggest a follow-up question that acknowledges their initial answer and the issue with it if possible."
                    follow_up = llm.invoke(prompt).content.strip()  
                    record_interaction('system', follow_up, debug=debug)
                    continue

    if api['api_name'] == "check provider availability":
        payload["start_date"] = payload["start_date"].strftime("%Y-%m-%d")
        # payload["start_time"] = payload["start_time"].strftime("%H:%M")
        # payload["end_time"] = payload["end_time"].strftime("%H:%M")

    if debug:
        print(f"Payload after data gathering: {payload}")

    return payload

def execution_loop(intent, debug=False):
    if debug:
        print(f"execution_loop started with intent: {intent}")

    headers = {
        "Authorization": f"Bearer {os.getenv('JWT_TOKEN')}",
        "he_type": "Patient",
        "organization_id": "776e17a2-f7cb-45b0-a52a-630e57c7227e"
    }

    logic_graph = intent["logic_graph"]
    
    next_node = logic_graph["start"]
    while next_node:
        node = logic_graph["nodes"][next_node]
        CONTEXT["current_logic_node"] = node
        if node["type"] == "api":
            api_to_call = node["api_to_call"]
            if debug:
                print(f"calling API: {api_to_call['api_name']}")
            payload = data_gathering_loop(api_to_call, debug=debug)

            if debug:
                print(f"Payload: {payload}")
            
            if api_to_call['api_name'] == "check provider availability":
                if debug:
                    print("Checking provider availability...")
                url = api_to_call['api_path']
                response = requests.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    providers = []
                    availability_by_date = {}
                    for item in response.json()["items"]:
                        if 'display_name' in item:
                            providers.append(item['display_name'])
                        availble_date_time = item["available_date_time"]
                        for date in availble_date_time:
                            if date not in availability_by_date:
                                availability_by_date[date] = 1
                            else:
                                availability_by_date[date] += 1
                    AVAILABLE_APIS["schedule_api"]["json_arguments_options"]["provider"] = providers
                    AVAILABLE_APIS["reschedule_api"]["json_arguments_options"]["provider"] = providers

                    # print the availability by date for the user
                    print("Here is the number of available providers each day:")
                    for date in availability_by_date:
                        print(f"{date}: Available Providers: {availability_by_date[date]}")
                    print()

                else:
                    if debug:
                        print(f"Request failed with status code {response.status_code}")
                        print("Response:", response.text)
            else:
                print(f"API {api_to_call['api_name']} called.")
                print(f"Payload: {payload}")

            next_node = node["next_node"]
        elif node["type"] == "logic":
            next_node = which_next(node["logic_block"], CONTEXT)
        else:
            print("Invalid node type")
            break


# ----------------- Control Loop -----------------
def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Control debug mode")
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    # Parse arguments
    args = parser.parse_args()
    
    # Set debug flag based on argument
    debug = args.debug

    # Main logic
    intent = intent_loop(debug=debug)
    if intent:
        CONTEXT['intent'] = intent['name']
        execution_loop(intent, debug=debug)

if __name__ == "__main__":
    main()
