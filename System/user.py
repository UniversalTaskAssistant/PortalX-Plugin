import os

class User:
    def __init__(self, user_id: str, output_dir: str="./Output/"):
        self.user_id = user_id
        
        # User directory
        self.user_dir = os.path.join(output_dir, "users", user_id)
        self.chat_dir = os.path.join(self.user_dir, "chats")
        os.makedirs(self.chat_dir, exist_ok=True)

    def save_user_data(self):
        pass

    def load_user_data(self):
        pass
