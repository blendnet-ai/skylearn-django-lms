import random
import string


class Utils:
    @staticmethod
    def generate_random_password():
        characters = string.ascii_letters + string.digits
        password = "".join(random.choice(characters) for _ in range(12))
        return password
