import re
from typing import Optional


def normalize_email(email: Optional[str]) -> Optional[str]:
    """
    Normalize a Gmail address:
    1. Lowercase
    2. Strip '+alias' portion (everything after + before @)
    3. Remove dots from local part (Gmail ignores dots)

    Returns None if email is None or empty.
    """
    if not email or not email.strip():
        return None

    email = email.strip().lower()

    if '@' not in email:
        return None

    local, domain = email.rsplit('@', 1)

    if domain == 'gmail.com':
        # Remove +alias
        local = local.split('+')[0]
        # Remove dots
        local = local.replace('.', '')

    if not local:
        return None

    return f'{local}@{domain}'


def normalize_phone(phone: Optional[str]) -> Optional[str]:
    """
    Normalize phone number by:
    1. Stripping all non-digit characters
    2. Removing country code prefix (91, 0091) to get last 10 digits

    Returns None if phone is None or empty.
    """
    if not phone or not str(phone).strip():
        return None

    digits = re.sub(r'\D', '', str(phone))

    if not digits:
        return None

    # Indian numbers: strip country code to get 10-digit number
    if len(digits) > 10:
        digits = digits[-10:]

    return digits


def normalize_name(name: str) -> str:
    """
    Normalize student name:
    1. Strip leading/trailing whitespace
    2. Collapse multiple spaces
    3. Title case
    """
    if not name:
        return ''
    return ' '.join(name.strip().split()).title()


def get_student_identity(
    email: Optional[str],
    phone: Optional[str]
) -> tuple[str, str]:
    """
    Determine canonical student identity.
    Returns (identity_type, identity_value).
    Priority: normalized email > normalized phone.
    """
    norm_email = normalize_email(email)
    if norm_email:
        return ('email', norm_email)

    norm_phone = normalize_phone(phone)
    if norm_phone:
        return ('phone', norm_phone)

    raise ValueError('Student must have at least an email or phone number')
