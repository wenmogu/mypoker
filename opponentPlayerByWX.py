from pypokerengine.players import BasePokerPlayer
import time
import pprint
from pypokerengine.utils.card_utils import estimate_hole_card_win_rate, gen_cards
from math import floor
from random import random
from pypokerengine.engine.card import Card
from pypokerengine.engine.hand_evaluator import HandEvaluator

class opponent_player(BasePokerPlayer):
    RAISE_INDEX = 2
    CALL_INDEX = 1
    FOLD_INDEX = 0

    def __init__(self, level_of_aggressiveness):
        assert(type(level_of_aggressiveness) == int
               and (level_of_aggressiveness >= 0)
               and (level_of_aggressiveness <= 10))
        super(object).__init__()
        # threshhold_winrate_to_raise can be 0, 0.1, 0.2 ... until 1,
        # it is proportional to the last integer digit of input level_of_aggressiveness
        self.threshhold_winrate_to_raise = 1 - floor(level_of_aggressiveness % 10) / 10

        self.sb_amount = 0
        self.gameStartTime = time.time()

        # updated by round
        self.hole_card = []
        self.averageRoundTime = 0
        self.numberOfRounds = 0

        # updated by street
        self.community_card = []
        self.winrate = 0
        self.is_at_street_start = True
        self.street_start_bet = 0
        self.street_raise_amount = 0
        self.street_raise_limit = 0

        # updated by turn
        # the lowest amount of money I now have to contribute to the pot. Dependent on opponent action.
        self.my_lowest_bet = 0
        # the amount of money I have contributed to the pot so far. Independent of opponent action.
        self.my_current_bet = 0
        self.no_of_me_raise_for_one_game = 0

        # to determine opponent type
        self.no_of_opponent_raise_for_one_game = 0
        self.no_of_opponent_call_before_using_up_raise_for_one_game = 0
        self.opponent_win_rate_for_one_game = 0
        self.no_of_opponent_raise_for_three_game = 0
        self.no_of_opponent_call_before_using_up_raise_for_three_game = 0
        self.no_of_opponent_fold = 0


    def __reset(self):
        # updated by round
        self.hole_card = []

        # updated by street
        self.community_card = []
        self.winrate = 0
        self.is_at_street_start = True
        self.street_start_bet = 0
        self.street_raise_amount = 0
        self.street_raise_limit = 0

        # updated by turn
        self.my_lowest_bet = 2 * self.sb_amount
        self.my_current_bet = 0
        self.no_of_me_raise_for_one_game = 0

        # to determine opponent type
        self.no_of_opponent_raise_for_one_game = 0
        self.no_of_opponent_call_before_using_up_raise_for_one_game = 0
        self.opponent_win_rate_for_one_game = 0

    def declare_action(self, valid_actions, hole_card, round_state):
        achievable_aims = self.__get_achievable_aims_at_this_turn(4 - self.no_of_me_raise_for_one_game,
                                                                  4 - self.no_of_opponent_raise_for_one_game)
        print(str(achievable_aims))
        if self.winrate > self.threshhold_winrate_to_raise:
            action = self.__get_raise_action(valid_actions)
        else:
            action = self.__get_call_action(valid_actions)

        if not action:
            action = self.__get_call_action(valid_actions)
        if action == "raise" and self.no_of_me_raise_for_one_game >= 4:
            print("ILLEEEEGALLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLl")
            print("valid_actions supplied to this illegal move: ")
            pprint.pprint(valid_actions)
        return action

    def receive_game_start_message(self, game_info):
        self.sb_amount = game_info["rule"]["small_blind_amount"]
        self.my_lowest_bet = 2 * self.sb_amount

    def receive_round_start_message(self, round_count, hole_card, seats):
        self.hole_card = gen_cards(hole_card)


    def receive_street_start_message(self, street, round_state):
        self.community_card = gen_cards(round_state["community_card"])
        self.winrate = estimate_hole_card_win_rate(2000, 2, self.hole_card, self.community_card)
        self.is_at_street_start = True

        if street == "preflop":
            self.street_start_bet = 0
            sb_player = round_state["seats"][round_state["small_blind_pos"]]
            if sb_player["uuid"] == self.uuid:
                self.my_current_bet = self.sb_amount
            else:
                self.my_current_bet = self.sb_amount * 2
        else:
            self.street_start_bet = self.my_lowest_bet
        self.street_raise_amount, self.street_raise_limit = self.__round_raise_amount(self.sb_amount, street)

    def receive_game_update_message(self, action, round_state):
        pot = round_state["pot"]["main"]["amount"]
        self.__update_at_each_turn(action, round_state["street"], pot)
        self.is_at_street_start = False

    def receive_round_result_message(self, winners, hand_info, round_state):
        totalTime = self.averageRoundTime * self.numberOfRounds
        thisRoundTime = time.time() - self.gameStartTime
        self.numberOfRounds += 1
        self.averageRoundTime = (totalTime + thisRoundTime) / self.numberOfRounds
        # print(self.averageRoundTime)
        if hand_info:
            # opponent_hole_card = self.__get_opponent_hole_card(hand_info)
            opponent_hole_card = gen_cards(self.__get_opponent_hole_card(hand_info))
            self.opponent_win_rate_for_one_game = estimate_hole_card_win_rate(1000, 2, opponent_hole_card, self.community_card)

        self.__reset()

    def __get_ordered_action_list(self, valid_actions):
        action_index_list = [-1, -1, -1];
        # always in the order of fold, call, raise.
        # if the action is not available, the index will be -1.
        for i in valid_actions:
            if i["action"] == "raise":
                action_index_list[opponent_player.RAISE_INDEX] = i
            if i["action"] == "call":
                action_index_list[opponent_player.CALL_INDEX] = i
            else:
                action_index_list[opponent_player.FOLD_INDEX] = i

        return action_index_list

    def __get_raise_action(self, valid_actions):
        action_index_list = self.__get_ordered_action_list(valid_actions)
        action_info = action_index_list[opponent_player.RAISE_INDEX]
        if action_info != -1:
            return action_info["action"]
        return None

    def __get_call_action(self, valid_actions):
        action_index_list = self.__get_ordered_action_list(valid_actions)
        action_info = action_index_list[opponent_player.CALL_INDEX]
        if action_info != -1:
            return action_info["action"]
        return None

    def __get_fold_action(self, valid_actions):
        action_index_list = self.__get_ordered_action_list(valid_actions)
        action_info = action_index_list[opponent_player.FOLD_INDEX]
        if action_info != -1:
            return action_info["action"]
        return None

    def __get_achievable_aims_at_this_turn(self, number_of_raises_i_hv, number_of_raises_oppo_hv):
        if self.is_at_street_start:
            max_raise_if_i_raise, max_raise_if_i_call = \
                self.__get_max_raise_at_this_turn(number_of_raises_i_hv, number_of_raises_oppo_hv)
            print("(" + str(number_of_raises_i_hv) + ", " + str(number_of_raises_oppo_hv) + ")")
            print(max_raise_if_i_raise)
            print(max_raise_if_i_call)
            max_bet_aim_if_i_raise = min(self.my_lowest_bet + max_raise_if_i_raise, self.street_start_bet + self.street_raise_limit)
            max_bet_aim_if_i_call = min(self.my_lowest_bet + max_raise_if_i_call, self.street_start_bet + self.street_raise_limit)

            list_of_aims_i_can_achieve_if_raise = [0] + list(filter(lambda aim: aim <= max_bet_aim_if_i_raise,
                                                           [i * self.street_raise_amount + self.my_lowest_bet for i in range(5)]))
            list_of_aims_i_can_achieve_if_call = [0] + list(filter(lambda aim: aim <= max_bet_aim_if_i_call,
                                                           [i * self.street_raise_amount + self.my_lowest_bet for i in range(5)]))
            return list_of_aims_i_can_achieve_if_raise, list_of_aims_i_can_achieve_if_call
        else:
            print("(" + str(number_of_raises_i_hv) + ", " + str(number_of_raises_oppo_hv) + ")")

            max_raise, max_raise_if_i_call = self.__get_max_raise_at_this_turn(number_of_raises_i_hv, number_of_raises_oppo_hv)
            max_bet_aim = min(self.my_lowest_bet + max_raise, self.street_start_bet + self.street_raise_limit)
            list_of_aims_i_can_achieve = [0] + list(filter(lambda aim: aim <= max_bet_aim,
                                                           [i * self.street_raise_amount + self.my_lowest_bet for i in range(5)]))
            aimstr = ""
            for i in range(len(list_of_aims_i_can_achieve)):
                aimstr += str(list_of_aims_i_can_achieve[i]) + ", "
            print("list_of_aims_i_can_achieve: " + aimstr)
            return list_of_aims_i_can_achieve, []

    def __get_max_raise_at_this_turn(self, number_of_raises_i_hv, number_of_raises_oppo_hv):
        if min(number_of_raises_oppo_hv, number_of_raises_i_hv) >= 2:
            raise_amount = self.street_raise_amount * (number_of_raises_i_hv + number_of_raises_oppo_hv)
            return raise_amount, raise_amount
        elif number_of_raises_i_hv == number_of_raises_oppo_hv:
            raise_amount = self.street_raise_amount * (number_of_raises_i_hv + number_of_raises_oppo_hv)
            return raise_amount, raise_amount
        else:
            if self.is_at_street_start:
                # return max_raise_if_i_raise, max_raise_if_i_call
                if number_of_raises_i_hv == 0:
                    return 0, self.street_raise_amount * 1
                elif number_of_raises_oppo_hv == 0:
                    return self.street_raise_amount * 1, 0
                elif number_of_raises_i_hv == 1:
                    return self.street_raise_amount * 2, self.street_raise_amount * 3
                elif number_of_raises_oppo_hv == 1:
                    return self.street_raise_amount * 3, self.street_raise_amount * 2
                else:
                    print("huehuehuehue this is totally illegal...somebody is at -1")
                    return self.street_raise_amount * number_of_raises_i_hv, self.street_raise_amount * number_of_raises_i_hv
            else:
                # if i m not at the street start there is only one option for me to continue.
                if number_of_raises_i_hv == 0:
                    return self.street_raise_amount * 1, 0
                elif number_of_raises_oppo_hv == 0:
                    return self.street_raise_amount * 1, 0
                elif number_of_raises_i_hv == 1:
                    return self.street_raise_amount * 2, 0
                elif number_of_raises_oppo_hv == 1:
                    return self.street_raise_amount * 3, 0
                else:
                    print("huehuehuehue this is totally illegal...somebody is at -1")
                    return self.street_raise_amount * number_of_raises_i_hv, self.street_raise_amount * number_of_raises_i_hv

    def __round_raise_amount(self, sb_amount, street):
        if street == "preflop" or street == "flop":
            return sb_amount * 2, sb_amount * 2 * 4
        else:
            return sb_amount * 4 ,sb_amount * 4 * 4

    def __update_at_each_turn(self, action, street, pot):
        player_action = action["action"]
        raise_amount, raise_limit = self.__round_raise_amount(self.sb_amount, street)

        if action["player_uuid"] == self.uuid:
            if player_action == "raise":
                self.no_of_me_raise_for_one_game += 1
                self.my_lowest_bet += raise_amount
                self.my_current_bet += raise_amount

            elif player_action == "call":
                self.my_lowest_bet = pot / 2
                self.my_current_bet = pot / 2
        else:
            if player_action == "fold":
                self.no_of_opponent_fold += 1
            elif player_action == "raise":
                self.no_of_opponent_raise_for_one_game += 1
                self.my_lowest_bet += raise_amount
            else:
                if self.no_of_opponent_raise_for_one_game < 4:
                    self.no_of_opponent_call_before_using_up_raise_for_one_game += 1
                    self.my_lowest_bet = pot / 2

    def __get_opponent_hole_card(self, hand_info):
        for item in hand_info or []:
            if item["uuid"] != self.uuid:
                return item["hand"]["card"]

    # def __get_opponent_hole_card(self, hand_info):
    #     oppo_hand_strength, hole_high_rank, hole_low_rank = self.__get_opponent_hand_info(hand_info)
    #     for i in range(1, 4):
    #         for j in range(1, 4):
    #             opponent_hole_card_guess = gen_cards([Card.SUIT_MAP[2**i] + hole_high_rank,
    #                                   Card.SUIT_MAP[2**j] + hole_low_rank])
    #             opponent_hand_guess = HandEvaluator.eval_hand(opponent_hole_card_guess, self.community_card)
    #             row_strength_guess = self.__hand_evaluator_mask_hand_strength(opponent_hand_guess)
    #             strength_guess = HandEvaluator.HAND_STRENGTH_MAP[row_strength_guess]
    #             if strength_guess == oppo_hand_strength:
    #                 return opponent_hole_card_guess
    #     return []
    #
    # def __get_opponent_hand_info(self, hand_info):
    #     for item in hand_info or []:
    #         if item["uuid"] != self.uuid:
    #             return (item["hand"]["hand"]["strength"],
    #                         Card.RANK_MAP[item["hand"]["hole"]["high"]],
    #                           Card.RANK_MAP[item["hand"]["hole"]["low"]])
    #
    # # copied from hand_evaluator.py, as it is a instance method
    # def __hand_evaluator_mask_hand_strength(self, bit):
    #     mask = 511 << 16
    #     return (bit & mask) >> 8  # 511 = (1 << 9) -1

def setup_ai():
    return opponent_player()