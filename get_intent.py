from helper import *
import json
from langchain_openai import ChatOpenAI
import datetime

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

# ----------------- Constants / Globals -----------------

AVAILABLE_APIS = {
    "schedule_api": {
        "api_name": "schedule visit",
        "api_path": "api.healion.com/practice_mgmt/schedule",
        "json_arguments" : {
            "first name": None,
            "last name": None,
            "reason_for_visit": None,
            "date_start": None,
            "date_end": None,
        }
    },
    "reschedule_api": {
        "api_name": "reschedule visit",
        "api_path": "api.healion.com/practice_mgmt/reschedule",
        "json_arguments" : {
            "first name": None,
            "last name": None,
            "reason_for_reschedule": None,
            "new_date_start": None,
            "new_date_end": None,
        }
    }
}

INTENTS = [
    {
        "name": "schedule appointment",
        "alt_names": ["make a visit"],
        "api_graph": [
            {
                "api_name": "schedule_api",
            }
        ]
    },
    {
        "name": "reschedule appointment",
        "alt_names": ["reschedule visit"],
        "api_graph": [
            {
                "api_name": "reschedule_api",
            }
        ]
    },
]

conversation_stack = []
message_id = 1

options = ["Schedule New Appointment", "Reschedule an Existing Appointment", "Not Applicable"]

conversation_stack.append({
    "id": 0,
    "actor": "system",
    "message_type": "memory_instructions",
    "content": "This is a Clinic Appointment Scheduling service for a medical clinic. We can help you schedule a new appointment or reschedule an existing appointment. Whenever you believe it is appropriate, mention that the user may choose to quit the service at any time by just saying so."
})

# ----------------- Helper Functions -----------------

def check_quit():
    llm_prompt = """
    Given the following context, check if the user has decided to quit the service. If they have, respond with 'yes'. If they have not, respond with 'no'. 
    """
    
    llm_output = prompt_llm_with_context(conversation_stack, llm_prompt)
    
    if 'yes' in llm_output:
        print("Thank you for using our Clinic Appointment Scheduling service. Have a great day!")
        return True
    else:
        return False

def record_context(actor, content, intent=None):
    global message_id

    # set message type
    if actor == 'system':
        message_type = 'system_message'
    elif actor == 'user':
        message_type = 'user_message'
    else:
        message_type = None

    conversation_stack.append({
        "id": message_id,
        "actor": actor,
        "message_type": message_type,
        "content": content,
        "in_response_to": message_id - 1 if message_id > 0 else None,
        "intent": intent,
        "from_control_function": get_caller_name(),
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    message_id += 1

# ----------------- Main Functions -----------------

def intent_loop():
    welcome_message = "Welcome to our Clinic Appointment Scheduling service. What would you like to do? You may quit this interface by just saying so."

    record_context('system', welcome_message)
    
    curr_resp = input(welcome_message + '\n')
    record_context('user', curr_resp)

    while True:
        if check_quit():
            user_intent = None
            break

        best_option = select_best_option(curr_resp, options)

        if best_option == 'Schedule New Appointment':
            curr_message = "It sounds like you would like to schedule a new appointment. Is this correct?"
            record_context('system', curr_message)
            
            curr_resp = input(curr_message + '\n')
            record_context('user', curr_resp)

            llm_prompt = """
            Given the following context, check if the user has double confirmed that they would like to schedule a new appointment. If they have, respond with 'yes'. If they have not, respond with 'no'. 
            """
            
            llm_output = prompt_llm_with_context(conversation_stack, llm_prompt)
            
            if 'yes' in llm_output:
                curr_message = "Great, let's schedule a new appointment"
                record_context('system', curr_message)
                user_intent = INTENTS[0]
                break
            else:
                curr_message = "What would you like to do instead?"
                record_context('system', curr_message)
                curr_resp = input(curr_message + '\n')
                record_context('user', curr_resp)
                continue

        elif best_option == 'Reschedule an Existing Appointment':
            curr_message = "It sounds like you would like to reschedule an existing appointment. Is this correct?"
            record_context('system', curr_message)
            
            curr_resp = input(curr_message + '\n')
            record_context('user', curr_resp)

            llm_prompt = """
            Given the following context, check if the user has double confirmed that they would like to reschedule an existing appointment. If they have, respond with 'yes'. If they have not, respond with 'no'. 
            """
            
            llm_output = prompt_llm_with_context(conversation_stack, llm_prompt)
            
            if 'yes' in llm_output:
                curr_message = "Great, let's reschedule an existing appointment"
                record_context('system', curr_message)
                user_intent = INTENTS[1]
                break
            else:
                curr_message = "What would you like to do instead?"
                record_context('system', curr_message)
                curr_resp = input(curr_message + '\n')
                record_context('user', curr_resp)
                continue

        elif best_option == 'Not Applicable':
            llm_prompt = """
            Given the following context, respond with a message that acknowledges the user's response but reiterates that we are a clinic scheduling service.
            """
            
            llm_output = prompt_llm_with_context(conversation_stack, llm_prompt)
            curr_message = llm_output
            record_context('system', curr_message)
            
            curr_resp = input(curr_message + '\n')
            record_context('user', curr_resp)

            if check_quit():
                user_intent = None
                break
            else:
                continue

    print("End of conversation")
    print("Here is a transcript of the conversation:")
    print(json.dumps(conversation_stack, indent=2))

    return user_intent

def data_gathering_loop(intent):
    api = AVAILABLE_APIS[get_start_api(intent)]

    payload = api['json_arguments']

    # TODO: populate paylaod with existing information

    for key in payload:
        if payload[key] is None:
            prompt = f"Please provide the value for '{key}'"
            response = llm.invoke(prompt).pretty_repr()
            payload[key] = response



# TODO
# def execution_loop




# ----------------- Control Loop -----------------
if __name__ == "__main__":
    intent = intent_loop()
    if intent:
        print(data_gathering_loop(intent))
