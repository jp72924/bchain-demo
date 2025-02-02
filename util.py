
def bitcoins_to_satoshis(bitcoins):
    """
    Converts an amount of bitcoins to satoshis.

    Args:
        bitcoins (float): The amount of bitcoins to convert.

    Returns:
        int: The equivalent amount in satoshis.

    Raises:
        ValueError: If the input is negative.
    """
    if bitcoins < 0:
        raise ValueError("Amount of bitcoins cannot be negative.")

    satoshis_per_bitcoin = 100000000
    return int(bitcoins * satoshis_per_bitcoin)


def satoshis_to_bitcoins(satoshis):
    """
    Converts an amount of satoshis to bitcoins.

    Args:
        satoshis (int): The amount of satoshis to convert.

    Returns:
        float: The equivalent amount in bitcoins.

    Raises:
        ValueError: If the input is negative.
    """
    if satoshis < 0:
        raise ValueError("Amount of satoshis cannot be negative.")

    satoshis_per_bitcoin = 100000000
    return satoshis / satoshis_per_bitcoin