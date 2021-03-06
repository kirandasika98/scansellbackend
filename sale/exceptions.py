# This file will have all the exceptions that the app for sale will hold

class NotificationNotFoundException(Exception):
    ''' This arises only when the notification that we are trying to get is not
    found '''
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class UserForIDNotFoundException(Exception):
    ''' This only arises when the user id is not in the database '''
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
        
class ErrorInInsertionException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
