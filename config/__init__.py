# __init__.py

# >>> import config
# >>> config.path
# PosixPath('/home/realpython/config/tic_tac_toe.toml')
#
# >>> config.tic_tac_toe
# {'user': {'player_x': {'color': 'blue'}, 'player_o': {'color': 'green'}},
#  'constant': {'board_size': 3},
#  'server': {'url': 'https://tictactoe.example.com'}}

import pathlib
import tomli

path = pathlib.Path(__file__).parent / "config.toml"
with path.open(mode="rb") as fp:
    cmconf = tomli.load(fp)
