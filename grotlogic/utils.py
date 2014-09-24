INVALID_HOSTS = {
    'localhost',
    '0.0.0.0'
}


def is_address_correct(address):
    return ':' in address and address.split(':')[0] not in INVALID_HOSTS
