package main

import (
	"context"
	"fmt"
	"io"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/cheggaaa/pb/v3"
	jsoniter "github.com/json-iterator/go"
	openai "github.com/sashabaranov/go-openai"
)

type CourseComment struct {
	CourseGUID string `json:"course_guid"`
	Comment    string `json:"comment"`
}

type CourseDetails map[string]map[string]interface{}

func Map(taskQueue chan CourseComment, courseDetails CourseDetails, client *openai.Client, intermediate chan<- map[string]interface{}, bar *pb.ProgressBar, wg *sync.WaitGroup, workerID int) {
	defer wg.Done()
	for comment := range taskQueue {
		details, ok := courseDetails[comment.CourseGUID]
		if !ok {
			fmt.Printf("[Worker %d] Course details not found for GUID: %s\n", workerID, comment.CourseGUID)
			continue
		}

		courseInfo := fmt.Sprintf("Course Title: %s\nCourse Code: %s %s", details["Course Title"], details["Department Code"], details["Catalog Number"])

		var resp openai.ChatCompletionResponse
		var err error
		retries := 0

		for retries < 3 {
			req := openai.ChatCompletionRequest{
				Model:       openai.GPT3Dot5Turbo,
				Temperature: 1.1,
				Messages: []openai.ChatCompletionMessage{
					{
						Role:    openai.ChatMessageRoleSystem,
						Content: systemPrompt,
					},
					{
						Role:    openai.ChatMessageRoleUser,
						Content: prompt + "\n\nContext: " + courseInfo + "\n\nResponse: " + comment.Comment,
					},
				},
			}

			resp, err = client.CreateChatCompletion(context.Background(), req)
			if err != nil {
				if strings.Contains(err.Error(), "status code:") {
					retries++
					fmt.Printf("[Worker %d] Error encountered (Status code: %s). Retry attempt: %d\n", workerID, err.Error(), retries)
					time.Sleep(time.Duration(retries*100) * time.Millisecond)
					continue
				} else {
					fmt.Printf("[Worker %d] Error: %v\n", workerID, err)
					break
				}
			}
			break
		}

		if err == nil {
			entry := map[string]interface{}{
				"messages": []map[string]interface{}{
					{
						"role":    "system",
						"content": systemPrompt,
					},
					{
						"role":    "user",
						"content": resp.Choices[0].Message.Content + "\n\nNote: If I don't not explicitly ask for additional information or context about the course, do not offer it.",
					},
					{
						"role":    "assistant",
						"content": comment.Comment,
					},
				},
			}

			intermediate <- entry
			bar.Increment()
		}
	}
}

func Reduce(intermediate <-chan map[string]interface{}, outputFile *os.File, wg *sync.WaitGroup) {
	defer wg.Done()
	var json = jsoniter.ConfigCompatibleWithStandardLibrary

	encoder := json.NewEncoder(outputFile)
	encoder.SetEscapeHTML(false)

	entriesProcessed := 0
	startTime := time.Now()

	for entry := range intermediate {
		if err := encoder.Encode(entry); err != nil {
			fmt.Printf("Error encoding entry: %v\n", err)
		}

		entriesProcessed++
		if entriesProcessed%1024 == 0 {
			elapsedTime := time.Since(startTime)
			fmt.Printf("Processed %d entries in %s\n", entriesProcessed, elapsedTime)
		}
	}

	fmt.Printf("Total entries processed: %d\n", entriesProcessed)
}

func main() {
	cwd, _ := os.Getwd()
	fmt.Println("Current working directory:", cwd)
	commentsFile, err := os.Open("../course_comments.json")
	if err != nil {
		fmt.Printf("Error opening comments file: %v\n", err)
		return
	}
	defer commentsFile.Close()
	commentsData, err := io.ReadAll(commentsFile)
	if err != nil {
		fmt.Printf("Error reading comments file: %v\n", err)
		return
	}
	var courseComments []CourseComment
	var json = jsoniter.ConfigCompatibleWithStandardLibrary
	err = json.Unmarshal(commentsData, &courseComments)
	if err != nil {
		fmt.Printf("Error unmarshalling comments data: %v\n", err)
		return
	}

	detailsFile, err := os.Open("../course_details.json")
	if err != nil {
		fmt.Printf("Error opening details file: %v\n", err)
		return
	}
	defer detailsFile.Close()
	detailsData, _ := io.ReadAll(detailsFile)
	var courseDetails CourseDetails
	json.Unmarshal(detailsData, &courseDetails)

	apiKey := os.Getenv("OPENAI_API_KEY")
	client := openai.NewClient(apiKey)

	var wg sync.WaitGroup
	maxGoroutines := 16
	intermediate := make(chan map[string]interface{}, maxGoroutines*10)
	taskQueue := make(chan CourseComment, len(courseComments))
	bar := pb.StartNew(len(courseComments))

	outputFile, err := os.Create("course_comments_dataset.jsonl")
	if err != nil {
		fmt.Printf("Error creating dataset file: %v\n", err)
		return
	}
	defer outputFile.Close()

	wg.Add(1)
	go Reduce(intermediate, outputFile, &wg)

	fmt.Printf("Starting data processing with %d worker goroutines...\n", maxGoroutines)
	for i := 0; i < maxGoroutines; i++ {
		wg.Add(1)
		go Map(taskQueue, courseDetails, client, intermediate, bar, &wg, i)
	}

	fmt.Println("Queueing course comments for processing...")
	for _, comment := range courseComments {
		taskQueue <- comment
	}

	close(taskQueue)
	fmt.Println("All course comments queued. Waiting for processing to complete...")

	wg.Wait()

	close(intermediate)

	wg.Wait()

	bar.Finish()
	fmt.Println("Dataset generated successfully.")
}

const prompt string = `Your job is to imagine yourself as a student curious about ` +
	`academic course planning. Your goal is to anticipate and simulate ` +
	`what an undergraduate student might have asked to the ` +
	`large language model on the course planning web application. ` +
	`DO NOT PREFACE WITH ANYTHING, and DO NOT INSERT YOUR OWN OPINION. ` +
	`Just begin your message with the student's response. ` +
	`That is, carefully and realistically craft a prompt that the student ` +
	`would have most likely used to generate the following response: `

const systemPrompt string = `The assistant is Sage, a honest, helpful, and harmless ` +
	`academic planning assistant for students at Princeton University.\n\n` +
	`You are Sage, created by Windsor Nguyen '25 from the hoagie.io team as part of ` +
	`his junior year independent work project, "hoagieplan," where students can ` +
	`research and plan for their academic courses. When asked if you are an AGI or ` +
	`the like, you should humbly respond that you are not.\n\n` +
	`Sage should give concise responses to very simple questions, but provide ` +
	`thorough responses to more complex and open-ended questions. ` +
	`If you are asked to assist with tasks involving the expression of views held ` +
	`by a significant number of people, Sage provides assistance with the task even ` +
	`if it personally disagrees with the views being expressed but follows this with ` +
	`a nudge to broader perspectives.\n\n` +
	`Sage doesn't engage in stereotyping, including the negative stereotyping of ` +
	`majority groups. If asked about controversial topics, Sage tries to provide ` +
	`careful thoughts and objective information without downplaying its harmful ` +
	`content or implying that there are reasonable perspectives on both sides.\n\n` +
	`Sage is happy to help with writing, analysis, question answering, math, coding, ` +
	`and all sorts of other tasks. Sage uses markdown for coding.\n\n` +
	`Sage does not mention this information about itself unless the information is ` +
	`directly pertinent to the human's query.`
