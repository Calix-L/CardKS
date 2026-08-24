'''
    File name: gin_rummy/round.py
    Author: William Hale
    Date created: 2/12/2020
'''
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .utils.move import GinRummyMove

from typing import List

from ksplay._vendor.rlcard.games.gin_rummy.dealer import GinRummyDealer

from .utils.action_event import DrawCardAction, PickUpDiscardAction, DeclareDeadHandAction
from .utils.action_event import DiscardAction, KnockAction, GinAction
from .utils.action_event import ScoreNorthPlayerAction, ScoreSouthPlayerAction

from .utils.move import DealHandMove
from .utils.move import DrawCardMove, PickupDiscardMove, DeclareDeadHandMove
from .utils.move import DiscardMove, KnockMove, GinMove
from .utils.move import ScoreNorthMove, ScoreSouthMove

from .utils.gin_rummy_error import GinRummyProgramError

from .player import GinRummyPlayer
from . import judge

from ksplay._vendor.rlcard.games.gin_rummy.utils import melding
from ksplay._vendor.rlcard.games.gin_rummy.utils import utils


def _get_cached_best_meld_cluster(player):
    """Return the public scorer's first best cluster via maintained caches."""
    hand = player.hand
    if player._hand_mask is None:
        best = melding.get_best_meld_clusters(hand=hand)
        cluster = [] if not best else best[0]
        return cluster, utils.get_deadwood_count(
            hand=hand, meld_cluster=cluster
        )

    # Match melding.get_meld_clusters exactly: suit-ordered runs first,
    # followed by set melds in its original lexicographic-rank order.
    melds = [
        frozenset(meld)
        for meld_group in player.meld_run_by_suit_id
        for meld in meld_group
    ]
    melds.extend(
        frozenset(meld)
        for meld in melding.get_all_set_melds(hand)
    )
    total_deadwood = sum(utils.get_deadwood_value(card) for card in hand)
    best_deadwood = total_deadwood
    best_indexes = ()
    meld_values = [
        sum(utils.get_deadwood_value(card) for card in meld)
        for meld in melds
    ]
    meld_count = len(melds)
    for i in range(meld_count):
        first = melds[i]
        deadwood = total_deadwood - meld_values[i]
        if deadwood < best_deadwood:
            best_deadwood = deadwood
            best_indexes = (i,)
        for j in range(i + 1, meld_count):
            second = melds[j]
            if not second.isdisjoint(first):
                continue
            deadwood = total_deadwood - meld_values[i] - meld_values[j]
            if deadwood < best_deadwood:
                best_deadwood = deadwood
                best_indexes = (i, j)
            for k in range(j + 1, meld_count):
                third = melds[k]
                if (
                    not third.isdisjoint(first)
                    or not third.isdisjoint(second)
                ):
                    continue
                deadwood = (
                    total_deadwood
                    - meld_values[i]
                    - meld_values[j]
                    - meld_values[k]
                )
                if deadwood < best_deadwood:
                    best_deadwood = deadwood
                    best_indexes = (i, j, k)
    cluster = [list(melds[index]) for index in best_indexes]
    return cluster, best_deadwood


class GinRummyRound:

    def __init__(self, dealer_id: int, np_random):
        ''' Initialize the round class

            The round class maintains the following instances:
                1) dealer: the dealer of the round; dealer has stock_pile and discard_pile
                2) players: the players in the round; each player has his own hand_pile
                3) current_player_id: the id of the current player who has the move
                4) is_over: true if the round is over
                5) going_out_action: knock or gin or None
                6) going_out_player_id: id of player who went out or None
                7) move_sheet: history of the moves of the player (including the deal_hand_move)

            The round class maintains a list of moves made by the players in self.move_sheet.
            move_sheet is similar to a chess score sheet.
            I didn't want to call it a score_sheet since it is not keeping score.
            I could have called move_sheet just moves, but that might conflict with the name moves used elsewhere.
            I settled on the longer name "move_sheet" to indicate that it is the official list of moves being made.

        Args:
            dealer_id: int
        '''
        self.np_random = np_random
        self.dealer_id = dealer_id
        self.dealer = GinRummyDealer(self.np_random)
        self.players = [GinRummyPlayer(player_id=0, np_random=self.np_random), GinRummyPlayer(player_id=1, np_random=self.np_random)]
        self.current_player_id = (dealer_id + 1) % 2
        self.is_over = False
        self.going_out_action = None  # going_out_action: int or None
        self.going_out_player_id = None  # going_out_player_id: int or None
        self.move_sheet = []  # type: List[GinRummyMove]
        player_dealing = GinRummyPlayer(player_id=dealer_id, np_random=self.np_random)
        shuffled_deck = self.dealer.shuffled_deck
        self.move_sheet.append(DealHandMove(player_dealing=player_dealing, shuffled_deck=shuffled_deck))

    def get_current_player(self) -> GinRummyPlayer or None:
        current_player_id = self.current_player_id
        return None if current_player_id is None else self.players[current_player_id]

    def draw_card(self, action: DrawCardAction, trusted=False):
        # when current_player takes DrawCardAction step, the move is recorded and executed
        # current_player keeps turn
        current_player = self.players[self.current_player_id]
        if not trusted and not len(current_player.hand) == 10:
            raise GinRummyProgramError("len(current_player.hand) is {}: should be 10.".format(len(current_player.hand)))
        card = self.dealer.stock_pile.pop()
        if trusted:
            move = DrawCardMove.__new__(DrawCardMove)
            move.player = current_player
            move.action = action
            move.card = card
        else:
            move = DrawCardMove(
                current_player, action=action, card=card
            )
        self.move_sheet.append(move)
        current_player.add_card_to_hand(card=card)

    def pick_up_discard(self, action: PickUpDiscardAction, trusted=False):
        # when current_player takes PickUpDiscardAction step, the move is recorded and executed
        # opponent knows that the card is in current_player hand
        # current_player keeps turn
        current_player = self.players[self.current_player_id]
        if not trusted and not len(current_player.hand) == 10:
            raise GinRummyProgramError("len(current_player.hand) is {}: should be 10.".format(len(current_player.hand)))
        card = self.dealer.discard_pile.pop()
        if trusted:
            move = PickupDiscardMove.__new__(PickupDiscardMove)
            move.player = current_player
            move.action = action
            move.card = card
        else:
            move = PickupDiscardMove(
                current_player, action, card=card
            )
        self.move_sheet.append(move)
        current_player.add_card_to_hand(card=card)
        current_player.known_cards.append(card)
        if current_player._known_mask is not None:
            try:
                current_player._known_mask |= card._gin_rummy_bit
            except AttributeError:
                current_player._known_mask = None

    def declare_dead_hand(self, action: DeclareDeadHandAction, trusted=False):
        # when current_player takes DeclareDeadHandAction step, the move is recorded and executed
        # north becomes current_player to score his hand
        current_player = self.players[self.current_player_id]
        if trusted:
            move = DeclareDeadHandMove.__new__(DeclareDeadHandMove)
            move.player = current_player
            move.action = action
        else:
            move = DeclareDeadHandMove(current_player, action)
        self.move_sheet.append(move)
        self.going_out_action = action
        self.going_out_player_id = self.current_player_id
        if not trusted and not len(current_player.hand) == 10:
            raise GinRummyProgramError("len(current_player.hand) is {}: should be 10.".format(len(current_player.hand)))
        self.current_player_id = 0

    def discard(self, action: DiscardAction, trusted=False):
        # when current_player takes DiscardAction step, the move is recorded and executed
        # opponent knows that the card is no longer in current_player hand
        # current_player loses his turn and the opponent becomes the current player
        current_player = self.players[self.current_player_id]
        if not trusted and not len(current_player.hand) == 11:
            raise GinRummyProgramError("len(current_player.hand) is {}: should be 11.".format(len(current_player.hand)))
        if trusted:
            move = DiscardMove.__new__(DiscardMove)
            move.player = current_player
            move.action = action
        else:
            move = DiscardMove(current_player, action)
        self.move_sheet.append(move)
        card = action.card
        current_player.remove_card_from_hand(card=card)
        if current_player.known_cards:
            current_player.remove_known_card(card, trusted)
        self.dealer.discard_pile.append(card)
        self.current_player_id = (self.current_player_id + 1) % 2

    def knock(self, action: KnockAction, trusted=False):
        # when current_player takes KnockAction step, the move is recorded and executed
        # opponent knows that the card is no longer in current_player hand
        # north becomes current_player to score his hand
        current_player = self.players[self.current_player_id]
        if trusted:
            move = KnockMove.__new__(KnockMove)
            move.player = current_player
            move.action = action
        else:
            move = KnockMove(current_player, action)
        self.move_sheet.append(move)
        self.going_out_action = action
        self.going_out_player_id = self.current_player_id
        if not trusted and not len(current_player.hand) == 11:
            raise GinRummyProgramError("len(current_player.hand) is {}: should be 11.".format(len(current_player.hand)))
        card = action.card
        current_player.remove_card_from_hand(card=card)
        if current_player.known_cards:
            current_player.remove_known_card(card, trusted)
        self.current_player_id = 0

    def gin(self, action: GinAction, going_out_deadwood_count: int,
            trusted=False):
        # when current_player takes GinAction step, the move is recorded and executed
        # opponent knows that the card is no longer in current_player hand
        # north becomes current_player to score his hand
        current_player = self.players[self.current_player_id]
        if trusted:
            move = GinMove.__new__(GinMove)
            move.player = current_player
            move.action = action
        else:
            move = GinMove(current_player, action)
        self.move_sheet.append(move)
        self.going_out_action = action
        self.going_out_player_id = self.current_player_id
        if not trusted and not len(current_player.hand) == 11:
            raise GinRummyProgramError("len(current_player.hand) is {}: should be 11.".format(len(current_player.hand)))
        _, gin_cards = judge.get_going_out_cards(current_player.hand, going_out_deadwood_count)
        card = gin_cards[0]
        current_player.remove_card_from_hand(card=card)
        if current_player.known_cards:
            current_player.remove_known_card(card, trusted)
        self.current_player_id = 0

    def score_player_0(self, action: ScoreNorthPlayerAction, trusted=False):
        # when current_player takes ScoreNorthPlayerAction step, the move is recorded and executed
        # south becomes current player
        if not trusted and not self.current_player_id == 0:
            raise GinRummyProgramError("current_player_id is {}: should be 0.".format(self.current_player_id))
        current_player = self.get_current_player()
        if trusted:
            best_meld_cluster, deadwood_count = (
                _get_cached_best_meld_cluster(current_player)
            )
        else:
            best_meld_clusters = melding.get_best_meld_clusters(hand=current_player.hand)
            best_meld_cluster = [] if not best_meld_clusters else best_meld_clusters[0]
            deadwood_count = utils.get_deadwood_count(hand=current_player.hand, meld_cluster=best_meld_cluster)
        if trusted:
            move = ScoreNorthMove.__new__(ScoreNorthMove)
            move.player = current_player
            move.action = action
            move.best_meld_cluster = best_meld_cluster
            move.deadwood_count = deadwood_count
        else:
            move = ScoreNorthMove(
                player=current_player,
                action=action,
                best_meld_cluster=best_meld_cluster,
                deadwood_count=deadwood_count,
            )
        self.move_sheet.append(move)
        self.current_player_id = 1

    def score_player_1(self, action: ScoreSouthPlayerAction, trusted=False):
        # when current_player takes ScoreSouthPlayerAction step, the move is recorded and executed
        # south remains current player
        # the round is over
        if not trusted and not self.current_player_id == 1:
            raise GinRummyProgramError("current_player_id is {}: should be 1.".format(self.current_player_id))
        current_player = self.get_current_player()
        if trusted:
            best_meld_cluster, deadwood_count = (
                _get_cached_best_meld_cluster(current_player)
            )
        else:
            best_meld_clusters = melding.get_best_meld_clusters(hand=current_player.hand)
            best_meld_cluster = [] if not best_meld_clusters else best_meld_clusters[0]
            deadwood_count = utils.get_deadwood_count(hand=current_player.hand, meld_cluster=best_meld_cluster)
        if trusted:
            move = ScoreSouthMove.__new__(ScoreSouthMove)
            move.player = current_player
            move.action = action
            move.best_meld_cluster = best_meld_cluster
            move.deadwood_count = deadwood_count
        else:
            move = ScoreSouthMove(
                player=current_player,
                action=action,
                best_meld_cluster=best_meld_cluster,
                deadwood_count=deadwood_count,
            )
        self.move_sheet.append(move)
        self.is_over = True
