from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit
import json
from main import user_agent, helper_agent, fill_data_from_context, check_quit, record_interaction, data_gathering_loop, which_next, select_best_option

app = Flask(__name__)
socketio = SocketIO(app)

# Global variables
CONTEXT = {}
AVAILABLE_APIS = {}
INTENTS = []
options = []
uploaded_data = {}
current_intent = None
current_api = None
current_api_field = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_data():
    global uploaded_data
    data = request.json
    uploaded_data = data
    initialize_chatbot(uploaded_data)
    return jsonify({"message": "Data uploaded successfully"}), 200

@socketio.on('start_chat')
def handle_start_chat():
    global CONTEXT, current_intent, current_api, current_api_field
    
    # Reset conversation state
    CONTEXT = {}
    current_intent = None
    current_api = None
    current_api_field = None
    
    # Start the chatbot conversation
    welcome_message = user_agent.call("Given your instructions, generate an intro message to greet the user and explain the service.")
    record_interaction('system', welcome_message)
    emit('message', {'sender': 'bot', 'message': welcome_message})

@socketio.on('user_message')
def handle_user_message(message):
    global CONTEXT, current_intent, current_api, current_api_field
    
    record_interaction('user', message)
    
    if check_quit():
        emit('message', {'sender': 'bot', 'message': "Thank you for using our Clinic Appointment Scheduling service. Have a great day!"})
        return

    if current_api and current_api_field:
        # We're in the middle of gathering data for an API
        handle_api_input(message)
    elif current_intent is None:
        # We're at the start of the conversation, trying to determine the intent
        intent = get_intent(message)
        if intent:
            current_intent = intent
            CONTEXT['intent'] = intent['name']
            handle_execution(intent)
        else:
            response = user_agent.call(f"The user said: {message}. Respond appropriately based on your role as a Clinic Appointment Scheduling service.")
            emit('message', {'sender': 'bot', 'message': response})
    else:
        # We're in the middle of executing an intent
        handle_execution(current_intent)

def initialize_chatbot(data):
    global AVAILABLE_APIS, INTENTS, options
    
    # Update global variables with uploaded data
    if 'AVAILABLE_APIS' in data:
        AVAILABLE_APIS = data['AVAILABLE_APIS']
    if 'INTENTS' in data:
        INTENTS = data['INTENTS']
    if 'options' in data:
        options = data['options']

def get_intent(message):
    best_option = select_best_option(message, options)
    
    for intent in INTENTS:
        if intent['name'] == best_option or best_option in intent.get('alt_names', []):
            return intent
    
    return None

def handle_execution(intent):
    global current_api, current_api_field
    logic_graph = intent["logic_graph"]
    next_node = logic_graph["start"]
    
    while next_node:
        node = logic_graph["nodes"][next_node]
        CONTEXT["current_logic_node"] = node
        
        if node["type"] == "api":
            api_name = node["api_to_call"]
            if api_name in AVAILABLE_APIS:
                current_api = AVAILABLE_APIS[api_name]
                gather_data(current_api)
                break  # Exit the loop and wait for user input
            else:
                emit('message', {'sender': 'bot', 'message': f"Error: API {api_name} not found in AVAILABLE_APIS"})
                break
        elif node["type"] == "logic":
            next_node = which_next(node["logic_block"], CONTEXT)
        else:
            emit('message', {'sender': 'bot', 'message': "Invalid node type"})
            break

def gather_data(api):
    global current_api_field
    for key, value in api['json_arguments'].items():
        if value is None and key not in CONTEXT:
            current_api_field = key
            question = construct_question(api, key)
            emit('message', {'sender': 'bot', 'message': question})
            break  # Ask one question at a time

def handle_api_input(user_input):
    global current_api, current_api_field, CONTEXT
    
    interpretation = interpret_response(current_api, current_api_field, user_input)
    if interpretation:
        CONTEXT[current_api_field] = interpretation
        current_api_field = None
        gather_data(current_api)  # Continue gathering data
    else:
        emit('message', {'sender': 'bot', 'message': "I couldn't interpret that response. Could you please try again?"})
    
    # Check if we've gathered all the data
    if all(key in CONTEXT or value is not None for key, value in current_api['json_arguments'].items()):
        # If we've gathered all the data, proceed with the API call
        payload = {key: CONTEXT.get(key, value) for key, value in current_api['json_arguments'].items()}
        emit('message', {'sender': 'bot', 'message': f"API {current_api['api_name']} called with payload: {json.dumps(payload, indent=2)}"})
        
        # Reset for the next API or intent
        current_api = None
        current_api_field = None
        
        # Continue with the next node in the intent's logic graph
        handle_execution(current_intent)

def construct_question(api, key):
    hint = api['json_arguments_hints'].get(key, "")
    return f"Please provide the {key}. {hint}"

def interpret_response(api, key, response):
    # This is a simplified interpretation. You might need more complex logic based on your requirements.
    return response

if __name__ == '__main__':
    socketio.run(app, debug=True)