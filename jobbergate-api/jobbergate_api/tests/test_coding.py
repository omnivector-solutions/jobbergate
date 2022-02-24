from jobbergate_api.coding import encode, decode


def test_encode_decode():
    """
    Test that a text string can be encode and then decoded back to the original text.
    """
    text = """
        Here's som test text.
        The encoding should really mangle it up.
        However, decoding should return it to the original form.
    """
    encoded_text = encode(text)
    assert encoded_text != text
    decoded_text = decode(encoded_text)
    assert decoded_text == text
