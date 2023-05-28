import os

from dotenv import dotenv_values

config = {
    # **dotenv_values("../docker-elk/.env"),  # load shared development variables
    **dotenv_values(".env"),  # load sensitive variables
    **os.environ,  # override loaded values with environment variables
}
