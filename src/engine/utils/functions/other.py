import re
from rapidfuzz import fuzz
import base58


def str_to_base58(string: str) -> str:
    """
    Encodes a string to Base58
    :param string: Input string to encode
    :return: Encoded string in Base58 format
    """
    return base58.b58encode(string.encode('utf-8')).decode('utf-8')


def base58_to_str(string: str) -> str:
    """
    Decodes a Base58-encoded string to normal text
    :param string: Base58-encoded string to decode
    :return: Normal text string
    """
    return base58.b58decode(string).decode('utf-8')


JAPANESE_CHAR_PATTERN = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9faf]")


def contains_japanese(string: str, threshold: float = 0.60) -> bool:
    if type(string) is not str:
        return False

    japanese_token = 0

    tokens = string.split()
    total_tokens = len(tokens)

    for token in string.split():
        if bool(JAPANESE_CHAR_PATTERN.search(token)):
            japanese_token += 1

    if japanese_token / total_tokens >= threshold:
        return True
    else:
        return False

    # return bool(JAPANESE_CHAR_PATTERN.search(string))

def fuzzy_partial_match(string: str, pattern: str, threshold: float = 95) -> bool:
    if fuzz.partial_ratio(string, pattern) >= threshold:
        return True
    else:
        return False