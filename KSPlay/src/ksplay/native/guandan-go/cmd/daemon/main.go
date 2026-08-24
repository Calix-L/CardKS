package main

import (
	"bufio"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"os"

	"github.com/Calix-L/CardKS/KSPlay/native/guandan-go/engine"
)

type request struct {
	Cmd               string    `json:"cmd"`
	TableID           int       `json:"tableId,omitempty"`
	Compact           bool      `json:"compact,omitempty"`
	ActionFeatures    bool      `json:"actionFeatures,omitempty"`
	ActionFeatureOnly bool      `json:"actionFeatureOnly,omitempty"`
	NoSummary         bool      `json:"noSummary,omitempty"`
	Name              string    `json:"name,omitempty"`
	Index             int       `json:"index,omitempty"`
	ActIndex          int       `json:"actIndex,omitempty"`
	DeckData          []string  `json:"deckData,omitempty"`
	FirstPlayer       *int      `json:"firstPlayer,omitempty"`
	Ops               []request `json:"ops,omitempty"`
}

type response struct {
	OK       bool           `json:"ok"`
	Error    string         `json:"error,omitempty"`
	Messages []engine.Msg   `json:"messages,omitempty"`
	Summary  map[string]any `json:"summary,omitempty"`
	Results  []response     `json:"results,omitempty"`
}

func main() {
	tables := map[int]*engine.Table{}
	scanner := bufio.NewScanner(os.Stdin)
	// The actionList can be large; keep enough room for one JSON command line.
	scanner.Buffer(make([]byte, 0, 1024*1024), 32*1024*1024)
	enc := json.NewEncoder(os.Stdout)
	enc.SetEscapeHTML(false)

	for scanner.Scan() {
		line := scanner.Bytes()
		var req request
		if err := json.Unmarshal(line, &req); err != nil {
			write(enc, response{OK: false, Error: err.Error()})
			continue
		}
		resp, err := handle(tables, req)
		if err != nil {
			write(enc, response{OK: false, Error: err.Error()})
			continue
		}
		write(enc, resp)
	}
	if err := scanner.Err(); err != nil {
		write(enc, response{OK: false, Error: err.Error()})
	}
}

func handle(tables map[int]*engine.Table, req request) (response, error) {
	if req.Cmd == "batch" {
		results := make([]response, len(req.Ops))
		for i, op := range req.Ops {
			if req.Compact {
				op.Compact = true
			}
			if req.ActionFeatures {
				op.ActionFeatures = true
			}
			if req.ActionFeatureOnly {
				op.ActionFeatureOnly = true
			}
			if req.NoSummary {
				op.NoSummary = true
			}
			resp, err := handle(tables, op)
			if err != nil {
				results[i] = response{OK: false, Error: err.Error()}
			} else {
				results[i] = resp
			}
		}
		return response{OK: true, Results: results}, nil
	}

	switch req.Cmd {
	case "new_table":
		t, err := engine.NewTable(req.DeckData, req.FirstPlayer)
		if err != nil {
			return response{}, err
		}
		tables[req.TableID] = t
		return maybeCompact(response{OK: true, Summary: optionalRuntimeSummary(t, req)}, req), nil
	case "drop_table":
		delete(tables, req.TableID)
		return response{OK: true}, nil
	case "add_player":
		t, err := requireTable(tables, req.TableID)
		if err != nil {
			return response{}, err
		}
		t.AddPlayer(req.Name, req.Index)
		return maybeCompact(response{OK: true, Summary: optionalRuntimeSummary(t, req)}, req), nil
	case "start":
		t, err := requireTable(tables, req.TableID)
		if err != nil {
			return response{}, err
		}
		msgs, err := t.Start()
		if err != nil {
			return response{}, err
		}
		return maybeCompact(response{OK: true, Messages: msgs, Summary: runtimeSummary(t, req)}, req), nil
	case "play":
		t, err := requireTable(tables, req.TableID)
		if err != nil {
			return response{}, err
		}
		msgs, err := t.Play(req.ActIndex)
		if err != nil {
			return response{}, err
		}
		return maybeCompact(response{OK: true, Messages: msgs, Summary: runtimeSummary(t, req)}, req), nil
	case "enter_tribute_stage":
		t, err := requireTable(tables, req.TableID)
		if err != nil {
			return response{}, err
		}
		msgs, err := t.EnterTributeStage(nil)
		if err != nil {
			return response{}, err
		}
		return maybeCompact(response{OK: true, Messages: msgs, Summary: runtimeSummary(t, req)}, req), nil
	case "start_new_episode_back_2":
		t, err := requireTable(tables, req.TableID)
		if err != nil {
			return response{}, err
		}
		msgs, err := t.StartNewEpisodeBack2(nil)
		if err != nil {
			return response{}, err
		}
		return maybeCompact(response{OK: true, Messages: msgs, Summary: runtimeSummary(t, req)}, req), nil
	case "tribute":
		t, err := requireTable(tables, req.TableID)
		if err != nil {
			return response{}, err
		}
		msgs, err := t.Tribute(req.ActIndex)
		if err != nil {
			return response{}, err
		}
		return maybeCompact(response{OK: true, Messages: msgs, Summary: runtimeSummary(t, req)}, req), nil
	case "back":
		t, err := requireTable(tables, req.TableID)
		if err != nil {
			return response{}, err
		}
		msgs, err := t.Back(req.ActIndex)
		if err != nil {
			return response{}, err
		}
		return maybeCompact(response{OK: true, Messages: msgs, Summary: runtimeSummary(t, req)}, req), nil
	case "close":
		os.Exit(0)
	}
	return response{}, fmt.Errorf("unknown cmd %q", req.Cmd)
}

func runtimeSummary(t *engine.Table, req request) map[string]any {
	return t.RuntimeSummary()
}

func optionalRuntimeSummary(t *engine.Table, req request) map[string]any {
	if req.NoSummary {
		return nil
	}
	return runtimeSummary(t, req)
}

func maybeCompact(resp response, req request) response {
	for i := range resp.Messages {
		compactBody(resp.Messages[i].Body, req)
	}
	return resp
}

func compactBody(body map[string]any, req request) {
	if raw, ok := body["actionList"]; ok && req.ActionFeatures {
		if actions, ok := raw.([]any); ok {
			body["actionCount"] = len(actions)
			body["actionFeaturesPacked"] = packedActionFeatures(actions)
			body["actionFeaturesEncoding"] = "nibble4"
			if req.ActionFeatureOnly && body["stage"] == "play" {
				delete(body, "actionList")
			}
		}
	}
	if raw, ok := body["handCards"]; ok && req.Compact {
		if cards, ok := raw.([]string); ok {
			body["handCardNums"] = cardNums(cards)
			delete(body, "handCards")
		}
	}
	if raw, ok := body["actionList"]; ok && req.Compact {
		if actions, ok := raw.([]any); ok {
			body["actionListCompact"] = compactActions(actions)
			delete(body, "actionList")
		}
	}
}

func packedActionFeatures(actions []any) string {
	counts := make([]byte, len(actions)*54)
	for i, raw := range actions {
		tuple, ok := raw.([]any)
		if !ok || len(tuple) != 3 {
			continue
		}
		cards, ok := tuple[2].([]string)
		if !ok {
			continue
		}
		base := i * 54
		for _, card := range cards {
			num := cardNum(card)
			if num >= 0 && num < 54 {
				counts[base+num]++
			}
		}
	}
	buf := make([]byte, len(actions)*27)
	for i := range actions {
		inBase := i * 54
		outBase := i * 27
		for j := 0; j < 27; j++ {
			lo := counts[inBase+j*2] & 0x0f
			hi := counts[inBase+j*2+1] & 0x0f
			buf[outBase+j] = lo | (hi << 4)
		}
	}
	return base64.StdEncoding.EncodeToString(buf)
}

func compactActions(actions []any) []any {
	out := make([]any, len(actions))
	for i, raw := range actions {
		tuple, ok := raw.([]any)
		if !ok || len(tuple) != 3 {
			out[i] = raw
			continue
		}
		typ, _ := tuple[0].(string)
		rank, _ := tuple[1].(string)
		cards, _ := tuple[2].([]string)
		out[i] = []any{typeCode(typ), rankCode(rank), cardNums(cards)}
	}
	return out
}

func cardNums(cards []string) []int {
	out := make([]int, 0, len(cards))
	for _, label := range cards {
		out = append(out, cardNum(label))
	}
	return out
}

func cardNum(label string) int {
	if len(label) != 2 {
		return -1
	}
	rankIndex := map[byte]int{'2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7, 'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12}
	if label == "SB" {
		return 52
	}
	if label == "HR" {
		return 53
	}
	r, ok := rankIndex[label[1]]
	if !ok {
		return -1
	}
	switch label[0] {
	case 'H':
		return r
	case 'S':
		return 13 + r
	case 'C':
		return 26 + r
	case 'D':
		return 39 + r
	}
	return -1
}

func typeCode(typ string) int {
	switch typ {
	case "PASS":
		return 0
	case "Single":
		return 1
	case "Pair":
		return 2
	case "Trips":
		return 3
	case "Bomb":
		return 4
	case "ThreeWithTwo":
		return 5
	case "TwoTrips":
		return 6
	case "ThreePair":
		return 7
	case "Straight":
		return 8
	case "StraightFlush":
		return 9
	case "FourKings":
		return 10
	case "tribute":
		return 11
	case "back":
		return 12
	}
	return -1
}

func rankCode(rank string) int {
	if len(rank) == 0 || rank == "PASS" || rank == "tribute" || rank == "back" {
		return 0
	}
	switch rank[0] {
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
	return -1
}

func requireTable(tables map[int]*engine.Table, tableID int) (*engine.Table, error) {
	table := tables[tableID]
	if table == nil {
		return nil, fmt.Errorf("table %d is not initialized", tableID)
	}
	return table, nil
}

func write(enc *json.Encoder, resp response) {
	if err := enc.Encode(resp); err != nil {
		fmt.Fprintf(os.Stderr, "encode response failed: %v\n", err)
	}
}
