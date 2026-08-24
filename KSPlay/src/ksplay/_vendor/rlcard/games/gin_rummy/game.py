'''
    File name: gin_rummy/game.py
    Author: William Hale
    Date created: 2/12/2020
'''

import numpy as np

from .player import GinRummyPlayer
from .round import GinRummyRound
from .judge import GinRummyJudge
from .utils.settings import Settings, DealerForRound

from .utils.action_event import *
from .utils.move import (
    DeclareDeadHandMove,
    DiscardMove,
    DrawCardMove,
    KnockMove,
    PickupDiscardMove,
)


class GinRummyGame:
    ''' Game class. This class will interact with outer environment.
    '''

    def __init__(self, allow_step_back=False):
        '''Initialize the class GinRummyGame
        '''
        self.allow_step_back = allow_step_back
        self.np_random = np.random.RandomState()
        self.judge = GinRummyJudge(game=self)
        self.settings = Settings()
        self.actions = None  # type: List[ActionEvent] or None # must reset in init_game
        self.round = None  # round: GinRummyRound or None, must reset in init_game
        self.num_players = 2

    def init_game(self, return_state=True):
        ''' Initialize all characters in the game and start round 1
        '''
        dealer_id = self.np_random.choice([0, 1])
        if self.settings.dealer_for_round == DealerForRound.North:
            dealer_id = 0
        elif self.settings.dealer_for_round == DealerForRound.South:
            dealer_id = 1
        self.actions = []
        self.round = GinRummyRound(dealer_id=dealer_id, np_random=self.np_random)
        for i in range(2):
            num = 11 if i == 0 else 10
            player = self.round.players[(dealer_id + 1 + i) % 2]
            self.round.dealer.deal_cards(player=player, num=num)
        current_player_id = self.round.current_player_id
        state = self.get_state(player_id=current_player_id) if return_state else {}
        return state, current_player_id

    def step(self, action: ActionEvent, return_state=True):
        ''' Perform game action and return next player number, and the state for next player
        '''
        if isinstance(action, ScoreNorthPlayerAction):
            self.round.score_player_0(action)
        elif isinstance(action, ScoreSouthPlayerAction):
            self.round.score_player_1(action)
        elif isinstance(action, DrawCardAction):
            self.round.draw_card(action)
        elif isinstance(action, PickUpDiscardAction):
            self.round.pick_up_discard(action)
        elif isinstance(action, DeclareDeadHandAction):
            self.round.declare_dead_hand(action)
        elif isinstance(action, GinAction):
            self.round.gin(action, going_out_deadwood_count=self.settings.going_out_deadwood_count)
        elif isinstance(action, DiscardAction):
            self.round.discard(action)
        elif isinstance(action, KnockAction):
            self.round.knock(action)
        else:
            raise Exception('Unknown step action={}'.format(action))
        self.actions.append(action)
        next_player_id = self.round.current_player_id
        next_state = self.get_state(player_id=next_player_id) if return_state else {}
        return next_state, next_player_id

    def _step_action_id(self, action_id: int, action: ActionEvent):
        """Step a decoded, validated action without repeating type dispatch."""
        round_ = self.round
        if discard_action_id <= action_id < knock_action_id:
            current_player = round_.players[round_.current_player_id]
            move = DiscardMove.__new__(DiscardMove)
            move.player = current_player
            move.action = action
            round_.move_sheet.append(move)
            card = action.card
            current_player.remove_card_from_hand(card)
            if current_player.known_cards:
                current_player.remove_known_card(card, True)
            round_.dealer.discard_pile.append(card)
            round_.current_player_id = 1 - round_.current_player_id
        elif action_id == pick_up_discard_action_id:
            current_player = round_.players[round_.current_player_id]
            card = round_.dealer.discard_pile.pop()
            move = PickupDiscardMove.__new__(PickupDiscardMove)
            move.player = current_player
            move.action = action
            move.card = card
            round_.move_sheet.append(move)
            current_player.add_card_to_hand(card)
            current_player.known_cards.append(card)
            current_player._known_mask |= card._gin_rummy_bit
        elif action_id == draw_card_action_id:
            current_player = round_.players[round_.current_player_id]
            card = round_.dealer.stock_pile.pop()
            move = DrawCardMove.__new__(DrawCardMove)
            move.player = current_player
            move.action = action
            move.card = card
            round_.move_sheet.append(move)
            current_player.add_card_to_hand(card)
        elif action_id == score_player_0_action_id:
            round_.score_player_0(action, True)
        elif action_id == score_player_1_action_id:
            round_.score_player_1(action, True)
        elif action_id == declare_dead_hand_action_id:
            current_player = round_.players[round_.current_player_id]
            move = DeclareDeadHandMove.__new__(DeclareDeadHandMove)
            move.player = current_player
            move.action = action
            round_.move_sheet.append(move)
            round_.going_out_action = action
            round_.going_out_player_id = round_.current_player_id
            round_.current_player_id = 0
        elif action_id == gin_action_id:
            round_.gin(
                action,
                going_out_deadwood_count=(
                    self.settings.going_out_deadwood_count
                ),
                trusted=True,
            )
        else:
            current_player = round_.players[round_.current_player_id]
            move = KnockMove.__new__(KnockMove)
            move.player = current_player
            move.action = action
            round_.move_sheet.append(move)
            round_.going_out_action = action
            round_.going_out_player_id = round_.current_player_id
            card = action.card
            current_player.remove_card_from_hand(card)
            if current_player.known_cards:
                current_player.remove_known_card(card, True)
            round_.current_player_id = 0
        self.actions.append(action)
        return {}, round_.current_player_id

    def step_back(self):
        ''' Takes one step backward and restore to the last state
        '''
        raise NotImplementedError

    def get_num_players(self):
        ''' Return the number of players in the game
        '''
        return 2

    def get_num_actions(self):
        ''' Return the number of possible actions in the game
        '''
        return ActionEvent.get_num_actions()

    def get_player_id(self):
        ''' Return the current player that will take actions soon
        '''
        return self.round.current_player_id

    def is_over(self):
        ''' Return whether the current game is over
        '''
        return self.round.is_over

    def get_current_player(self) -> GinRummyPlayer or None:
        return self.round.get_current_player()

    def get_last_action(self) -> ActionEvent or None:
        return self.actions[-1] if self.actions and len(self.actions) > 0 else None

    def get_state(self, player_id: int):
        ''' Get player's state

        Return:
            state (dict): The information of the state
        '''
        state = {}
        if not self.is_over():
            discard_pile = self.round.dealer.discard_pile
            top_discard = [] if not discard_pile else [discard_pile[-1]]
            dead_cards = discard_pile[:-1]
            last_action = self.get_last_action()
            opponent_id = (player_id + 1) % 2
            opponent = self.round.players[opponent_id]
            known_cards = opponent.known_cards
            if isinstance(last_action, ScoreNorthPlayerAction) or isinstance(last_action, ScoreSouthPlayerAction):
                known_cards = opponent.hand
            unknown_cards = self.round.dealer.stock_pile + [card for card in opponent.hand if card not in known_cards]
            state['player_id'] = self.round.current_player_id
            state['hand'] = [x.get_index() for x in self.round.players[self.round.current_player_id].hand]
            state['top_discard'] = [x.get_index() for x in top_discard]
            state['dead_cards'] = [x.get_index() for x in dead_cards]
            state['opponent_known_cards'] = [x.get_index() for x in known_cards]
            state['unknown_cards'] = [x.get_index() for x in unknown_cards]
        return state

    @staticmethod
    def decode_action(action_id) -> ActionEvent:  # FIXME 200213 should return str
        ''' Action id -> the action_event in the game.

        Args:
            action_id (int): the id of the action

        Returns:
            action (ActionEvent): the action that will be passed to the game engine.
        '''
        return ActionEvent.decode_action(action_id=action_id)
