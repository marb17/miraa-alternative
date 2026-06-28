import re

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


def contains_japanese(string: str) -> bool:
    if type(string) is not str:
        return False

    return bool(JAPANESE_CHAR_PATTERN.search(string))
