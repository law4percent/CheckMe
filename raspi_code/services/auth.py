"""
START
  │
  ▼
Does cred.txt exist?
  │
  ├─NO──► Create cred.txt with {"teacher_uid": null, "username": null}
  │       │
  │       ▼
  │     Return NOT_AUTHENTICATED
  │
  ├─YES─► Load cred.txt
          │
          ▼
        Do teacher_uid AND username keys exist?
          │
          ├─NO──► Return NOT_AUTHENTICATED
          │
          ├─YES─► Are BOTH values non-null?
                  │
                  ├─NO──► Return NOT_AUTHENTICATED
                  │
                  └─YES─► Return AUTHENTICATED
                          + teacher_uid value
                          + username value
"""

class Authenticate:
    def __init__(self):
        pass

    