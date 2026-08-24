package engine

import (
	"fmt"
	"math/rand"
	"time"
)

type Table struct {
	rank         int
	deck         []Card
	cardPool     []Card
	players      []Player
	rankBelongs  int
	state        Trick
	settlement   Finish
	results      []int
	deckData     []string
	fixedDeck    bool
	firstPlayer  *int
	actionFirst  bool
	legalActions []Action
	belongsTo    int
	rankInc      int
	phase        string
	shuffleTimes int
	rng          *rand.Rand
}

func NewTable(deckData []string, firstPlayer *int) (*Table, error) {
	if deckData != nil && len(deckData) != 108 {
		return nil, fmt.Errorf("deckData length must be 108, got %d", len(deckData))
	}
	t := &Table{
		rank:        2,
		rankBelongs: -1,
		state:       NewTrick(),
		cardPool:    newCardPool(),
		deckData:    append([]string(nil), deckData...),
		fixedDeck:   deckData != nil,
		firstPlayer: firstPlayer,
		belongsTo:   -1,
		phase:       PhasePlay,
		rng:         rand.New(rand.NewSource(time.Now().UnixNano())),
	}
	if deckData != nil {
		t.deck = ParseCards(deckData)
	}
	return t, nil
}

func newCardPool() []Card {
	labels := make([]string, 0, 108)
	for i := 0; i < 2; i++ {
		for _, suit := range []byte{'S', 'H', 'C', 'D'} {
			for rank := 2; rank < len(cardRanks); rank++ {
				labels = append(labels, string([]byte{suit, cardRanks[rank][0]}))
			}
		}
		labels = append(labels, "SB", "HR")
	}
	return ParseCards(labels)
}

func (t *Table) Reshuffle() {
	t.deck = append([]Card(nil), t.cardPool...)
	t.rng.Shuffle(len(t.deck), func(i, j int) {
		t.deck[i], t.deck[j] = t.deck[j], t.deck[i]
	})
	t.deckData = FormatCards(t.deck)
}

func (t *Table) AddPlayer(name string, index int) {
	t.players = append(t.players, NewPlayer(name, index))
}

func (t *Table) Rank() string {
	return cardRanks[t.rank]
}

func (t *Table) Deal() error {
	if len(t.players) != 4 {
		return fmt.Errorf("need 4 players, got %d", len(t.players))
	}
	if len(t.deck) != 108 {
		return fmt.Errorf("deck length must be 108 before deal, got %d", len(t.deck))
	}
	count := 107
	for i := 0; i < 4; i++ {
		t.players[i].HandCards = nil
		t.players[i].HeartsNum = 0
		for j := 0; j < 27; j++ {
			card := t.deck[count]
			if string(card.Rank) == t.Rank() && card.Suit == 'H' {
				t.players[i].HeartsNum++
			}
			inserted := false
			for idx := 0; idx < len(t.players[i].HandCards); idx++ {
				if cmpHand(card, t.players[i].HandCards[idx], t.Rank(), false) {
					t.players[i].HandCards = append(t.players[i].HandCards, Card{})
					copy(t.players[i].HandCards[idx+1:], t.players[i].HandCards[idx:])
					t.players[i].HandCards[idx] = card
					inserted = true
					break
				}
			}
			if !inserted {
				t.players[i].HandCards = append(t.players[i].HandCards, card)
			}
			count--
			t.deck = t.deck[:len(t.deck)-1]
		}
	}
	return nil
}

func (t *Table) Start() ([]Msg, error) {
	for i := range t.players {
		t.players[i].ResetForStart()
	}
	if !t.fixedDeck {
		t.Reshuffle()
	} else {
		t.deck = ParseCards(t.deckData)
	}
	if err := t.Deal(); err != nil {
		return nil, err
	}

	pending := []Msg{}
	t.settlement.Clear()
	t.state.Reset()
	curPos := 0
	if t.firstPlayer != nil {
		curPos = *t.firstPlayer
	}
	t.legalActions = FirstActions(FormatCards(t.players[curPos].HandCards), t.Rank())
	t.actionFirst = true
	t.notifyBeginning(&pending)
	t.act(&pending, curPos, PhasePlay)
	t.state.CurrentPos = curPos
	return pending, nil
}

func (t *Table) Play(actIndex int) ([]Msg, error) {
	if actIndex < 0 || actIndex >= len(t.legalActions) {
		return nil, fmt.Errorf("actIndex out of range: %d", actIndex)
	}
	action := actionToMove(t.legalActions[actIndex])
	t.state.CurrentAction = action
	t.state.CurrentNil = false
	t.players[t.state.CurrentPos].PlayArea = &action
	pending := []Msg{}
	if action.Type == PassType {
		t.notifyPlay(&pending)
		var currentPos int
		if t.leadPassesAfterPassChain() {
			currentPos = (t.state.GreaterPos + 2) % 4
			t.clearActionWithPlayerAliases()
			t.firstAction(currentPos)
			t.actionFirst = true
		} else {
			currentPos = t.nextSeatWithCards()
			if currentPos == t.state.GreaterPos {
				t.clearActionWithPlayerAliases()
				t.firstAction(currentPos)
				t.actionFirst = true
			} else {
				t.secondAction(currentPos)
				t.actionFirst = false
			}
		}
		t.act(&pending, currentPos, PhasePlay)
		t.state.CurrentPos = currentPos
		return pending, nil
	}

	player := &t.players[t.state.CurrentPos]
	player.PlayCard(action.Cards, "H"+t.Rank())
	player.PlayArea = &action
	t.state.UpdateGreaterAction(action)
	t.notifyPlay(&pending)
	if len(player.HandCards) == 0 {
		t.settlement.Add(t.state.CurrentPos)
		if t.settlement.EpisodeOver() {
			for i := 0; i < 4; i++ {
				if len(t.players[i].HandCards) > 0 {
					t.settlement.Add(i)
				}
			}
			firstPos, _, inc := t.settlement.Settlement()
			t.notifyEpisodeOver(&pending)
			if t.rank == 14 {
				if (t.rankBelongs+2)%4 == firstPos || t.rankBelongs == firstPos {
					if (firstPos+2)%4 == t.settlement.Fourth() {
						t.stuckAtAce(firstPos, (firstPos+2)%4, inc, &pending)
					} else {
						t.oneTimesOver(firstPos, &pending)
					}
				} else {
					t.belongsTo = firstPos
					t.rankInc = inc
					t.phase = "enter_tribute"
				}
			} else {
				t.belongsTo = firstPos
				t.rankInc = inc
				t.phase = "enter_tribute"
			}
			return pending, nil
		}
		t.nextPlayerSecondAction(&pending)
		return pending, nil
	}
	t.nextPlayerSecondAction(&pending)
	return pending, nil
}

func (t *Table) StartNewEpisodeBack2(nextDeck []string) ([]Msg, error) {
	if t.belongsTo < 0 {
		return nil, fmt.Errorf("belongsTo is not set")
	}
	t.players[t.belongsTo].Rank = 2
	t.players[(t.belongsTo+2)%4].Rank = 2
	t.players[t.belongsTo].StuckTimes = 0
	t.players[(t.belongsTo+2)%4].StuckTimes = 0
	for i := range t.players {
		t.players[i].PlayArea = nil
	}
	t.rank = 2
	t.rankBelongs = t.belongsTo
	if nextDeck == nil {
		t.Reshuffle()
	} else if len(nextDeck) != 108 {
		return nil, fmt.Errorf("nextDeck length must be 108, got %d", len(nextDeck))
	} else {
		t.deckData = append([]string(nil), nextDeck...)
		t.deck = ParseCards(nextDeck)
	}
	if err := t.Deal(); err != nil {
		return nil, err
	}
	pending := []Msg{}
	t.actTribute(&pending)
	return pending, nil
}

func (t *Table) EnterTributeStage(nextDeck []string) ([]Msg, error) {
	if t.belongsTo < 0 {
		return nil, fmt.Errorf("belongsTo is not set")
	}
	t.players[t.belongsTo].UpdateRank(t.rankInc)
	teammate := (t.belongsTo + 2) % 4
	t.players[teammate].UpdateRank(t.rankInc)
	t.rank = t.players[t.belongsTo].Rank
	t.rankBelongs = t.belongsTo
	for i := range t.players {
		t.players[i].PlayArea = nil
		t.players[i].HeartsNum = 0
	}
	if nextDeck == nil {
		t.Reshuffle()
	} else if len(nextDeck) != 108 {
		return nil, fmt.Errorf("nextDeck length must be 108, got %d", len(nextDeck))
	} else {
		t.deckData = append([]string(nil), nextDeck...)
		t.deck = ParseCards(nextDeck)
	}
	if err := t.Deal(); err != nil {
		return nil, err
	}
	pending := []Msg{}
	t.actTribute(&pending)
	return pending, nil
}

func (t *Table) Tribute(actIndex int) ([]Msg, error) {
	if actIndex < 0 || actIndex >= len(t.legalActions) {
		return nil, fmt.Errorf("actIndex out of range: %d", actIndex)
	}
	pending := []Msg{}
	tributePos, to := t.settlement.FindShip(t.state.CurrentPos, "tri")
	action := actionToMove(t.legalActions[actIndex])
	t.settlement.TriCards = append(t.settlement.TriCards, [3]any{tributePos, to, action.Cards[0]})
	t.players[tributePos].PlayCard(action.Cards, "H"+t.Rank())
	if t.settlement.Index == 0 && len(t.settlement.TriShip) == 2 {
		t.settlement.Index++
		nextTributePos := t.settlement.TriShip[len(t.settlement.TriShip)-1][0]
		t.state.ClearAction()
		t.legalActions = t.players[nextTributePos].MaxCards(t.Rank(), "H"+t.Rank())
		t.act(&pending, nextTributePos, PhaseTribute)
		t.state.CurrentPos = nextTributePos
		return pending, nil
	}
	for _, item := range t.settlement.TriCards {
		toPos := item[1].(int)
		card := item[2].(string)
		t.players[toPos].AddCard(card, t.Rank())
	}
	if len(t.settlement.TriCards) == 2 {
		a := t.settlement.TriCards[0]
		b := t.settlement.TriCards[1]
		triPosA := a[0].(int)
		triPosB := b[0].(int)
		cardA := a[2].(string)
		cardB := b[2].(string)
		cmp := t.cmpRank(cardA[1], cardB[1])
		if cmp == 1 {
			t.settlement.FirstPlay = triPosB
		} else if cmp == -1 {
			t.settlement.FirstPlay = triPosA
		} else {
			t.settlement.FirstPlay = t.settlement.Fourth()
		}
	} else {
		t.settlement.FirstPlay = t.settlement.Fourth()
	}
	t.notifyTribute(&pending)
	t.settlement.Index = 0
	back := t.settlement.BckShip[0][0]
	t.state.CurrentPos = -1
	t.state.CurrentAction = Move{}
	t.state.CurrentNil = true
	t.legalActions = t.players[back].LessThanTen(t.Rank())
	t.act(&pending, back, PhaseBack)
	t.state.CurrentPos = back
	t.phase = PhaseBack
	return pending, nil
}

func (t *Table) Back(actIndex int) ([]Msg, error) {
	if actIndex < 0 || actIndex >= len(t.legalActions) {
		return nil, fmt.Errorf("actIndex out of range: %d", actIndex)
	}
	backPos, to := t.settlement.FindShip(t.state.CurrentPos, "bck")
	action := actionToMove(t.legalActions[actIndex])
	t.settlement.BckCards = append(t.settlement.BckCards, [3]any{backPos, to, action.Cards[0]})
	t.players[backPos].PlayCard(action.Cards, "H"+t.Rank())
	pending := []Msg{}
	if t.settlement.Index == 0 && len(t.settlement.BckShip) == 2 {
		t.settlement.Index++
		nextBackPos := t.settlement.BckShip[len(t.settlement.BckShip)-1][0]
		t.legalActions = t.players[nextBackPos].LessThanTen(t.Rank())
		t.act(&pending, nextBackPos, PhaseBack)
		t.state.CurrentPos = nextBackPos
		return pending, nil
	}
	for _, item := range t.settlement.BckCards {
		toPos := item[1].(int)
		card := item[2].(string)
		t.players[toPos].AddCard(card, t.Rank())
	}
	t.notifyBack(&pending)
	t.settlement.Index = 0
	t.state.CurrentPos = -1
	t.firstAction(t.settlement.FirstPlay)
	t.actionFirst = true
	t.act(&pending, t.settlement.FirstPlay, PhasePlay)
	t.state.CurrentPos = t.settlement.FirstPlay
	t.phase = PhasePlay
	t.settlement.Clear()
	return pending, nil
}

func (t *Table) nextPlayerSecondAction(pending *[]Msg) {
	currentPos := t.nextSeatWithCards()
	t.secondAction(currentPos)
	t.actionFirst = false
	t.act(pending, currentPos, PhasePlay)
	t.state.CurrentPos = currentPos
}

func (t *Table) CurrentActionList() []any {
	return ActionsAsTuples(t.legalActions)
}

func (t *Table) Phase() string {
	return t.phase
}

func (t *Table) notifyBeginning(msgs *[]Msg) {
	for i := range t.players {
		player := t.players[i]
		opponent := t.players[(i+1)%4]
		*msgs = append(*msgs, Msg{
			Seat: player.Pos,
			Body: notifyBeginning(player.HandCards, player.Pos, t.rank, player.Rank, opponent.Rank),
		})
	}
}

func (t *Table) notifyPlay(msgs *[]Msg) {
	curPos, curAction, greaterPos, greaterAction := t.state.ActionInfo()
	for i := range t.players {
		*msgs = append(*msgs, Msg{
			Seat: t.players[i].Pos,
			Body: notifyPlay(curPos, curAction, greaterPos, greaterAction),
		})
	}
}

func (t *Table) notifyEpisodeOver(msgs *[]Msg) {
	restCards := []any{}
	for i := range t.players {
		if len(t.players[i].HandCards) > 0 {
			restCards = append(restCards, []any{t.players[i].Pos, FormatCards(t.players[i].HandCards)})
		}
	}
	body := notifyEpisodeOver(t.Rank(), t.settlement.Order, restCards)
	for i := range t.players {
		*msgs = append(*msgs, Msg{Seat: t.players[i].Pos, Body: body})
	}
}

func (t *Table) notifyGameOver(msgs *[]Msg) {
	body := notifyGameOver(1, 1)
	for i := range t.players {
		*msgs = append(*msgs, Msg{Seat: t.players[i].Pos, Body: body})
	}
}

func (t *Table) notifyGameResult(msgs *[]Msg) {
	wins := make([]int, len(t.players))
	for i := range t.players {
		wins[i] = t.players[i].Victory
	}
	t.results = append([]int(nil), wins...)
	body := notifyGameResult(wins, []int{0, 0, 0, 0})
	for i := range t.players {
		*msgs = append(*msgs, Msg{Seat: t.players[i].Pos, Body: body})
	}
}

func (t *Table) notifyTribute(msgs *[]Msg) {
	body := notifyTribute(t.settlement.TriCards)
	for i := range t.players {
		*msgs = append(*msgs, Msg{Seat: t.players[i].Pos, Body: body})
	}
}

func (t *Table) notifyBack(msgs *[]Msg) {
	body := notifyBack(t.settlement.BckCards)
	for i := range t.players {
		*msgs = append(*msgs, Msg{Seat: t.players[i].Pos, Body: body})
	}
}

func (t *Table) notifyAntiTribute(msgs *[]Msg, antiNum int, antiPos []int) {
	body := notifyAntiTribute(antiNum, antiPos)
	for i := range t.players {
		*msgs = append(*msgs, Msg{Seat: t.players[i].Pos, Body: body})
	}
}

func (t *Table) act(msgs *[]Msg, curPos int, stage string) {
	player := t.players[curPos]
	opponent := t.players[(curPos+1)%4]
	curPosInfo, curAction, greaterPos, greaterAction := t.state.ActionInfo()
	publicInfo := make([]map[string]any, len(t.players))
	for i := range t.players {
		publicInfo[i] = t.players[i].PublicInfo()
	}
	body := actBody(
		stage,
		FormatCards(player.HandCards),
		publicInfo,
		cardRanks[player.Rank],
		cardRanks[opponent.Rank],
		t.Rank(),
		curPosInfo,
		curAction,
		greaterPos,
		greaterAction,
		ActionsAsTuples(t.legalActions),
	)
	*msgs = append(*msgs, Msg{Seat: curPos, Body: body})
}

func (t *Table) secondAction(curPos int) {
	t.legalActions = SecondActions(FormatCards(t.players[curPos].HandCards), t.Rank(), moveToAction(t.state.GreaterAction))
}

func (t *Table) firstAction(curPos int) {
	t.legalActions = FirstActions(FormatCards(t.players[curPos].HandCards), t.Rank())
}

func (t *Table) nextSeatWithCards() int {
	for i := 1; i < 4; i++ {
		pos := (t.state.CurrentPos + i) % 4
		if len(t.players[pos].HandCards) > 0 {
			return pos
		}
	}
	return t.state.CurrentPos
}

func (t *Table) leadPassesAfterPassChain() bool {
	cPos, gPos := t.state.CurrentPos, t.state.GreaterPos
	prerequisiteA := (cPos+1)%4 == gPos
	prerequisiteB := gPos >= 0 && len(t.players[gPos].HandCards) == 0

	prerequisiteBigA := (cPos+2)%4 == gPos
	prerequisiteBigB := gPos >= 0 && len(t.players[gPos].HandCards) == 0 && len(t.players[(cPos+1)%4].HandCards) == 0

	return (prerequisiteA && prerequisiteB) || (prerequisiteBigA && prerequisiteBigB)
}

func (t *Table) clearActionWithPlayerAliases() {
	emptyCurrent := Move{}
	emptyGreater := Move{}
	if t.state.CurrentPos >= 0 {
		t.players[t.state.CurrentPos].PlayArea = &emptyCurrent
	}
	if t.state.GreaterPos >= 0 {
		t.players[t.state.GreaterPos].PlayArea = &emptyGreater
	}
	t.state.ClearAction()
}

func (t *Table) actTribute(pending *[]Msg) {
	t.phase = PhaseTribute
	t.notifyBeginning(pending)
	fourthAnti := t.players[t.settlement.Fourth()].RedJokerNum() == 2
	if len(t.settlement.TriShip) == 2 {
		thirdAnti := false
		if t.players[t.settlement.Third()].RedJokerNum() == 2 {
			thirdAnti = true
		} else if !fourthAnti && t.players[t.settlement.Fourth()].RedJokerNum() == 1 && t.players[t.settlement.Third()].RedJokerNum() == 1 {
			fourthAnti, thirdAnti = true, true
		}
		if fourthAnti || thirdAnti {
			t.notifyAntiTribute(pending, 2, []int{t.settlement.Third(), t.settlement.Fourth()})
			t.firstAction(t.settlement.First())
			t.actionFirst = true
			t.act(pending, t.settlement.First(), PhasePlay)
			t.state.CurrentPos = t.settlement.First()
			t.phase = PhasePlay
			t.settlement.Clear()
			return
		}
		tributePos := t.settlement.Fourth()
		t.legalActions = t.players[tributePos].MaxCards(t.Rank(), "H"+t.Rank())
		t.act(pending, tributePos, PhaseTribute)
		t.state.CurrentPos = tributePos
		return
	}
	if fourthAnti {
		t.settlement.TriShip = nil
		t.settlement.BckShip = nil
		t.notifyAntiTribute(pending, 1, []int{t.settlement.Fourth()})
		t.firstAction(t.settlement.First())
		t.actionFirst = true
		t.act(pending, t.settlement.First(), PhasePlay)
		t.state.CurrentPos = t.settlement.First()
		t.phase = PhasePlay
		t.settlement.Clear()
		return
	}
	tributePos := t.settlement.Fourth()
	t.legalActions = t.players[tributePos].MaxCards(t.Rank(), "H"+t.Rank())
	t.act(pending, tributePos, PhaseTribute)
	t.state.CurrentPos = tributePos
}

func (t *Table) addVictoryNum(pos int, teammatePos int) {
	t.players[pos].Victory++
	t.players[teammatePos].Victory++
}

func (t *Table) stuckAtAce(firstPos int, teammatePos int, rankInc int, pending *[]Msg) {
	t.players[firstPos].StuckTimes++
	t.players[teammatePos].StuckTimes++
	if t.players[firstPos].StuckTimes > 3 {
		t.shuffleTimes++
		if t.shuffleTimes >= 50 {
			t.notifyGameOver(pending)
			winner, teammate := t.shuffleTimesExceedsThreshold()
			t.addVictoryNum(winner, teammate)
			t.notifyGameResult(pending)
			return
		}
		t.belongsTo = firstPos
		t.phase = "start_new_episode_back_2"
		return
	}
	t.belongsTo = firstPos
	t.rankInc = rankInc
	t.phase = "enter_tribute"
}

func (t *Table) oneTimesOver(firstPos int, pending *[]Msg) {
	t.addVictoryNum(firstPos, (firstPos+2)%4)
	t.notifyGameOver(pending)
	t.notifyGameResult(pending)
}

func (t *Table) shuffleTimesExceedsThreshold() (int, int) {
	if t.players[0].Rank > t.players[1].Rank {
		return 0, 2
	}
	if t.players[0].Rank < t.players[1].Rank {
		return 1, 3
	}
	if t.rankBelongs == 0 || t.rankBelongs == 2 {
		return 0, 2
	}
	return 1, 3
}

func (t *Table) cmpRank(a byte, b byte) int {
	av, bv := t.rankOrderValue(a), t.rankOrderValue(b)
	if av > bv {
		return -1
	}
	if av < bv {
		return 1
	}
	return 0
}

func (t *Table) rankOrderValue(rank byte) int {
	if string(rank) == t.Rank() {
		return 15
	}
	switch rank {
	case '2':
		return 2
	case '3':
		return 3
	case '4':
		return 4
	case '5':
		return 5
	case '6':
		return 6
	case '7':
		return 7
	case '8':
		return 8
	case '9':
		return 9
	case 'T':
		return 10
	case 'J':
		return 11
	case 'Q':
		return 12
	case 'K':
		return 13
	case 'A':
		return 14
	case 'B':
		return 16
	case 'R':
		return 17
	}
	return 0
}

func actionToMove(action Action) Move {
	return Move{Type: action.Type, Rank: action.Rank, Cards: append([]string(nil), action.Cards...)}
}

func moveToAction(move Move) Action {
	return Action{Type: move.Type, Rank: move.Rank, Cards: append([]string(nil), move.Cards...)}
}
