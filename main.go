package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httputil"
	"os"
)

// Represents a single line from the command: `terraform plan -json`
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

// This script parses the output from the command `terraform plan -json` and posts a summary to a GitHub pull request.
//
// First run: `terraform plan -json > plan.json`
// Then run: `go run main.go plan.json <pr comments url> <github token>`
//
// <pr comments url> can be retrieved using the GitHub variable: github.event.pull_request.comments_url
// <github token> can be retrieved using the GitHub variable: secrets.GITHUB_TOKEN
func main() {
	var summary string
	var create []string
	var update []string
	var replace []string
	var deleted []string
	var varFile string

	planFile := os.Args[1]
	prUrl := os.Args[2]
	token := os.Args[3]

	if len(os.Args) >= 5 {
		varFile = os.Args[4]
	}

	fmt.Printf("Parsing: %s\n", planFile)
	planContents, err := os.Open(planFile)
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
		if plan.Type == "resource_drift" {
			continue
		}
		if varFile == "" && plan.Type == "change_summary" {
			summary = "👉 " + plan.Message + "\n"
		}
		if varFile != "" && plan.Type == "change_summary" {
			summary = "👉 " + plan.Message + " (" + varFile + ")\n"
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
	fmt.Printf("Summary: \n%s\n", summary)
	postComment(prUrl, token, summary)
}

// appendSummary adds a description and a list of items to the summary text string
func appendSummary(summary *string, items []string, description string) {
	if len(items) > 0 {
		fmt.Printf("Appending %d items for '%s' to summary\n", len(items), description)
		*summary += fmt.Sprintf("\n**%s**:\n", description)
		for _, s := range items {
			*summary += s + "\n"
		}
	} else {
		fmt.Printf("No items for '%s' to append to summary\n", description)
	}
}

// postComment sends a POST request to the given url to post the body to a pull request comment
func postComment(url string, token string, body string) {
	fmt.Printf("Posting summary to pull request comment: %s\n", url)
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
		panic(err)
	}
	responseBody, err := httputil.DumpResponse(resp, true)
	if err != nil {
		panic(err)
	}
	fmt.Printf("%s\n", string(responseBody))
}
