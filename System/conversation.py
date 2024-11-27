import json
from datetime import datetime
from os.path import join as pjoin
import os


class Conversation:
    def __init__(self, conversation_id: str, data_dir: str="./Output/chat"):
        self.data_dir = data_dir

        self.conv_id = conversation_id
        self.timestamp = None
        self.conversation = []  # [{"rule": str, "content": str}]
        self.load_conversation()

    def load_conversation(self):
        if os.path.exists(pjoin(self.data_dir, f"{self.conv_id}.json")):
            data = json.load(open(pjoin(self.data_dir, f"{self.conv_id}.json"), 'r'))
            self.timestamp = data["timestamp"]
            self.conversation = data["conversation"]

    def append_conversation(self, role: str, content: str):
        self.conversation.append({"rule": role, "content": content})
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    def save_conversation(self):
        data = {"conversation_id": self.conv_id, "timestamp": self.timestamp, "conversation": self.conversation}
        json.dump(data, open(pjoin(self.data_dir, f"{self.conv_id}.json"), 'w'), indent=4)

if __name__ == "__main__":
    conv = Conversation(conversation_id="test1", data_dir="./Output/chat")
    conv.append_conversation(role="assistant", content="test")
    conv.save_conversation()
