from pypokerengine.players import BasePokerPlayer
from time import sleep
import pprint
from pypokerengine.utils.card_utils import estimate_hole_card_win_rate, gen_cards
from math import floor
from random import random
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

class agent(BasePokerPlayer):
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
        super(object).__init__()
        self.sb_amount = 0

        # updated by round
        self.hole_card = []
        self.numberOfRounds = 0

        # updated by street
        self.community_card = []
        self.winrate = 0
        self.winrate_for_each_street = {}
        self.at_street = ""
        self.is_at_street_start = True
        self.street_start_bet = 0
        self.street_raise_amount = 0
        self.street_raise_limit = 0
        self.my_bet_at_start_of_street = {}

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

        # for training purposes
        self.write_to_csv_counter = 0
        self.tables = []
        for i in range(4):
            self.tables.append([[game_state() for i in range(34)] for j in range(80)])

    def __reset(self):
        # updated by round
        self.hole_card = []

        # updated by street
        self.community_card = []
        self.winrate = 0
        self.winrate_for_each_street = {}
        self.at_street = ""
        self.is_at_street_start = True
        self.street_start_bet = 0
        self.street_raise_amount = 0
        self.street_raise_limit = 0
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
        # print(str(achievable_aims_if_raise) + " " + str(achievable_aims_if_call))
        r = random()
        if (r > 0):
            achievable_aim_of_max_payoff, max_payoff = self.__get_aim_of_max_payoff(achievable_aims_if_raise, achievable_aims_if_call)
        else:
            achievable_aim_of_max_payoff, max_payoff = self.__get_an_random_aim(achievable_aims_if_raise, achievable_aims_if_call)
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
        self.sb_amount = game_info["rule"]["small_blind_amount"]
        self.my_lowest_bet = 2 * self.sb_amount

        with open('round_count.txt', 'r') as txtFile:
            if txtFile.mode == 'r':
                round_count = txtFile.read()
                self.numberOfRounds = int(round_count, 10)
        # for training purposes
        exists = os.path.isfile('qLearning.csv')
        if not exists:
            print("qLearning.csv file is not found")
        else:
            with open('qLearning.csv', 'r') as csvFile:
                stored_table = list(csv.reader(csvFile))
                # update for table type 1
                for i in range(1, 80):
                    for j in range(0, 34):
                        parsedInput = stored_table[i][j].split(" ")
                        self.tables[0][i-1][j].expectedPayoff = float(parsedInput[0])
                        self.tables[0][i-1][j].count = int(parsedInput[1])
                # update for table type 2
                for i in range(82, 161):
                    for j in range(0, 34):
                        parsedInput = stored_table[i][j].split(" ")
                        self.tables[1][i-82][j].expectedPayoff = float(parsedInput[0])
                        self.tables[1][i-82][j].count = int(parsedInput[1])
                # update for table type 3
                for i in range(163, 242):
                    for j in range(0, 34):
                        parsedInput = stored_table[i][j].split(" ")
                        self.tables[2][i-163][j].expectedPayoff = float(parsedInput[0])
                        self.tables[2][i-163][j].count = int(parsedInput[1])
                # update for table type 4
                for i in range(244, 323):
                    for j in range(0, 34):
                        parsedInput = stored_table[i][j].split(" ")
                        self.tables[3][i-244][j].expectedPayoff = float(parsedInput[0])
                        self.tables[3][i-244][j].count = int(parsedInput[1])
            csvFile.close()
        # print('\n'.join([''.join(['{:4}'.format(state.display()) for state in row]) for row in self.tables[0]]))
        # print('\n'.join([''.join(['{:4}'.format(state.display()) for state in row]) for row in self.tables[1]]))
        pass

    def receive_round_start_message(self, round_count, hole_card, seats):
        self.hole_card = gen_cards(hole_card)

    def receive_street_start_message(self, street, round_state):
        self.community_card = gen_cards(round_state["community_card"])
        self.winrate = estimate_hole_card_win_rate(2000, 2, self.hole_card, self.community_card)
        self.winrate_for_each_street[street] = self.winrate
        print(self.winrate)
        self.at_street = street
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

        # for training purposes
        preflop = [0]
        flop = [0]
        turn = [0]
        river = [0]
        for session in round_state["action_histories"]:
            if (session == "preflop"):
                for bid in round_state["action_histories"]["preflop"]:
                    self.__add_to_array(preflop, bid)
            if (session == "flop"):
                for bid in round_state["action_histories"]["flop"]:
                    self.__add_to_array(flop, bid)
        
            if (session == "turn"):
                for bid in round_state["action_histories"]["turn"]:
                    self.__add_to_array(turn, bid)
          
            if (session == "river"):
                for bid in round_state["action_histories"]["river"]:
                    self.__add_to_array(river, bid)


        earning = max(preflop) + max(flop) + max(turn) + max(river)
        if (winners[0]["uuid"] != self.uuid):
            # print("player lost")
            earning = -earning
        
        nextRow = 0
        prevIndex = 0

        tableType = self.__findTableType("preflop")
        # print("type is", tableType)

        if -1 in preflop:
            # only update fold action, nothing else
            print("fold is called at preflop")
            # self.table1[0][0].update(earning)
        elif(len(preflop) > 1):
            index = max(preflop) / 10
            self.tables[tableType][0][int(index)].update(earning)
            nextRow = index / 2
            prevIndex = index
        print("after preflop nextRow is: ", nextRow)

        # nextRow is either 1, 2, 3 or 4 here
        if -1 in flop:
            print("fold is called at flop")
            # self.table1[nextRow][0].update(earning)
        elif (len(flop) > 1):
            tableType = self.__findTableType("flop")
            # index is the new value / 10 that is bidded in that round
            index = max(flop) / 10 + prevIndex
            self.tables[tableType][int(nextRow)][int(index)].update(earning)
            nextRow = (nextRow * 6 + index + 2) / 2
            prevIndex = index
        print("after flop nextRow is: ", nextRow)

        # nextRow is either 9, 10, 11, ..., 20
        if -1 in turn:
            print("fold is called at turn")
            # self.table1[nextRow][0].update(earning)
        elif (len(turn) > 1):
            tableType = self.__findTableType("turn")
            # index is the new value / 10 that is bidded in that round
            index = max(turn) / 10 + prevIndex
            self.tables[tableType][int(nextRow)][int(index)].update(earning)
            nextRow = (nextRow * 6 + index + 2) / 2
            prevIndex = index 
        print("after turn nextRow is: ", nextRow)

        # nextRow will be 21, 22, ..., 80
        if -1 in river:
            print("fold is called at river")
            # self.table1[nextRow][0].update(earning)
        elif (len(river) > 1):
            tableType = self.__findTableType("river")
            index = max(river) / 10 + prevIndex
            self.tables[tableType][int(nextRow)][int(index)].update(earning)

        # print("-------------------------------")
        # print('\n'.join([''.join(['{:4}'.format(state.display()) for state in row]) for row in self.table]))
        # print("-------------------------------")
        self.write_to_csv_counter += 1

        # write to the csv file every 50 times
        if (self.write_to_csv_counter == 20):
            self.write_to_csv_counter = 0
            # write to the csv file
            download_dir = "qLearning.csv" #where you want the file to be downloaded to 
            csv = open(download_dir, "w") #"w" indicates that you're writing strings to the file

            for i in range(4):
                csv.write('table' + str(i) + '\n')
                writer = csv.write('\n'.join([''.join(['{:4}'.format(state.display()) for state in row]) for row in self.tables[i]]))
                csv.write('\n')
            csv.close()

            round_count_file = "round_count.txt"
            txt = open(round_count_file, "w")
            txt.write(str(self.numberOfRounds))
            txt.close()
        # NOT for training purposes
        self.__reset()
        pass

    def __locate_row_number_of_street_in_table(self, street):
        if street == "preflop":
            return 0
        elif street == "flop":
            my_bet_at_start_of_flop = self.my_bet_at_start_of_street["flop"]
            return my_bet_at_start_of_flop / 10 / 2
        elif street == "turn":
            my_bet_at_start_of_flop = self.my_bet_at_start_of_street["flop"]
            row_number_at_flop = my_bet_at_start_of_flop / 10 / 2
            my_bet_at_start_of_turn = self.my_bet_at_start_of_street["turn"]
            return (row_number_at_flop * 6 + my_bet_at_start_of_turn / 10 + 2) / 2
        elif street == "river":
            my_bet_at_start_of_flop = self.my_bet_at_start_of_street["flop"]
            row_number_at_flop = my_bet_at_start_of_flop / 10 / 2
            my_bet_at_start_of_turn = self.my_bet_at_start_of_street["turn"]
            row_number_at_turn = (row_number_at_flop * 6 + my_bet_at_start_of_turn / 10 + 2) / 2
            my_bet_at_start_of_river = self.my_bet_at_start_of_street["river"]
            return (row_number_at_turn * 6 + my_bet_at_start_of_river / 10 + 2) / 2

    def __findTableType(self, street):
        winrate_at_street = self.winrate_for_each_street[street]

        if winrate_at_street <= agent.winrate_ceiling_for_table_0:
            return 0
        elif winrate_at_street <= agent.winrate_ceiling_for_table_1:
            return 1
        elif winrate_at_street <= agent.winrate_ceiling_for_table_2:
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
                action_index_list[agent.RAISE_INDEX] = i
            if i["action"] == "call":
                action_index_list[agent.CALL_INDEX] = i
            else:
                action_index_list[agent.FOLD_INDEX] = i

        return action_index_list

    def __get_raise_action(self, valid_actions):
        action_index_list = self.__get_ordered_action_list(valid_actions)
        action_info = action_index_list[agent.RAISE_INDEX]
        if action_info != -1:
            return action_info["action"]
        return None

    def __get_call_action(self, valid_actions):
        action_index_list = self.__get_ordered_action_list(valid_actions)
        action_info = action_index_list[agent.CALL_INDEX]
        if action_info != -1:
            return action_info["action"]
        return None

    def __get_fold_action(self, valid_actions):
        action_index_list = self.__get_ordered_action_list(valid_actions)
        action_info = action_index_list[agent.FOLD_INDEX]
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

    def __get_aim_of_max_payoff(self, list_of_aims_i_can_achieve_if_raise, list_of_aims_i_can_achieve_if_call):
        merged_aim_list = list_of_aims_i_can_achieve_if_raise + \
                          list(set(list_of_aims_i_can_achieve_if_call) - set(list_of_aims_i_can_achieve_if_raise))
        # in this version, we do not consider the probability of chaning to another type of agent in the next street
        table_to_look_at = self.__findTableType(self.at_street)

        my_row_number = self.__locate_row_number_of_street_in_table(self.at_street)
        aim_to_expected_payoff = {}
        for aim in merged_aim_list:
            if aim == 0:
                aim_to_expected_payoff[0] = -self.my_current_bet
            else:
                aim_game_state = self.tables[table_to_look_at][int(my_row_number)][int(aim/10)]
                aim_to_expected_payoff[aim] = aim_game_state.expectedPayoff

        max_payoff = max(aim_to_expected_payoff.values())
        aims_of_max_payoff = []
        for key, value in aim_to_expected_payoff.items():
            if value == max_payoff:
                aims_of_max_payoff.append(key)
        #return the one that is closest to achieve
        return min(aims_of_max_payoff), max_payoff

    def __get_an_random_aim(self, list_of_aims_i_can_achieve_if_raise, list_of_aims_i_can_achieve_if_call):
        merged_aim_list = list_of_aims_i_can_achieve_if_raise + \
                          list(set(list_of_aims_i_can_achieve_if_call) - set(list_of_aims_i_can_achieve_if_raise))
        r = random()
        l = len(merged_aim_list)
        aim_index = int(floor(r * l))
        if aim_index == l:
            aim_index -= 1
        return merged_aim_list[aim_index], 0

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
                if self.my_current_bet == self.sb_amount:
                    self.my_current_bet = self.sb_amount * 2 + raise_amount
                else:
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
    return agent()
