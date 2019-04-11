from pypokerengine.api.game import setup_config, start_poker
from randomplayer import RandomPlayer
from raise_player import RaisedPlayer
from opponentPlayerByWX import opponent_player
from agent import agent

#TODO:config the config as our wish
config = setup_config(max_round=100000000000000000, initial_stack=100000000000000000000, small_blind_amount=10)
# config = setup_config(max_round=2, initial_stack=1000, small_blind_amount=10)



config.register_player(name="agent", algorithm=agent())
config.register_player(name="opponent_player", algorithm=opponent_player(6))


game_result = start_poker(config, verbose=0) #set verbose=0 to turn off the game messages
