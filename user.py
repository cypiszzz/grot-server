import email.mime.text
import uuid
import smtplib
import multiprocessing.pool

import settings


# smtp = smtplib.SMTP(settings.SMTP_HOST)
# smtp.starttls()
# smtp.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)

# smtp_thread = multiprocessing.pool.ThreadPool(1)


class User(object):
    collection = settings.db['users']

    def __init__(self, name, email, **kwargs):
        self.id = kwargs.get('_id')
        self.name = name
        self.email = email
        self.token = kwargs.get('token', str(uuid.uuid4()))
        self.admin = kwargs.get('admin')

    def __lt__(self, other):
        return self.name < other.name

    @classmethod
    def get(cls, token):
        if not token:
            return None

        user = User.collection.find_one({
            'token': token,
        })

        return cls(**user) if user else None

    def put(self):
        saved = self.id is not None
        user = {
            'name': self.name,
            'email': self.email,
            'token': self.token,
        }

        if saved:
            user['_id'] = self.id

        self.id = User.collection.save(user)

        if not saved:
            self.on_create()

    def send(self, subject, body):
        def task(user, subject, body):
            message = email.mime.text.MIMEText(body)
            message['From'] = settings.SMTP_EMAIL
            message['To'] = user.email
            message['Subject'] = subject

            smtp.send_message(message)

        smtp_thread.apply_async(task, (self, subject, body))

    def on_create(self):
        pass
        self.send('Registration', self.token)


class LocalUser(User):
    def __init__(self, name, *arg, **kwargs):
        super(LocalUser, self).__init__(
            name,
            settings.SMTP_EMAIL,
            _id=name,
            admin=True,
            token=name,
        )

    def put(self):
        pass

    def send(self, *args, **kwargs):
        pass
