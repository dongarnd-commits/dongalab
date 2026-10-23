"""Local format/check-digit validation; never claims NTS registration status."""
import re

def normalize_business_number(value: str) -> str:
    if not isinstance(value,str):raise ValueError("BUSINESS_NUMBER_FORMAT_INVALID")
    value = value.strip()
    if re.fullmatch(r"[0-9]{3}-[0-9]{2}-[0-9]{5}", value):
        value = value.replace("-", "")
    if not re.fullmatch(r"[0-9]{10}", value):
        raise ValueError("BUSINESS_NUMBER_FORMAT_INVALID")
    return value

def validate_business_number(value: str) -> str:
    value = normalize_business_number(value)
    digits = list(map(int, value))
    total = sum(a*b for a,b in zip(digits[:9], (1,3,7,1,3,7,1,3,5))) + digits[8]*5//10
    if len(set(value)) == 1 or (10-total%10)%10 != digits[9]:
        raise ValueError("BUSINESS_NUMBER_CHECKSUM_INVALID")
    return value
