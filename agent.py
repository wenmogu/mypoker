from pypokerengine.players import BasePokerPlayer
from time import sleep
import pprint
from pypokerengine.utils.card_utils import estimate_hole_card_win_rate, gen_cards
from math import floor
from random import random, randint
import csv
import os

class game_state:
  expectedPayoff = 0
  count = 0

  def __init__(self):
    self.expectedPayoff = 0.0;
    self.count = 0;

  def update(self, payoff):
    totalPayoff = self.expectedPayoff * self.count
    self.count += 1
    self.expectedPayoff = (totalPayoff + payoff) / self.count

  def display(self):
    return(str(self.expectedPayoff) + " " + str(self.count) + ",")

class Group30Player(BasePokerPlayer):
    RAISE_INDEX = 2
    CALL_INDEX = 1
    FOLD_INDEX = 0
    player_types = {
        "type1" : 0,
        "type2" : 1,
        "type3" : 2,
        "type4" : 3
    }
    winrate_ceiling_for_table_0 = 0.25
    winrate_ceiling_for_table_1 = 0.5
    winrate_ceiling_for_table_2 = 0.75
    winrate_ceiling_for_table_3 = 1

    def __init__(self):
        # super(object).__init__() # uncomment to run on python 3.6
        pass # ensure this is python 2.7 compatible
        self.sb_amount = 0

        # updated by round
        self.hole_card = []
        self.numberOfRounds = 0
        self.is_choose_aim_randomly = True

        # updated by street
        self.community_card = []
        self.winrate = 0
        self.winrate_for_each_street = {}
        self.at_street = ""
        self.is_at_street_start = True
        self.street_start_bet = 0
        self.street_raise_amount = 0
        self.street_raise_limit = 0
        self.aim_of_street = 0
        self.my_bet_at_start_of_street = {}

        # updated by turn
        # the lowest amount of money I now have to contribute to the pot. Dependent on opponent action.
        self.my_lowest_bet = 0
        # the amount of money I have contributed to the pot so far. Independent of opponent action.
        self.my_current_bet = 0
        self.no_of_me_raise_for_one_game = 0

        # to determine opponent type
        self.opponent_uuid = ""
        self.no_of_opponent_raise_for_one_game = 0
        self.no_of_opponent_call_before_using_up_raise_for_one_game = 0
        self.opponent_win_rate_for_one_game = 0
        self.no_of_opponent_raise_for_three_game = 0
        self.no_of_opponent_call_before_using_up_raise_for_three_game = 0
        self.no_of_opponent_fold = 0
        self.call_to_raise_ratio = 0 # start by using random table

        # for training purposes
        self.write_to_csv_counter = 0
        self.tables = []
        self.choose_opponent_table = 1 # initialize to be aggressive level 2
        self.opponent_tables = []
        w, h = 40, 133
        for f in range(5):
            for i in range(4):
                self.tables.append([[game_state() for i in range(w)] for j in range(h)])
            self.opponent_tables.append(self.tables)

    def __reset(self):
        # updated by round
        self.hole_card = []
        self.is_choose_aim_randomly = True

        # updated by street
        self.community_card = []
        self.winrate = 0
        self.winrate_for_each_street = {}
        self.at_street = ""
        self.is_at_street_start = True
        self.street_start_bet = 0
        self.street_raise_amount = 0
        self.street_raise_limit = 0
        self.aim_of_street = 0
        self.my_bet_at_start_of_street = {}

        # updated by turn
        self.my_lowest_bet = 2 * self.sb_amount
        self.my_current_bet = 0
        self.no_of_me_raise_for_one_game = 0

        # to determine opponent type
        self.no_of_opponent_raise_for_one_game = 0
        self.no_of_opponent_call_before_using_up_raise_for_one_game = 0
        self.opponent_win_rate_for_one_game = 0

    def declare_action(self, valid_actions, hole_card, round_state):
        achievable_aims_if_raise, achievable_aims_if_call = \
            self.__get_achievable_aims_at_this_turn(4 - self.no_of_me_raise_for_one_game,
                                                                  4 - self.no_of_opponent_raise_for_one_game)
        # for training purposes
        if (self.is_choose_aim_randomly):
            # i dont choose fold when i go by random aim.
            achievable_aim_of_max_payoff, max_payoff = self.__get_an_random_aim(achievable_aims_if_raise, achievable_aims_if_call)
            self.aim_of_street = achievable_aim_of_max_payoff
        else:
            achievable_aim_of_max_payoff, max_payoff = self.__get_aim_of_max_payoff(achievable_aims_if_raise, achievable_aims_if_call)
            self.aim_of_street = achievable_aim_of_max_payoff
        if achievable_aim_of_max_payoff in achievable_aims_if_raise:
            if achievable_aim_of_max_payoff == 0:
                action = self.__get_fold_action(valid_actions)
            else:
                if achievable_aim_of_max_payoff == self.my_current_bet:
                    action = self.__get_call_action(valid_actions)
                else:
                    action = self.__get_raise_action(valid_actions)
        elif achievable_aim_of_max_payoff in achievable_aims_if_call:
            # i am at the street start, and i am small blind, and the action is not obtainable by me raising
            # so i can only call to obtain my desirable aim
            if achievable_aim_of_max_payoff == 0:
                action = self.__get_fold_action(valid_actions)
            else:
                action = self.__get_call_action(valid_actions)

        if not action:
            action = self.__get_call_action(valid_actions)
        # print("my_current_bet: " + str(self.my_current_bet))
        # print("achievable aim with max payoff: " + str(achievable_aim_of_max_payoff))
        # print(action)
        return action

    def receive_game_start_message(self, game_info):
        for seat in game_info["seats"]:
            if seat["uuid"] != self.uuid:
                self.opponent_uuid = seat["uuid"]
        self.sb_amount = game_info["rule"]["small_blind_amount"]
        self.my_lowest_bet = 2 * self.sb_amount

        # for training purposes
        countExists = os.path.isfile('round_count.txt')
        if not countExists:
            print("round_count.txt file is not found")
        else:
            with open('round_count.txt', 'r') as txtFile:
                if txtFile.mode == 'r':
                    round_count = txtFile.read()
                    self.numberOfRounds = int(round_count, 10)

        # update opponent tables 1,2,3,4 to opponent types 2,4,6,8
        for f in range(1, 5):
            file_name = "Group30Player_oppo_" + str(f * 2) + "_combined.csv"
            exists = os.path.isfile(file_name)
            if not exists:
                print(file_name + " csv is not found")
            else:
                with open(file_name, 'r') as csvFile:
                    stored_table = list(csv.reader(csvFile))
                    # update for table type 1
                    for i in range(1, 133):
                        for j in range(0, 40):
                            parsedInput = stored_table[i][j].split(" ")
                            self.opponent_tables[f][0][i-1][j].expectedPayoff = float(parsedInput[0])
                            self.opponent_tables[f][0][i-1][j].count = int(parsedInput[1])
                    # update for table type 2
                    for i in range(135, 267):
                        for j in range(0, 40):
                            parsedInput = stored_table[i][j].split(" ")
                            self.opponent_tables[f][1][i-135][j].expectedPayoff = float(parsedInput[0])
                            self.opponent_tables[f][1][i-135][j].count = int(parsedInput[1])
                    # update for table type 3
                    for i in range(269, 401):
                        for j in range(0, 40):
                            parsedInput = stored_table[i][j].split(" ")
                            self.opponent_tables[f][2][i-269][j].expectedPayoff = float(parsedInput[0])
                            self.opponent_tables[f][2][i-269][j].count = int(parsedInput[1])
                    # update for table type 4
                    for i in range(403, 535):
                        for j in range(0, 40):
                            parsedInput = stored_table[i][j].split(" ")
                            self.opponent_tables[f][3][i-403][j].expectedPayoff = float(parsedInput[0])
                            self.opponent_tables[f][3][i-403][j].count = int(parsedInput[1])
                csvFile.close()
            # checking if table populated correctly
            # print('\n'.join([''.join(['{:4}'.format(state.display()) for state in row]) for row in self.opponent_tables[1][0]]))
            # print('-----------------------------')
            # print('\n'.join([''.join(['{:4}'.format(state.display()) for state in row]) for row in self.opponent_tables[1][1]]))
        pass

    def receive_round_start_message(self, round_count, hole_card, seats):
        self.hole_card = gen_cards(hole_card)
        r = random()
        if r > 0.618:
            self.is_choose_aim_randomly = False
        else:
            self.is_choose_aim_randomly = True

    def receive_street_start_message(self, street, round_state):
        self.community_card = gen_cards(round_state["community_card"])
        self.winrate = estimate_hole_card_win_rate(2000, 2, self.hole_card, self.community_card)
        self.winrate_for_each_street[street] = self.winrate
        # print(self.winrate)
        self.at_street = street
        self.is_at_street_start = True
        self.aim_of_street = 0

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

        self.my_bet_at_start_of_street[street] = self.my_current_bet

    def receive_game_update_message(self, action, round_state):
        pot = round_state["pot"]["main"]["amount"]
        self.__update_at_each_turn(action, round_state["street"], pot)
        self.is_at_street_start = False

    def receive_round_result_message(self, winners, hand_info, round_state):
        self.numberOfRounds += 1
        if hand_info:
            # opponent_hole_card = self.__get_opponent_hole_card(hand_info)
            opponent_hole_card = gen_cards(self.__get_opponent_hole_card(hand_info))
            self.opponent_win_rate_for_one_game = estimate_hole_card_win_rate(1000, 2, opponent_hole_card, self.community_card)

        # NOT for training purposes
        self.__update_oppo_table_type(round_state)
        self.__reset()
        pass

    def __update_oppo_table_type(self, round_state):
        if (round_state["action_histories"]["preflop"][0]["uuid"] == self.opponent_uuid):
            opponent_sb = True
        else:
            opponent_sb = False

        if (self.no_of_opponent_raise_for_one_game != 0):
            call_to_raise_ratio = 1.0 * self.no_of_opponent_call_before_using_up_raise_for_one_game / self.no_of_opponent_raise_for_one_game
        else:
            call_to_raise_ratio = 0
        
        if (opponent_sb):
            if (call_to_raise_ratio >= 0 and call_to_raise_ratio <= 0.75):
                new_choose_opponent_table = 1
            elif (call_to_raise_ratio >= 1 and call_to_raise_ratio <= 1.5):
                new_choose_opponent_table = 2
            elif (call_to_raise_ratio >= 1.7 and call_to_raise_ratio <= 3):
                new_choose_opponent_table = 3
            elif (call_to_raise_ratio >= 4 and call_to_raise_ratio <= 8):
                new_choose_opponent_table = 4
            # print("ratio in SB is: ", call_to_raise_ratio)
            # print("opponent table in SB is: ", self.choose_opponent_table)
        else:
            if (call_to_raise_ratio >= 0 and call_to_raise_ratio <= 0.4):
                new_choose_opponent_table = 1
            elif (call_to_raise_ratio >= 0.5 and call_to_raise_ratio <= 0.8):
                new_choose_opponent_table = 2
            elif (call_to_raise_ratio >= 1 and call_to_raise_ratio <= 1.5):
                new_choose_opponent_table = 3
            elif (call_to_raise_ratio >= 2 and call_to_raise_ratio <= 4):
                new_choose_opponent_table = 4
            # print("ratio in BB is: ", call_to_raise_ratio)
            # print("opponent table in BB is: ", self.choose_opponent_table)

        # remove ability to switch to table 0 initially
        # if (new_choose_opponent_table * 2 - self.choose_opponent_table * 2 >= 4):
            # new_choose_opponent_table = 0

        self.choose_opponent_table = new_choose_opponent_table
        # print("opponent type is: ", self.choose_opponent_table)

    def __locate_row_number_of_street_in_table(self, street):
        # assume bet before each turn is correct
        if street == "preflop":
            return 0
        elif street == "flop":
            my_bet_at_start_of_flop = self.my_bet_at_start_of_street["flop"]
            # print("bet before flop is: ", my_bet_at_start_of_flop)
            return my_bet_at_start_of_flop / 10 / 2
        elif street == "turn":
            my_bet_at_start_of_flop = self.my_bet_at_start_of_street["flop"]
            row_number_at_flop = my_bet_at_start_of_flop / 10 / 2
            my_bet_at_start_of_turn = self.my_bet_at_start_of_street["turn"]
            # print("bet before turn is: ", my_bet_at_start_of_turn)
            return row_number_at_flop * 4 + my_bet_at_start_of_turn / 10 / 2
        elif street == "river":
            my_bet_at_start_of_flop = self.my_bet_at_start_of_street["flop"]
            row_number_at_flop = my_bet_at_start_of_flop / 10 / 2
            my_bet_at_start_of_turn = self.my_bet_at_start_of_street["turn"]
            row_number_at_turn = row_number_at_flop * 4 + my_bet_at_start_of_turn / 10 / 2
            my_bet_at_start_of_river = self.my_bet_at_start_of_street["river"]
            # print("bet before river is: ", my_bet_at_start_of_turn)
            index_for_bet = int(my_bet_at_start_of_turn / 10)
            if (index_for_bet % 4 != 0):
                return (row_number_at_turn * 5 + (index_for_bet + 2) / 4 - 1 + (row_number_at_turn / 5 -1) * 2)
            return (row_number_at_turn * 5 + index_for_bet / 4 - 1 + (row_number_at_turn / 5 - 1) * 2)

    def __findTableType(self, street):
        winrate_at_street = self.winrate_for_each_street[street]

        if winrate_at_street <= Group30Player.winrate_ceiling_for_table_0:
            return 0
        elif winrate_at_street <= Group30Player.winrate_ceiling_for_table_1:
            return 1
        elif winrate_at_street <= Group30Player.winrate_ceiling_for_table_2:
            return 2
        else:
            return 3

    def __add_to_array(self, array, bid):
        if (bid["uuid"] == self.uuid):
            if (bid["action"] == "FOLD"):
                array.append(-1)
            else:
                array.append(bid["amount"])

    def __get_ordered_action_list(self, valid_actions):
        action_index_list = [-1, -1, -1];
        # always in the order of fold, call, raise.
        # if the action is not available, the index will be -1.
        for i in valid_actions:
            if i["action"] == "raise":
                action_index_list[Group30Player.RAISE_INDEX] = i
            if i["action"] == "call":
                action_index_list[Group30Player.CALL_INDEX] = i
            else:
                action_index_list[Group30Player.FOLD_INDEX] = i

        return action_index_list

    def __get_raise_action(self, valid_actions):
        action_index_list = self.__get_ordered_action_list(valid_actions)
        action_info = action_index_list[Group30Player.RAISE_INDEX]
        if action_info != -1:
            return action_info["action"]
        return None

    def __get_call_action(self, valid_actions):
        action_index_list = self.__get_ordered_action_list(valid_actions)
        action_info = action_index_list[Group30Player.CALL_INDEX]
        if action_info != -1:
            return action_info["action"]
        return None

    def __get_fold_action(self, valid_actions):
        action_index_list = self.__get_ordered_action_list(valid_actions)
        action_info = action_index_list[Group30Player.FOLD_INDEX]
        if action_info != -1:
            return action_info["action"]
        return None

    def __get_achievable_aims_at_this_turn(self, number_of_raises_i_hv, number_of_raises_oppo_hv):
            if self.is_at_street_start:
                max_raise_if_i_raise, max_raise_if_i_call = \
                    self.__get_max_raise_at_this_turn(number_of_raises_i_hv, number_of_raises_oppo_hv)
                max_bet_aim_if_i_raise = min(self.my_lowest_bet + max_raise_if_i_raise, self.street_start_bet + self.street_raise_limit)
                max_bet_aim_if_i_call = min(self.my_lowest_bet + max_raise_if_i_call, self.street_start_bet + self.street_raise_limit)

                list_of_aims_i_can_achieve_if_raise = [0] + list(filter(lambda aim: aim <= max_bet_aim_if_i_raise,
                                                                        [i * self.street_raise_amount + self.my_lowest_bet for i in range(5)]))
                list_of_aims_i_can_achieve_if_call = [0] + list(filter(lambda aim: aim <= max_bet_aim_if_i_call,
                                                                       [i * self.street_raise_amount + self.my_lowest_bet for i in range(5)]))
                return list_of_aims_i_can_achieve_if_raise, list_of_aims_i_can_achieve_if_call
            else:
                # print("(" + str(number_of_raises_i_hv) + ", " + str(number_of_raises_oppo_hv) + ")")

                max_raise, max_raise_if_i_call = self.__get_max_raise_at_this_turn(number_of_raises_i_hv, number_of_raises_oppo_hv)
                max_bet_aim = min(self.my_lowest_bet + max_raise, self.street_start_bet + self.street_raise_limit)
                list_of_aims_i_can_achieve = [0] + list(filter(lambda aim: aim <= max_bet_aim,
                                                               [i * self.street_raise_amount + self.my_lowest_bet for i in range(5)]))
                # aimstr = ""
                # for i in range(len(list_of_aims_i_can_achieve)):
                #     aimstr += str(list_of_aims_i_can_achieve[i]) + ", "
                # print("list_of_aims_i_can_achieve: " + aimstr)
                return list_of_aims_i_can_achieve, []

    def __get_aim_of_max_payoff(self, list_of_aims_i_can_achieve_if_raise, list_of_aims_i_can_achieve_if_call):
        merged_aim_list = list_of_aims_i_can_achieve_if_raise + \
                          list(set(list_of_aims_i_can_achieve_if_call) - set(list_of_aims_i_can_achieve_if_raise))
        if self.aim_of_street == 0 or (self.aim_of_street not in merged_aim_list):
            # in this version, we do not consider the probability of chaning to another type of agent in the next street
            table_to_look_at = self.__findTableType(self.at_street)

            my_row_number = self.__locate_row_number_of_street_in_table(self.at_street)
            aim_to_expected_payoff = {}
            for aim in merged_aim_list:
                if aim == 0:
                    aim_to_expected_payoff[0] = -self.my_current_bet
                else:
                    # print("my table to look at: " + str(table_to_look_at))
                    # print("my row number: " + str(my_row_number))
                    # print("my aim: " + str(int(aim/10)))
                    try:
                        aim_game_state = self.opponent_tables[self.choose_opponent_table][table_to_look_at][int(my_row_number)][int(aim/10)]
                        aim_to_expected_payoff[aim] = aim_game_state.expectedPayoff
                    except:
                        print(str(len(self.opponent_tables[self.choose_opponent_table])) + " " + str(len(self.opponent_tables[0])) + " " + str(len(self.opponent_tables[0][0])))
                        print("my table to look at: " + str(table_to_look_at))
                        print("my row number: " + str(my_row_number))
                        print("my aim: " + str(int(aim/10)))
                        # print(sys.exc_info()[0])
                        return self.__get_an_random_aim(list_of_aims_i_can_achieve_if_raise, list_of_aims_i_can_achieve_if_call)

            max_payoff = max(aim_to_expected_payoff.values())
            aims_of_max_payoff = []
            for key, value in aim_to_expected_payoff.items():
                if value == max_payoff:
                    aims_of_max_payoff.append(key)
            #return the one that is closest to achieve
            return min(aims_of_max_payoff), max_payoff
        else:
            return self.aim_of_street, 0

    def __get_an_random_aim(self, list_of_aims_i_can_achieve_if_raise, list_of_aims_i_can_achieve_if_call):
        merged_aim_list = list_of_aims_i_can_achieve_if_raise + \
                          list(set(list_of_aims_i_can_achieve_if_call) - set(list_of_aims_i_can_achieve_if_raise))
        if self.aim_of_street == 0 or (self.aim_of_street not in merged_aim_list):
            l = len(merged_aim_list) - 1
            if l <= 0:
              print("not possibleeeeeee that i have no aims available, I should always have at least 2 aims!")
              return ""
            else:
              r = randint(1, l)
              return merged_aim_list[r], 0
        else:
            return self.aim_of_street, 0

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
                self.my_current_bet = (pot - raise_amount) / 2 + raise_amount

            elif player_action == "call":
                self.my_lowest_bet = pot / 2
                self.my_current_bet = pot / 2
        else:
            if player_action == "fold":
                self.no_of_opponent_fold += 1
            elif player_action == "raise":
                self.no_of_opponent_raise_for_one_game += 1
                self.my_lowest_bet += raise_amount
            elif player_action == "call":
                self.my_lowest_bet = pot / 2
                self.my_current_bet = pot / 2
                if self.no_of_opponent_raise_for_one_game < 4:
                    self.no_of_opponent_call_before_using_up_raise_for_one_game += 1

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
    return Group30Player()
