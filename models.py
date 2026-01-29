from datetime import datetime

class Event:
    def __init__(self, action, author, from_branch, to_branch, timestamp):
        self.action = action
        self.author = author
        self.from_branch = from_branch
        self.to_branch = to_branch
        self.timestamp = timestamp
    
    def to_dict(self):
        return {
            'action': self.action,
            'author': self.author,
            'from_branch': self.from_branch,
            'to_branch': self.to_branch,
            'timestamp': self.timestamp
        }