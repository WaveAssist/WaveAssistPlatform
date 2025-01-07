import openai


def test_openai_key(api_key):
    """
    Test if the provided OpenAI API key is valid.
    """
    try:
        # Set the OpenAI API key
        openai.api_key = api_key

        # Make a small test call to the OpenAI API
        response = openai.Engine.list()
        return True, response
    except openai.error.AuthenticationError:
        return False, "Invalid API key."
    except Exception as e:
        return False, f"An error occurred: {e}"


# Replace with your OpenAI API key
test_api_key = "REMOVED_CREDENTIAL"

# Test the API key
is_valid, result = test_openai_key(test_api_key)
print(is_valid)
print(result)
