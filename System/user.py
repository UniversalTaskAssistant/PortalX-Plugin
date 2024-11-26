import os

class User:
    def __init__(self, user_id: str, output_dir: str="./Output/"):
        self.user_id = user_id
        self.user_dir = os.path.join(output_dir, "users", user_id)
        self.chat_dir = os.path.join(self.user_dir, "chats")
        self._initialize_directories()

    def _initialize_directories(self):
        """Create necessary directories if they don't exist"""
        os.makedirs(self.chat_dir, exist_ok=True)
