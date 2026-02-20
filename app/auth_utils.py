def check_role(user, allowed_roles):
    if user.role not in allowed_roles:
        raise Exception("Unauthorized action")
