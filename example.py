from pypokerengine.api.game import setup_config, start_poker
from randomplayer import RandomPlayer
from raise_player import RaisedPlayer
from opponentPlayerByWX import opponent_player

#TODO:config the config as our wish
config = setup_config(max_round=2, initial_stack=10000, small_blind_amount=10)



config.register_player(name="raised_player", algorithm=RaisedPlayer())
config.register_player(name="opponent_player", algorithm=opponent_player(6))


game_result = start_poker(config, verbose=1) #set verbose=0 to turn off the game messages
