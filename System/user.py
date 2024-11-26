import os

class User:
    def __init__(self, user_id: str, data_dir: str="./Output/"):
        self.user_id = user_id

        self.user_dir = os.path.join(data_dir, "user", user_id)
        self.chat_dir = os.path.join(self.user_dir, "chat")
        self.websites_dir = os.path.join(self.user_dir, "websites")

        self.init_user()

    def init_user(self):
        if not os.path.exists(self.user_dir):
            os.makedirs(self.chat_dir, exist_ok=True)
            os.makedirs(self.websites_dir, exist_ok=True)
