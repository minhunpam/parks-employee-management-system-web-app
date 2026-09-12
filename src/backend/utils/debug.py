from django.contrib.auth.models import AnonymousUser

class Debugger:
    @staticmethod
    def debug_user(user) -> None:
        if isinstance(user, AnonymousUser) or not user.is_authenticated:
            print("User: AnonymousUser")
            print("Authenticated: False")
            return

        print(f"""
            ========= User Debug Info ========
            ID: {user.id}
            Email: {user.email}
            IsActive: {user.is_active}
            IsStaff: {user.is_staff}
            IsSuperuser: {user.is_superuser}
            ==================================
        """)
