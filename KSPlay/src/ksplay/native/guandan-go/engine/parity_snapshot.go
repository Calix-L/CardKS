package engine

import "fmt"

type PlayerParitySnapshot struct {
	Rank       int      `json:"rank"`
	Victory    int      `json:"victory"`
	StuckTimes int      `json:"stuckTimes"`
	HeartsNum  int      `json:"heartsNum"`
	HandCards  []string `json:"handCards"`
}

type TableParitySnapshot struct {
	Rank             int                    `json:"rank"`
	RankBelongs      int                    `json:"rankBelongs"`
	BelongsTo        int                    `json:"belongsTo"`
	RankInc          int                    `json:"rankInc"`
	ShuffleTimes     int                    `json:"shuffleTimes"`
	Phase            string                 `json:"phase"`
	ActionFirst      bool                   `json:"actionFirst"`
	CurrentPos       int                    `json:"currentPos"`
	CurrentAction    *Move                  `json:"currentAction"`
	CurrentActionNil bool                   `json:"currentActionNil"`
	GreaterPos       int                    `json:"greaterPos"`
	GreaterAction    *Move                  `json:"greaterAction"`
	SettlementOrder  []int                  `json:"settlementOrder"`
	Players          []PlayerParitySnapshot `json:"players"`
}

func (t *Table) LoadParitySnapshot(s TableParitySnapshot) error {
	if len(s.Players) != 4 {
		return fmt.Errorf("snapshot needs 4 players, got %d", len(s.Players))
	}
	if len(t.players) != 4 {
		return fmt.Errorf("table needs 4 players, got %d", len(t.players))
	}
	if s.Rank < 2 || s.Rank >= len(cardRanks) {
		return fmt.Errorf("invalid rank index %d", s.Rank)
	}
	t.rank = s.Rank
	t.rankBelongs = s.RankBelongs
	t.belongsTo = s.BelongsTo
	t.rankInc = s.RankInc
	t.shuffleTimes = s.ShuffleTimes
	t.phase = s.Phase
	if t.phase == "" {
		t.phase = PhasePlay
	}
	t.actionFirst = s.ActionFirst
	t.state.CurrentPos = s.CurrentPos
	t.state.CurrentAction = Move{}
	if s.CurrentAction != nil {
		t.state.CurrentAction = *s.CurrentAction
	}
	t.state.CurrentNil = s.CurrentActionNil
	t.state.GreaterPos = s.GreaterPos
	t.state.GreaterAction = Move{}
	if s.GreaterAction != nil {
		t.state.GreaterAction = *s.GreaterAction
	}
	t.settlement.Clear()
	t.settlement.Order = append([]int(nil), s.SettlementOrder...)
	for i, ps := range s.Players {
		t.players[i].Rank = ps.Rank
		t.players[i].Victory = ps.Victory
		t.players[i].StuckTimes = ps.StuckTimes
		t.players[i].HeartsNum = ps.HeartsNum
		t.players[i].HandCards = ParseCards(ps.HandCards)
		t.players[i].PlayArea = nil
	}
	if s.CurrentPos >= 0 {
		if s.ActionFirst {
			t.firstAction(s.CurrentPos)
		} else {
			t.secondAction(s.CurrentPos)
		}
	}
	return nil
}

func (t *Table) ParitySummary() map[string]any {
	players := make([]map[string]any, len(t.players))
	for i, player := range t.players {
		players[i] = map[string]any{
			"rank":       player.Rank,
			"victory":    player.Victory,
			"stuckTimes": player.StuckTimes,
			"heartsNum":  player.HeartsNum,
			"handCards":  FormatCards(player.HandCards),
		}
	}
	results := append([]int(nil), t.results...)
	if results == nil {
		results = []int{}
	}
	return map[string]any{
		"rank":            t.rank,
		"rankLabel":       t.Rank(),
		"rankBelongs":     t.rankBelongs,
		"belongsTo":       t.belongsTo,
		"rankInc":         t.rankInc,
		"shuffleTimes":    t.shuffleTimes,
		"phase":           t.phase,
		"actionFirst":     t.actionFirst,
		"currentPos":      t.state.CurrentPos,
		"greaterPos":      t.state.GreaterPos,
		"settlementOrder": append([]int(nil), t.settlement.Order...),
		"results":         results,
		"players":         players,
	}
}

func (t *Table) RuntimeSummary() map[string]any {
	players := make([]map[string]any, len(t.players))
	for i, player := range t.players {
		players[i] = map[string]any{
			"pos":       player.Pos,
			"rank":      player.Rank,
			"handCount": len(player.HandCards),
		}
	}
	return map[string]any{
		"phase":       t.phase,
		"rank":        t.rank,
		"rankLabel":   t.Rank(),
		"currentPos":  t.state.CurrentPos,
		"players":     players,
		"results":     append([]int(nil), t.results...),
		"shuffleTime": t.shuffleTimes,
	}
}
