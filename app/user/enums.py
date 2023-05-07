from dataclasses import dataclass

TOKEN_TYPE_CHOICE = (
    ("PASSWORD_RESET", "PASSWORD_RESET"),
)

ROLE_CHOICE = (
    ("ADMIN", "ADMIN"),
    ("CUSTOMER", "CUSTOMER"),

)

@dataclass
class TokenEnum:
    PASSWORD_RESET = "PASSWORD_RESET"


@dataclass
class SystemRoleEnum:
    ADMIN = "ADMIN"
    CUSTOMER = "CUSTOMER"

