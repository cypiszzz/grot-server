

class User(object):

    def __init__(self, name, admin=False):
        self.id = name
        self.name = name
        self.admin = admin

    def __lt__(self, other):
        return self.name < other.name


class LocalUser(User):
    def __init__(self, name):
        super(LocalUser, self).__init__(
            name,
            admin=True,
        )
