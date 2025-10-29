"""Helper module with utility functions."""


def get_greeting_message(name: str = "world") -> dict:
    """
    Generate a greeting message.

    Args:
        name: The name to greet (default: "world")

    Returns:
        A dictionary with greeting details
    """
    return {"greeting": f"Hello, {name}!", "source": "helper module", "status": "success"}


def multiply_numbers(a: int, b: int) -> int:
    """
    Simple function to test module imports.

    Args:
        a: First number
        b: Second number

    Returns:
        The product of a and b
    """
    return a * b
