class AnimalDTO:
    def __init__(self, user_id, personality, mbti, animal, breed):
        self.user_id = user_id
        self.personality = personality
        self.mbti = mbti
        self.animal = animal
        self.breed = breed

class UserAnimalList:
    def __init__(self, user_id, animal, breed, type):
        self.user_id = user_id
        self.animal = animal
        self.breed = breed
        self.type = type

class list:
    def __init__(self, user_id):
        self.user_id = user_id

        