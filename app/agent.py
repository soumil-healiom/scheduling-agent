from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain_core.prompts.prompt import PromptTemplate

class Agent:
    def __init__(self, initial_instructions=[], temperature=0.7):
        self.llm = ChatOpenAI(temperature=temperature)
        self.instructions = initial_instructions  
        self.memory = ConversationBufferMemory() 
        self.agent = self._create_agent()

    def _create_agent(self):
        instructions_text = "\n".join([f"{i + 1}. {instruction}" for i, instruction in enumerate(self.instructions)])

        template = """You are a helpful AI agent. Please follow the instructions given below:
        Instructions:
        {instructions}

        Current conversation:
        {history}
        Human: {input}
        AI Assistant:"""

        formatted_template = template.format(instructions=instructions_text, history="{history}", input="{input}")

        prompt = PromptTemplate.from_template(formatted_template)

        return ConversationChain(
            prompt = prompt,
            llm = self.llm,
            verbose = False,
            memory = self.memory,
        )

    def add_instruction(self, new_instruction):
        self.instructions.append(new_instruction)  
        self.agent = self._create_agent()  # Recreate the agent with updated instructions

    def call(self, user_input):
        response = self.agent.predict(input=user_input)

        assistant_response = response.strip()        
        
        return assistant_response

    def get_instructions(self):
        return self.instructions  
    
    def print_instructions(self):
        print('Instructions:')
        for i, instruction in enumerate(self.get_instructions()):
            print(f'{i + 1}. {instruction}')

    def get_conversation_history(self):
        return self.memory.load_memory_variables({})['history']

    def print_conversation_history(self):
        print('Conversation history:')
        print(self.get_conversation_history())  