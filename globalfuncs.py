import base58

# global functions
# string to base58
def str_to_base58(text_input: str) -> str:
    bytes = text_input.encode('utf-8')
    base58_string = base58.b58encode(bytes)
    return base58_string.decode('utf-8')

# base58 to string
def base58_to_str(base58_string: str) -> str:
    base58_bytes = base58_string.encode('ascii')
    decoded_bytes = base58.b58decode(base58_bytes)
    return decoded_bytes.decode('utf-8')
