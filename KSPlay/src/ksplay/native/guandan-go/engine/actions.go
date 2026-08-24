package engine

import (
	"encoding/json"
	"sort"
)

const PassType = "PASS"

var (
	ranks       = []byte{'A', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K'}
	rankValue   = map[byte]int{'A': 14, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'B': 16, 'R': 17}
	numberValue = map[byte]int{'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13}
	valueRank   = map[int]byte{1: 'A', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9', 10: 'T', 11: 'J', 12: 'Q', 13: 'K'}
	suitOrder   = map[byte]int{'S': 0, 'H': 1, 'C': 2, 'D': 3}
)

type Action struct {
	Type  string   `json:"type"`
	Rank  string   `json:"rank"`
	Cards []string `json:"cards"`
}

func (a Action) Tuple() []any {
	if a.Type == PassType {
		return []any{PassType, PassType, PassType}
	}
	return []any{a.Type, a.Rank, a.Cards}
}

func FirstActions(handCards []string, currentRank string) []Action {
	labels := sortedLabels(handCards, currentRank)
	handCounts := countLabels(labels)
	wildCards := wildCards(labels, currentRank)
	naturalLabels := withoutWild(labels, currentRank)
	sequenceLabels := withoutJokers(naturalLabels)
	actions := make([]Action, 0, 128)
	seen := map[string]bool{}
	add := func(action Action) {
		var ok bool
		action, ok = canonicalizeAction(action, currentRank)
		if !ok {
			return
		}
		key := actionKey(action)
		if !seen[key] {
			seen[key] = true
			actions = append(actions, action)
		}
	}

	byRankMap := byRank(naturalLabels)
	sequenceByRank := byRank(sequenceLabels)
	sequenceBySuitRank := bySuitRank(sequenceLabels)

	for _, label := range labels {
		add(Action{Type: "Single", Rank: actionRank(label[1], currentRank), Cards: []string{label}})
	}

	sameRankGroups := map[byte]map[int][][]string{}
	for _, rank := range candidateGroupRanks(byRankMap, currentRank) {
		groupsBySize := map[int][][]string{}
		for size := 2; size <= len(byRankMap[rank])+len(wildCards); size++ {
			groups := sameRankGroupsFor(
				byRankMap[rank], wildCards, size, rank, currentRank, true,
			)
			if len(groups) > 0 {
				groupsBySize[size] = groups
			}
		}
		sameRankGroups[rank] = groupsBySize
	}

	for _, rank := range sortedGroupRanks(sameRankGroups, currentRank) {
		groupsBySize := sameRankGroups[rank]
		for _, combo := range groupsBySize[2] {
			add(Action{Type: "Pair", Rank: actionRank(rank, currentRank), Cards: combo})
		}
		for _, combo := range groupsBySize[3] {
			add(Action{Type: "Trips", Rank: actionRank(rank, currentRank), Cards: combo})
		}
		for _, size := range sortedSizes(groupsBySize) {
			if size >= 4 {
				for _, combo := range groupsBySize[size] {
					add(Action{Type: "Bomb", Rank: actionRank(rank, currentRank), Cards: combo})
				}
			}
		}
	}

	jokers := jokerCards(labels)
	if countLabel(labels, "SB") >= 2 {
		add(Action{Type: "Pair", Rank: "B", Cards: []string{"SB", "SB"}})
	}
	if countLabel(labels, "HR") >= 2 {
		add(Action{Type: "Pair", Rank: "R", Cards: []string{"HR", "HR"}})
	}
	if len(jokers) >= 4 {
		add(Action{Type: "FourKings", Rank: "R", Cards: takeCards(jokers, 4)})
	}

	pairGroups := filterGroups(sameRankGroups, 2)
	if countLabel(labels, "SB") >= 2 {
		pairGroups['B'] = [][]string{{"SB", "SB"}}
	}
	if countLabel(labels, "HR") >= 2 {
		pairGroups['R'] = [][]string{{"HR", "HR"}}
	}
	tripsGroups := filterGroups(sameRankGroups, 3)
	for _, tripRank := range sortedGroupRanks2(tripsGroups, currentRank) {
		for _, pairRank := range sortedGroupRanks2(pairGroups, currentRank) {
			if pairRank == tripRank {
				continue
			}
			for _, trip := range tripsGroups[tripRank] {
				for _, pair := range pairGroups[pairRank] {
					if cardsAvailable(handCounts, trip, pair) {
						add(Action{Type: "ThreeWithTwo", Rank: actionRank(tripRank, currentRank), Cards: concat(trip, pair)})
					}
				}
			}
		}
	}

	sequencePairGroups := sequenceSameRankGroups(
		sequenceByRank, wildCards, currentRank, 2,
	)
	sequenceTripsGroups := sequenceSameRankGroups(
		sequenceByRank, wildCards, currentRank, 3,
	)
	for _, seq := range rankSequences(2, currentRank) {
		if allRanksExist(sequenceTripsGroups, seq) {
			for _, left := range sequenceTripsGroups[seq[0]] {
				for _, right := range sequenceTripsGroups[seq[1]] {
					if cardsAvailable(handCounts, left, right) {
						add(Action{Type: "TwoTrips", Rank: actionRank(seq[len(seq)-1], currentRank), Cards: concat(left, right)})
					}
				}
			}
		}
	}

	for _, seq := range rankSequences(3, currentRank) {
		if allRanksExist(sequencePairGroups, seq) {
			for _, a := range sequencePairGroups[seq[0]] {
				for _, b := range sequencePairGroups[seq[1]] {
					for _, c := range sequencePairGroups[seq[2]] {
						if cardsAvailable(handCounts, a, b, c) {
							add(Action{Type: "ThreePair", Rank: actionRank(seq[len(seq)-1], currentRank), Cards: concat(a, b, c)})
						}
					}
				}
			}
		}
	}

	for _, seq := range rankSequences(5, currentRank) {
		for _, straight := range sequenceCardsByRankAll(
			seq, sequenceByRank, wildCards, currentRank,
		) {
			if !isPlainStraightFlushInterpretation(straight, currentRank) {
				add(Action{Type: "Straight", Rank: actionRank(seq[len(seq)-1], currentRank), Cards: straight})
			}
		}
		for _, suit := range []byte{'S', 'H', 'C', 'D'} {
			for _, sf := range sequenceCardsBySuitRankAll(
				seq, sequenceBySuitRank, wildCards, suit, currentRank,
			) {
				add(Action{Type: "StraightFlush", Rank: actionRank(seq[len(seq)-1], currentRank), Cards: sf})
			}
		}
	}

	return actions
}

func SecondActions(handCards []string, currentRank string, greater Action) []Action {
	actions := []Action{{Type: PassType, Rank: PassType}}
	if greater.Type == "" || greater.Type == PassType {
		return append(actions, FirstActions(handCards, currentRank)...)
	}

	gRank := byte(0)
	if greater.Rank != "" {
		gRank = greater.Rank[0]
	}
	labels := sortedLabels(handCards, currentRank)
	handCounts := countLabels(labels)
	wildCards := wildCards(labels, currentRank)
	naturalLabels := withoutWild(labels, currentRank)
	sequenceLabels := withoutJokers(naturalLabels)
	byRankMap := byRank(naturalLabels)
	sequenceByRank := byRank(sequenceLabels)
	sequenceBySuitRank := bySuitRank(sequenceLabels)
	seen := map[string]bool{}
	add := func(action Action) {
		var ok bool
		action, ok = canonicalizeAction(action, currentRank)
		if !ok || !CanBeat(action, greater, currentRank) {
			return
		}
		key := actionKey(action)
		if !seen[key] {
			seen[key] = true
			actions = append(actions, action)
		}
	}

	jokers := jokerCards(labels)
	if len(jokers) >= 4 {
		add(Action{Type: "FourKings", Rank: "R", Cards: takeCards(jokers, 4)})
	}
	for _, seq := range rankSequences(5, currentRank) {
		for _, suit := range []byte{'S', 'H', 'C', 'D'} {
			for _, sfCards := range sequenceCardsBySuitRankAll(
				seq, sequenceBySuitRank, wildCards, suit, currentRank,
			) {
				add(Action{
					Type:  "StraightFlush",
					Rank:  actionRank(seq[len(seq)-1], currentRank),
					Cards: sfCards,
				})
			}
		}
	}

	sameRankGroups := map[byte]map[int][][]string{}
	for _, rank := range candidateGroupRanks(byRankMap, currentRank) {
		groupsBySize := map[int][][]string{}
		for size := 2; size <= len(byRankMap[rank])+len(wildCards); size++ {
			groups := sameRankGroupsFor(
				byRankMap[rank], wildCards, size, rank, currentRank, true,
			)
			if len(groups) > 0 {
				groupsBySize[size] = groups
			}
		}
		sameRankGroups[rank] = groupsBySize
	}
	for _, rank := range sortedGroupRanks(sameRankGroups, currentRank) {
		for _, size := range sortedSizes(sameRankGroups[rank]) {
			if size >= 4 {
				for _, combo := range sameRankGroups[rank][size] {
					add(Action{Type: "Bomb", Rank: actionRank(rank, currentRank), Cards: combo})
				}
			}
		}
	}
	if countLabel(labels, "SB") >= 2 {
		add(Action{Type: "Pair", Rank: "B", Cards: []string{"SB", "SB"}})
	}
	if countLabel(labels, "HR") >= 2 {
		add(Action{Type: "Pair", Rank: "R", Cards: []string{"HR", "HR"}})
	}

	pairGroups := filterGroups(sameRankGroups, 2)
	if countLabel(labels, "SB") >= 2 {
		pairGroups['B'] = [][]string{{"SB", "SB"}}
	}
	if countLabel(labels, "HR") >= 2 {
		pairGroups['R'] = [][]string{{"HR", "HR"}}
	}
	tripsGroups := filterGroups(sameRankGroups, 3)
	switch greater.Type {
	case "Single":
		gRV := rankVal(gRank, currentRank)
		for _, label := range labels {
			if rankVal(label[1], currentRank) > gRV {
				add(Action{Type: "Single", Rank: actionRank(label[1], currentRank), Cards: []string{label}})
			}
		}
	case "Pair":
		gRV := rankVal(gRank, currentRank)
		for _, rank := range sortedGroupRanks2(pairGroups, currentRank) {
			if rankVal(rank, currentRank) > gRV {
				for _, combo := range pairGroups[rank] {
					add(Action{Type: "Pair", Rank: actionRank(rank, currentRank), Cards: combo})
				}
			}
		}
	case "Trips":
		gRV := rankVal(gRank, currentRank)
		for _, rank := range sortedGroupRanks2(tripsGroups, currentRank) {
			if rankVal(rank, currentRank) > gRV {
				for _, combo := range tripsGroups[rank] {
					add(Action{Type: "Trips", Rank: actionRank(rank, currentRank), Cards: combo})
				}
			}
		}
	case "ThreeWithTwo":
		gRV := rankVal(gRank, currentRank)
		for _, tripRank := range sortedGroupRanks2(tripsGroups, currentRank) {
			if rankVal(tripRank, currentRank) > gRV {
				for _, pairRank := range sortedGroupRanks2(pairGroups, currentRank) {
					if pairRank == tripRank {
						continue
					}
					for _, trip := range tripsGroups[tripRank] {
						for _, pair := range pairGroups[pairRank] {
							action := Action{Type: "ThreeWithTwo", Rank: actionRank(tripRank, currentRank), Cards: concat(trip, pair)}
							if cardsAvailable(handCounts, trip, pair) && cardCount(action) == cardCount(greater) {
								add(action)
							}
						}
					}
				}
			}
		}
	case "TwoTrips":
		sequenceTripsGroups := sequenceSameRankGroups(
			sequenceByRank, wildCards, currentRank, 3,
		)
		for _, seq := range rankSequences(2, currentRank) {
			if naturalRankVal(seq[len(seq)-1]) > naturalRankVal(gRank) &&
				allRanksExist(sequenceTripsGroups, seq) {
				for _, left := range sequenceTripsGroups[seq[0]] {
					for _, right := range sequenceTripsGroups[seq[1]] {
						if cardsAvailable(handCounts, left, right) {
							add(Action{Type: "TwoTrips", Rank: actionRank(seq[len(seq)-1], currentRank), Cards: concat(left, right)})
						}
					}
				}
			}
		}
	case "ThreePair":
		sequencePairGroups := sequenceSameRankGroups(
			sequenceByRank, wildCards, currentRank, 2,
		)
		for _, seq := range rankSequences(3, currentRank) {
			if naturalRankVal(seq[len(seq)-1]) > naturalRankVal(gRank) &&
				allRanksExist(sequencePairGroups, seq) {
				for _, a := range sequencePairGroups[seq[0]] {
					for _, b := range sequencePairGroups[seq[1]] {
						for _, c := range sequencePairGroups[seq[2]] {
							if cardsAvailable(handCounts, a, b, c) {
								add(Action{Type: "ThreePair", Rank: actionRank(seq[len(seq)-1], currentRank), Cards: concat(a, b, c)})
							}
						}
					}
				}
			}
		}
	case "Straight":
		for _, seq := range rankSequences(5, currentRank) {
			if naturalRankVal(seq[len(seq)-1]) > naturalRankVal(gRank) {
				for _, straight := range sequenceCardsByRankAll(
					seq, sequenceByRank, wildCards, currentRank,
				) {
					if !isPlainStraightFlushInterpretation(straight, currentRank) {
						add(Action{Type: "Straight", Rank: actionRank(seq[len(seq)-1], currentRank), Cards: straight})
					}
				}
			}
		}
	}
	return actions
}

func CanBeat(action Action, greater Action, currentRank string) bool {
	if greater.Type == "" || greater.Type == PassType {
		return action.Type != PassType
	}
	if action.Type == PassType {
		return false
	}
	if isBombLike(action) {
		if !isBombLike(greater) {
			return true
		}
		return bombKey(action, currentRank).greaterThan(bombKey(greater, currentRank))
	}
	if isBombLike(greater) || action.Type != greater.Type || cardCount(action) != cardCount(greater) {
		return false
	}
	ar, gr := byte(0), byte(0)
	if action.Rank != "" {
		ar = action.Rank[0]
	}
	if greater.Rank != "" {
		gr = greater.Rank[0]
	}
	if action.Type == "Straight" || action.Type == "ThreePair" || action.Type == "TwoTrips" {
		return naturalRankVal(ar) > naturalRankVal(gr)
	}
	return rankVal(ar, currentRank) > rankVal(gr, currentRank)
}

func ActionsAsTuples(actions []Action) []any {
	out := make([]any, len(actions))
	for i, action := range actions {
		out[i] = action.Tuple()
	}
	return out
}

func ParseTuple(raw json.RawMessage) (Action, error) {
	var tuple []json.RawMessage
	if err := json.Unmarshal(raw, &tuple); err != nil {
		return Action{}, err
	}
	if len(tuple) != 3 {
		return Action{}, nil
	}
	var typ, rank string
	_ = json.Unmarshal(tuple[0], &typ)
	_ = json.Unmarshal(tuple[1], &rank)
	if typ == PassType {
		return Action{Type: PassType, Rank: PassType}, nil
	}
	var cards []string
	_ = json.Unmarshal(tuple[2], &cards)
	return Action{Type: typ, Rank: rank, Cards: cards}, nil
}

func sortedLabels(cards []string, currentRank string) []string {
	labels := append([]string(nil), cards...)
	sort.SliceStable(labels, func(i, j int) bool {
		a, b := labels[i], labels[j]
		av, bv := rankVal(a[1], currentRank), rankVal(b[1], currentRank)
		if av != bv {
			return av < bv
		}
		as, bs := suitOrder[a[0]], suitOrder[b[0]]
		if as != bs {
			return as < bs
		}
		return a < b
	})
	return labels
}

func countLabels(labels []string) map[string]int {
	out := map[string]int{}
	for _, label := range labels {
		out[label]++
	}
	return out
}

func countLabel(labels []string, target string) int {
	count := 0
	for _, label := range labels {
		if label == target {
			count++
		}
	}
	return count
}

func byRank(labels []string) map[byte][]string {
	out := map[byte][]string{}
	for _, label := range labels {
		out[label[1]] = append(out[label[1]], label)
	}
	return out
}

func bySuitRank(labels []string) map[int][]string {
	out := map[int][]string{}
	for _, label := range labels {
		if label == "SB" || label == "HR" {
			continue
		}
		key := int(label[0])<<8 | int(label[1])
		out[key] = append(out[key], label)
	}
	return out
}

func wildCards(labels []string, currentRank string) []string {
	wild := "H" + currentRank
	out := []string{}
	for _, label := range labels {
		if label == wild {
			out = append(out, label)
		}
	}
	return out
}

func withoutWild(labels []string, currentRank string) []string {
	wild := "H" + currentRank
	out := []string{}
	for _, label := range labels {
		if label != wild {
			out = append(out, label)
		}
	}
	return out
}

func withoutJokers(labels []string) []string {
	out := []string{}
	for _, label := range labels {
		if label != "SB" && label != "HR" {
			out = append(out, label)
		}
	}
	return out
}

func candidateGroupRanks(groups map[byte][]string, currentRank string) []byte {
	seen := map[byte]bool{}
	for rank := range groups {
		if rank != 'B' && rank != 'R' {
			seen[rank] = true
		}
	}
	for rank := range rankValue {
		if rank != 'B' && rank != 'R' {
			seen[rank] = true
		}
	}
	out := make([]byte, 0, len(seen))
	for rank := range seen {
		out = append(out, rank)
	}
	sort.Slice(out, func(i, j int) bool { return rankVal(out[i], currentRank) < rankVal(out[j], currentRank) })
	return out
}

func sameRankGroupsFor(
	naturalCards, wildCards []string,
	size int,
	rank byte,
	currentRank string,
	allowPureWild bool,
) [][]string {
	minWild := max(0, size-len(naturalCards))
	maxWild := min(size, len(wildCards))
	out := [][]string{}
	for wildCount := minWild; wildCount <= maxWild; wildCount++ {
		naturalCount := size - wildCount
		if naturalCount == 0 && !allowPureWild && rank != currentRank[0] {
			continue
		}
		for _, natural := range combos(naturalCards, naturalCount) {
			for _, wild := range combos(wildCards, wildCount) {
				out = append(out, concat(natural, wild))
			}
		}
	}
	return out
}

func sequenceSameRankGroups(
	groups map[byte][]string,
	wildCards []string,
	currentRank string,
	size int,
) map[byte][][]string {
	out := map[byte][][]string{}
	for _, rank := range candidateGroupRanks(groups, currentRank) {
		values := sameRankGroupsFor(
			groups[rank], wildCards, size, rank, currentRank, true,
		)
		if len(values) > 0 {
			out[rank] = values
		}
	}
	return out
}

func combos(cards []string, size int) [][]string {
	if size == 0 {
		return [][]string{{}}
	}
	if size > len(cards) {
		return nil
	}
	out := [][]string{}
	var walk func(start int, cur []string)
	walk = func(start int, cur []string) {
		if len(cur) == size {
			out = append(out, append([]string(nil), cur...))
			return
		}
		for i := start; i <= len(cards)-(size-len(cur)); i++ {
			walk(i+1, append(cur, cards[i]))
		}
	}
	walk(0, nil)
	return out
}

func filterGroups(groups map[byte]map[int][][]string, size int) map[byte][][]string {
	out := map[byte][][]string{}
	for rank, bySize := range groups {
		if v, ok := bySize[size]; ok {
			out[rank] = v
		}
	}
	return out
}

func sortedGroupRanks(groups map[byte]map[int][][]string, currentRank string) []byte {
	out := make([]byte, 0, len(groups))
	for rank := range groups {
		out = append(out, rank)
	}
	sort.Slice(out, func(i, j int) bool { return rankVal(out[i], currentRank) < rankVal(out[j], currentRank) })
	return out
}

func sortedGroupRanks2(groups map[byte][][]string, currentRank string) []byte {
	out := make([]byte, 0, len(groups))
	for rank := range groups {
		out = append(out, rank)
	}
	sort.Slice(out, func(i, j int) bool { return rankVal(out[i], currentRank) < rankVal(out[j], currentRank) })
	return out
}

func sortedSizes(groups map[int][][]string) []int {
	out := make([]int, 0, len(groups))
	for size := range groups {
		out = append(out, size)
	}
	sort.Ints(out)
	return out
}

func jokerCards(labels []string) []string {
	out := []string{}
	for _, label := range labels {
		if label == "SB" || label == "HR" {
			out = append(out, label)
		}
	}
	return out
}

func sequenceCardsByRankAll(
	seq []byte,
	lookup map[byte][]string,
	wildCards []string,
	currentRank string,
) [][]string {
	out := [][]string{}
	var walk func(int, int, []string)
	walk = func(index, usedWilds int, selected []string) {
		if index == len(seq) {
			out = append(out, append([]string(nil), selected...))
			return
		}
		rank := seq[index]
		for _, card := range lookup[rank] {
			walk(index+1, usedWilds, append(selected, card))
		}
		// A level-heart card may be used in a sequence only at its own
		// natural point. This mirrors the frozen Python Sports Bureau rule.
		if currentRank != "" && rank == currentRank[0] && usedWilds < len(wildCards) {
			walk(index+1, usedWilds+1, append(selected, wildCards[usedWilds]))
		}
	}
	walk(0, 0, nil)
	return out
}

func sequenceCardsBySuitRankAll(
	seq []byte,
	lookup map[int][]string,
	wildCards []string,
	suit byte,
	currentRank string,
) [][]string {
	out := [][]string{}
	var walk func(int, int, []string)
	walk = func(index, usedWilds int, selected []string) {
		if index == len(seq) {
			out = append(out, append([]string(nil), selected...))
			return
		}
		rank := seq[index]
		key := int(suit)<<8 | int(rank)
		for _, card := range lookup[key] {
			walk(index+1, usedWilds, append(selected, card))
		}
		if currentRank != "" && rank == currentRank[0] && usedWilds < len(wildCards) {
			walk(index+1, usedWilds+1, append(selected, wildCards[usedWilds]))
		}
	}
	walk(0, 0, nil)
	return out
}

func isPlainStraightFlushInterpretation(cards []string, currentRank string) bool {
	wild := "H" + currentRank
	suits := map[byte]bool{}
	for _, card := range cards {
		if card == wild {
			return false
		}
		if card == "SB" || card == "HR" || len(card) < 2 {
			continue
		}
		suits[card[0]] = true
	}
	return len(suits) == 1
}

func rankSequences(length int, currentRank string) [][]byte {
	_ = currentRank
	order := []byte{'A', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'}
	out := [][]byte{}
	for start := 0; start+length <= len(order); start++ {
		out = append(out, append([]byte(nil), order[start:start+length]...))
	}
	return out
}

func cardsAvailable(counts map[string]int, groups ...[]string) bool {
	needed := map[string]int{}
	for _, group := range groups {
		for _, card := range group {
			needed[card]++
		}
	}
	for card, count := range needed {
		if count > counts[card] {
			return false
		}
	}
	return true
}

func allRanksExist(groups map[byte][][]string, seq []byte) bool {
	for _, rank := range seq {
		if _, ok := groups[rank]; !ok {
			return false
		}
	}
	return true
}

func canonicalizeAction(action Action, currentRank string) (Action, bool) {
	if action.Type == PassType {
		return action, true
	}
	if len(action.Cards) == 0 {
		return Action{}, false
	}
	switch action.Type {
	case "FourKings":
		action.Rank = "R"
	case "Single":
		if len(action.Cards[0]) < 2 {
			return Action{}, false
		}
		action.Rank = string(action.Cards[0][1])
	case "Straight", "StraightFlush", "ThreePair", "TwoTrips", "ThreeWithTwo":
		// The generator knows the semantic sequence/triple rank. Physical
		// level-heart cards make re-inference ambiguous, so preserve it.
	default:
		wild := "H" + currentRank
		counts := map[byte]int{}
		var best byte
		bestCount := 0
		for _, card := range action.Cards {
			if card == wild || len(card) < 2 {
				continue
			}
			rank := card[1]
			counts[rank]++
			if counts[rank] > bestCount {
				best, bestCount = rank, counts[rank]
			}
		}
		if bestCount == 0 {
			if currentRank == "" {
				return Action{}, false
			}
			action.Rank = currentRank
		} else {
			action.Rank = string(best)
		}
	}
	if action.Rank == "" {
		return Action{}, false
	}
	return action, true
}

func actionRank(rank byte, currentRank string) string { return string(rank) }

func rankVal(rank byte, currentRank string) int {
	if currentRank != "" && rank == currentRank[0] {
		return 15
	}
	return rankValue[rank]
}

func naturalRankVal(rank byte) int { return rankValue[rank] }

func isBombLike(action Action) bool {
	return action.Type == "Bomb" || action.Type == "StraightFlush" || action.Type == "FourKings"
}

type bombTuple struct{ a, b, c int }

func (t bombTuple) greaterThan(o bombTuple) bool {
	if t.a != o.a {
		return t.a > o.a
	}
	if t.b != o.b {
		return t.b > o.b
	}
	return t.c > o.c
}

func bombKey(action Action, currentRank string) bombTuple {
	rank := byte(0)
	if action.Rank != "" {
		rank = action.Rank[0]
	}
	switch action.Type {
	case "FourKings":
		return bombTuple{100, 0, 0}
	case "StraightFlush":
		return bombTuple{70, 0, naturalRankVal(rank)}
	default:
		size := cardCount(action)
		if size >= 6 {
			return bombTuple{80 + min(size, 8), size, rankVal(rank, currentRank)}
		}
		if size == 5 {
			return bombTuple{60, size, rankVal(rank, currentRank)}
		}
		return bombTuple{50, size, rankVal(rank, currentRank)}
	}
}

func cardCount(action Action) int { return len(action.Cards) }

func actionKey(action Action) string {
	b, _ := json.Marshal(action.Tuple())
	return string(b)
}

func takeCards(cards []string, size int) []string {
	if size > len(cards) {
		size = len(cards)
	}
	return append([]string(nil), cards[:size]...)
}

func concat(groups ...[]string) []string {
	n := 0
	for _, group := range groups {
		n += len(group)
	}
	out := make([]string, 0, n)
	for _, group := range groups {
		out = append(out, group...)
	}
	return out
}

func equalInts(a, b []int) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
