package engine

const (
	PhasePlay    = "play"
	PhaseTribute = "tribute"
	PhaseBack    = "back"
)

var cardRanks = []string{"", "", "2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"}

var digital = map[string]int{
	"SA": 0x010e, "S2": 0x0102, "S3": 0x0103, "S4": 0x0104, "S5": 0x0105, "S6": 0x0106,
	"S7": 0x0107, "S8": 0x0108, "S9": 0x0109, "ST": 0x010a, "SJ": 0x010b, "SQ": 0x010c, "SK": 0x010d,
	"HA": 0x020e, "H2": 0x0202, "H3": 0x0203, "H4": 0x0204, "H5": 0x0205, "H6": 0x0206,
	"H7": 0x0207, "H8": 0x0208, "H9": 0x0209, "HT": 0x020a, "HJ": 0x020b, "HQ": 0x020c, "HK": 0x020d,
	"CA": 0x030e, "C2": 0x0302, "C3": 0x0303, "C4": 0x0304, "C5": 0x0305, "C6": 0x0306,
	"C7": 0x0307, "C8": 0x0308, "C9": 0x0309, "CT": 0x030a, "CJ": 0x030b, "CQ": 0x030c, "CK": 0x030d,
	"DA": 0x040e, "D2": 0x0402, "D3": 0x0403, "D4": 0x0404, "D5": 0x0405, "D6": 0x0406,
	"D7": 0x0407, "D8": 0x0408, "D9": 0x0409, "DT": 0x040a, "DJ": 0x040b, "DQ": 0x040c, "DK": 0x040d,
	"SB": 0x0110, "HR": 0x0211,
}

type Card struct {
	Suit    byte
	Rank    byte
	Digital int
	Label   string
}

func NewCard(label string) Card {
	return Card{Suit: label[0], Rank: label[1], Digital: digital[label], Label: label}
}

func ParseCards(labels []string) []Card {
	out := make([]Card, len(labels))
	for i, label := range labels {
		out[i] = NewCard(label)
	}
	return out
}

func FormatCards(cards []Card) []string {
	out := make([]string, len(cards))
	for i, card := range cards {
		out[i] = card.Label
	}
	return out
}

func cmpHand(a Card, b Card, trump string, suitBreak bool) bool {
	x := a.Digital & 0x00ff
	y := b.Digital & 0x00ff
	if string(a.Rank) == trump {
		x = 15
	}
	if string(b.Rank) == trump {
		y = 15
	}
	if x < y {
		return true
	}
	if x > y {
		return false
	}
	if suitBreak {
		return false
	}
	return (a.Digital & 0xff00) < (b.Digital & 0xff00)
}

type Move struct {
	Type  string
	Rank  string
	Cards []string
}

func (m Move) ToJSON() []any {
	if m.Type == "" && m.Rank == "" && m.Cards == nil {
		return []any{nil, nil, nil}
	}
	if m.Type == PassType {
		return []any{PassType, PassType, PassType}
	}
	return []any{m.Type, m.Rank, m.Cards}
}

type Msg struct {
	Seat int            `json:"seat"`
	Body map[string]any `json:"body"`
}

type Trick struct {
	CurrentPos    int
	CurrentAction Move
	CurrentNil    bool
	GreaterPos    int
	GreaterAction Move
}

func NewTrick() Trick {
	return Trick{CurrentPos: -1, GreaterPos: -1}
}

func (t *Trick) Reset() {
	t.CurrentPos = -1
	t.CurrentAction = Move{}
	t.CurrentNil = false
	t.GreaterPos = -1
	t.GreaterAction = Move{}
}

func (t *Trick) ClearAction() {
	t.CurrentPos = -1
	t.CurrentAction = Move{}
	t.CurrentNil = false
	t.GreaterPos = -1
	t.GreaterAction = Move{}
}

func (t *Trick) ActionInfo() (int, []any, int, []any) {
	if t.CurrentNil {
		return t.CurrentPos, nil, t.GreaterPos, t.GreaterAction.ToJSON()
	}
	return t.CurrentPos, t.CurrentAction.ToJSON(), t.GreaterPos, t.GreaterAction.ToJSON()
}

func (t *Trick) UpdateGreaterAction(action Move) {
	t.GreaterPos = t.CurrentPos
	t.GreaterAction = action
}

type Player struct {
	Name       string
	Pos        int
	Victory    int
	HeartsNum  int
	HandCards  []Card
	PlayArea   *Move
	Rank       int
	StuckTimes int
}

func NewPlayer(name string, index int) Player {
	return Player{Name: name, Pos: index, Rank: 2}
}

func (p *Player) ResetForStart() {
	p.PlayArea = nil
	p.StuckTimes = 0
	p.Rank = 2
	p.HeartsNum = 0
}

func (p *Player) UpdateRank(inc int) {
	p.Rank += inc
	if p.Rank > 14 {
		p.Rank = 14
	}
}

func (p Player) PublicInfo() map[string]any {
	var playArea any
	if p.PlayArea != nil {
		playArea = p.PlayArea.ToJSON()
	}
	return map[string]any{"rest": len(p.HandCards), "playArea": playArea}
}

func (p *Player) PlayCard(cards []string, heartsCard string) {
	for _, label := range cards {
		for i, card := range p.HandCards {
			if card.Label == label {
				p.HandCards = append(p.HandCards[:i], p.HandCards[i+1:]...)
				if label == heartsCard {
					p.HeartsNum--
				}
				break
			}
		}
	}
}

func (p *Player) AddCard(label string, currentRank string) {
	card := NewCard(label)
	inserted := false
	for i := 0; i < len(p.HandCards); i++ {
		if cmpHand(card, p.HandCards[i], currentRank, false) {
			p.HandCards = append(p.HandCards, Card{})
			copy(p.HandCards[i+1:], p.HandCards[i:])
			p.HandCards[i] = card
			inserted = true
			break
		}
	}
	if !inserted {
		p.HandCards = append(p.HandCards, card)
	}
}

func (p Player) RedJokerNum() int {
	n := len(p.HandCards)
	if n == 0 || p.HandCards[n-1].Label != "HR" {
		return 0
	}
	if n >= 2 && p.HandCards[n-2].Label == "HR" {
		return 2
	}
	return 1
}

func (p Player) MaxCards(rank string, rankCard string) []Action {
	if len(p.HandCards) == 0 {
		return nil
	}
	last := p.HandCards[len(p.HandCards)-1]
	if last.Label == "HR" {
		return []Action{{Type: "tribute", Rank: "tribute", Cards: []string{"HR"}}}
	}
	if last.Label == "SB" {
		return []Action{{Type: "tribute", Rank: "tribute", Cards: []string{"SB"}}}
	}
	avoidH := false
	idx := len(p.HandCards) - 1
	if last.Label == rankCard {
		checkIdx := len(p.HandCards) - 1 - p.HeartsNum
		if checkIdx >= 0 && string(p.HandCards[checkIdx].Rank) == rank {
			avoidH = true
		}
		idx = checkIdx
	} else if string(last.Rank) == rank && last.Label != rankCard && p.HeartsNum > 0 {
		avoidH = true
	}
	targetRank := p.HandCards[idx].Rank
	seen := map[string]bool{}
	actions := []Action{}
	for _, card := range p.HandCards {
		if card.Rank != targetRank {
			continue
		}
		if avoidH && card.Suit == 'H' {
			continue
		}
		if !seen[card.Label] {
			seen[card.Label] = true
			actions = append(actions, Action{Type: "tribute", Rank: "tribute", Cards: []string{card.Label}})
		}
	}
	return actions
}

func (p Player) LessThanTen(currentRank string) []Action {
	seen := map[string]bool{}
	actions := []Action{}
	for _, card := range p.HandCards {
		if card.Digital&0x00ff <= 10 && string(card.Rank) != currentRank && !seen[card.Label] {
			seen[card.Label] = true
			actions = append(actions, Action{Type: "back", Rank: "back", Cards: []string{card.Label}})
		}
	}
	return actions
}

type Finish struct {
	Order     []int
	TriShip   [][2]int
	BckShip   [][2]int
	TriCards  [][3]any
	BckCards  [][3]any
	Index     int
	FirstPlay int
}

func (f *Finish) Add(pos int) {
	f.Order = append(f.Order, pos)
}

func (f *Finish) EpisodeOver() bool {
	if len(f.Order) == 0 {
		return false
	}
	teammate := (f.Order[len(f.Order)-1] + 2) % 4
	for _, pos := range f.Order {
		if pos == teammate {
			return true
		}
	}
	return false
}

func (f *Finish) Settlement() (int, int, int) {
	if (f.Order[0]+2)%4 == f.Order[1] {
		inc := 3
		order := []int{0, 1, 2, 3}
		f.TriShip = append(f.TriShip, [2]int{f.Order[len(f.Order)-1], pyIndex(order, f.Order[len(f.Order)-1]-1)})
		f.TriShip = append(f.TriShip, [2]int{f.Order[len(f.Order)-2], pyIndex(order, f.Order[len(f.Order)-2]-1)})
		f.BckShip = append(f.BckShip, [2]int{pyIndex(order, f.Order[len(f.Order)-1]-1), f.Order[len(f.Order)-1]})
		f.BckShip = append(f.BckShip, [2]int{pyIndex(order, f.Order[len(f.Order)-2]-1), f.Order[len(f.Order)-2]})
		return f.Order[0], (f.Order[0] + 2) % 4, inc
	}
	if (f.Order[0]+2)%4 == f.Order[2] {
		inc := 2
		f.TriShip = append(f.TriShip, [2]int{f.Order[len(f.Order)-1], f.Order[0]})
		f.BckShip = append(f.BckShip, [2]int{f.Order[0], f.Order[len(f.Order)-1]})
		return f.Order[0], (f.Order[0] + 2) % 4, inc
	}
	inc := 1
	f.TriShip = append(f.TriShip, [2]int{f.Order[len(f.Order)-1], f.Order[0]})
	f.BckShip = append(f.BckShip, [2]int{f.Order[0], f.Order[len(f.Order)-1]})
	return f.Order[0], (f.Order[0] + 2) % 4, inc
}

func pyIndex(values []int, idx int) int {
	if idx < 0 {
		idx += len(values)
	}
	return values[idx]
}

func (f *Finish) Clear() {
	f.FirstPlay = -1
	f.Index = 0
	f.Order = nil
	f.TriShip = nil
	f.BckShip = nil
	f.TriCards = nil
	f.BckCards = nil
}

func (f Finish) First() int  { return f.Order[0] }
func (f Finish) Third() int  { return f.Order[2] }
func (f Finish) Fourth() int { return f.Order[3] }

func (f Finish) FindShip(pos int, kind string) (int, int) {
	ships := f.TriShip
	if kind == "bck" {
		ships = f.BckShip
	}
	for _, ship := range ships {
		if ship[0] == pos || ship[1] == pos {
			return ship[0], ship[1]
		}
	}
	return -1, -1
}

func notifyBeginning(handCards []Card, index int, curRank int, selfRank int, oppoRank int) map[string]any {
	return map[string]any{
		"type":      "notify",
		"stage":     "beginning",
		"handCards": FormatCards(handCards),
		"myPos":     index,
		"curRank":   curRank,
		"selfRank":  selfRank,
		"oppoRank":  oppoRank,
	}
}

func notifyPlay(curPos int, curAction []any, greaterPos int, greaterAction []any) map[string]any {
	return map[string]any{
		"type":          "notify",
		"stage":         "play",
		"curPos":        curPos,
		"curAction":     curAction,
		"greaterPos":    greaterPos,
		"greaterAction": greaterAction,
	}
}

func notifyEpisodeOver(curRank string, order []int, restCards []any) map[string]any {
	return map[string]any{
		"type":      "notify",
		"stage":     "episodeOver",
		"curRank":   curRank,
		"order":     append([]int(nil), order...),
		"restCards": restCards,
	}
}

func notifyGameOver(curTimes int, settingTimes int) map[string]any {
	return map[string]any{
		"type":         "notify",
		"stage":        "gameOver",
		"curTimes":     curTimes,
		"settingTimes": settingTimes,
	}
}

func notifyGameResult(respectiveWins []int, respectiveDraws []int) map[string]any {
	return map[string]any{
		"type":       "notify",
		"stage":      "gameResult",
		"victoryNum": append([]int(nil), respectiveWins...),
		"draws":      append([]int(nil), respectiveDraws...),
	}
}

func notifyTribute(tributeCards [][3]any) map[string]any {
	result := make([]any, len(tributeCards))
	for i, item := range tributeCards {
		result[i] = []any{item[0], item[1], item[2]}
	}
	return map[string]any{"type": "notify", "stage": "tribute", "result": result}
}

func notifyBack(backCards [][3]any) map[string]any {
	result := make([]any, len(backCards))
	for i, item := range backCards {
		result[i] = []any{item[0], item[1], item[2]}
	}
	return map[string]any{"type": "notify", "stage": "back", "result": result}
}

func notifyAntiTribute(antiNum int, antiPos []int) map[string]any {
	return map[string]any{"type": "notify", "stage": "anti-tribute", "antiNum": antiNum, "antiPos": antiPos}
}

func actBody(stage string, handCards []string, publicInfo []map[string]any, selfRank string, oppoRank string, cur string, curPos int, curAction []any, greaterPos int, greaterAction []any, actionList []any) map[string]any {
	return map[string]any{
		"type":          "act",
		"stage":         stage,
		"handCards":     handCards,
		"publicInfo":    publicInfo,
		"selfRank":      selfRank,
		"oppoRank":      oppoRank,
		"curRank":       cur,
		"curPos":        curPos,
		"curAction":     curAction,
		"greaterPos":    greaterPos,
		"greaterAction": greaterAction,
		"actionList":    actionList,
		"indexRange":    len(actionList) - 1,
	}
}
