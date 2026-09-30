"""
Mock in-memory database for demonstration purposes.
Stores user records in a global dictionary.
"""

from typing import Any

# In-memory user database mapping username -> user_dict
# Schema of user_dict:
# {
#     "id": str,
#     "username": str,
#     "hashed_password": str
# }
fake_users_db: dict[str, dict[str, Any]] = {}
