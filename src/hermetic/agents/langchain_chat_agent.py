import openai
from hermetic.core.agent import Agent, InputMarker
from abc import abstractmethod
from langchain.chat_models import ChatOpenAI
from langchain.callbacks.base import BaseCallbackHandler
from queue import SimpleQueue
from threading import Thread
import sys

from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage
)

class StreamingCBH(BaseCallbackHandler):
    def __init__(self, q):
        self.q = q

    def on_llm_new_token(
        self,
        token,
        *,
        run_id,
        parent_run_id = None,
        **kwargs,
    ) -> None:
        self.q.put(token)
    
    def on_llm_end(self, response, *, run_id, parent_run_id, **kwargs):
        self.q.put(InputMarker.END)

class LangchainChatAgent(Agent):

    def set_llm(self, llm):
        self.llm = llm

    def __init__(self, environment, id: str = None):
        super().__init__(environment, id=id)
        self.message_history = []
        self.q = SimpleQueue()

    def greet(self):
        return None
    
    def get_queue(self):
        return self.q

    def process_input(self, input: str):
        self.message_history.append(HumanMessage(content=input))
        thread =  Thread(target = self.llm.predict_messages, kwargs = {'messages': self.message_history})
        thread.start() 
        words = ''
        while True: 
            token = self.q.get()
            if token == InputMarker.END:
               break
            words += token 
            yield token

        self.message_history.append(AIMessage(content=words))

    def update_message_history(self, inp):
        """
        Subclasses of OpenAIChatAgent may want to override this
        method to do things like add metadata to the message history
        """
        self.message_history.append({
            'role': 'user',
            'content': inp
        })

        