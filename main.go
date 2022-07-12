package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
)

type plan struct {
	Message string `json:"@message"`
	Type    string `json:"type"`
	Change  struct {
		Action   string `json:"action"`
		Resource struct {
			Addr string `json:"addr"`
		} `json:"resource"`
	} `json:"change"`
}

func main() {
	var summary string
	var create []string
	var update []string
	var replace []string
	var deleted []string

	planFile := os.Args[1]
	prUrl := os.Args[2]
	token := os.Args[3]

	planContents, err := os.Open(planFile)
	defer planContents.Close()
	if err != nil {
		panic(err)
	}

	scanner := bufio.NewScanner(planContents)
	for scanner.Scan() {
		var plan plan
		err := json.Unmarshal(scanner.Bytes(), &plan)
		if err != nil {
			panic(err)
		}
		if plan.Type == "change_summary" {
			summary = "👉 " + plan.Message + "\n"
		}
		if plan.Change.Action == "create" {
			create = append(create, plan.Change.Resource.Addr)
		}
		if plan.Change.Action == "update" {
			update = append(update, plan.Change.Resource.Addr)
		}
		if plan.Change.Action == "replace" {
			replace = append(replace, plan.Change.Resource.Addr)
		}
		if plan.Change.Action == "delete" {
			deleted = append(deleted, plan.Change.Resource.Addr)
		}
	}

	appendSummary(&summary, create, "🛠️ Created")
	appendSummary(&summary, update, "🔀 Updated")
	appendSummary(&summary, replace, "♻️ Replaced")
	appendSummary(&summary, deleted, "❌ Deleted")
	fmt.Println(summary)
	postComment(prUrl, token, summary)
}

func appendSummary(summary *string, items []string, description string) {
	if len(items) > 0 {
		*summary += fmt.Sprintf("\n**%s**:\n", description)
		for _, s := range items {
			*summary += s + "\n"
		}
	}
}

func postComment(url string, token string, body string) {
	data, err := json.Marshal(map[string]string{"body": body})
	if err != nil {
		panic(err)
	}

	req, err := http.NewRequest("POST", url, bytes.NewBuffer(data))
	if err != nil {
		panic(err)
	}

	req.Header.Add("Authorization", fmt.Sprintf("token %s", token))

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		if err != nil {
			panic(err)
		}
	}
	defer resp.Body.Close()
	fmt.Println(resp.Status)
}
