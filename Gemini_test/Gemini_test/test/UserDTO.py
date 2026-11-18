class UserDTO:
    def __init__(self, user_id, user_pw, user_email, user_name): #user_email 추가
        self.user_id = user_id
        self.user_pw = user_pw
        self.user_email = user_email
        self.user_name = user_name
class Hasher:
    def __init__(self, user_id):
        self.user_id = user_id

class Update_user:
    def __init__(self, user_id, user_pw, name):
        self.user_id = user_id
        self.user_pw = user_pw
        self.name = name
        pass