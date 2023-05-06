from dataclasses import dataclass

TOKEN_TYPE_CHOICE = (
    ("ACCOUNT_VERIFICATION", "ACCOUNT_VERIFICATION"),
    ("PASSWORD_RESET", "PASSWORD_RESET"),
)

ROLE_CHOICE = (
    ("ADMIN", "ADMIN"),
    ("CUSTOMER", "CUSTOMER"),

)

@dataclass
class TokenEnum:
    ACCOUNT_VERIFICATION = "ACCOUNT_VERIFICATION"
    PASSWORD_RESET = "PASSWORD_RESET"


@dataclass
class SystemRoleEnum:
    ADMIN = "ADMIN"
    CUSTOMER = "CUSTOMER"

