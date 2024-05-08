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

type CourseDetails map[string]map[string]interface{}

func Map(taskQueue chan map[string]interface{}, client *openai.Client, intermediate chan<- map[string]interface{}, bar *pb.ProgressBar, wg *sync.WaitGroup, workerID int) {
	defer wg.Done()
	for courseDetail := range taskQueue {
		retries := 0

		for retries < 3 {
			req := openai.ChatCompletionRequest{
				Model:       openai.GPT3Dot5Turbo,
				Temperature: 1.2,
				Messages: []openai.ChatCompletionMessage{
					{
						Role:    openai.ChatMessageRoleSystem,
						Content: systemPrompt,
					},
					{
						Role: openai.ChatMessageRoleUser,
						Content: fmt.Sprintf(prompt, fmt.Sprintf("Course Code: %s\nCourse Title: %s\nInstructor: %s\nDescription: %s\nCrosslistings: %s\nDistribution Area: %s\nAssignments: %s\nReading List: %s\nSemester: %s\nTrack: %s",
							courseDetail["Department Code"],
							courseDetail["Course Title"],
							courseDetail["Instructor Name"],
							courseDetail["Description"],
							courseDetail["Crosslistings"],
							courseDetail["Distribution Area Long"],
							courseDetail["Assignments"],
							courseDetail["Reading List"],
							courseDetail["Semester"],
							courseDetail["Track"])),
					},
				},
			}

			resp, err := client.CreateChatCompletion(context.Background(), req)
			if err != nil {
				if strings.Contains(err.Error(), "Rate limit reached") || strings.Contains(err.Error(), "status code: 502") {
					retries++
					fmt.Printf("[Worker %d] Error encountered (Rate limit or Bad Gateway). Retry attempt: %d\n", workerID, retries)
					time.Sleep(time.Duration(retries*100) * time.Millisecond)
					continue
				} else {
					fmt.Printf("[Worker %d] Error: %v\n", workerID, err)
					break
				}
			}

			formattedDetails := fmt.Sprintf("Great question! Here are some details for the course \"%s\" (%s):\n\nInstructor: %s\n\nDescription: %s\n\nCrosslistings: %s\nDistribution Area: %s\n\nAssignments: %s\nReading List: %s\n\nOffered in: %s\nTrack: %s",
				courseDetail["Course Title"],
				fmt.Sprintf("%s %s", courseDetail["Department Code"], courseDetail["Catalog Number"]),
				courseDetail["Instructor Name"],
				courseDetail["Description"],
				courseDetail["Crosslistings"],
				courseDetail["Distribution Area Long"],
				courseDetail["Assignments"],
				courseDetail["Reading List"],
				courseDetail["Semester"],
				courseDetail["Track"])

			entry := map[string]interface{}{
				"messages": []map[string]interface{}{
					{
						"role":    "system",
						"content": systemPrompt,
					},
					{
						"role":    "user",
						"content": resp.Choices[0].Message.Content,
					},
					{
						"role":    "assistant",
						"content": formattedDetails,
					},
				},
			}

			intermediate <- entry
			bar.Increment()
			break
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
	detailsFile, err := os.Open("../course_details.json")
	if err != nil {
		fmt.Printf("Error opening details file: %v\n", err)
		return
	}
	defer detailsFile.Close()
	detailsData, _ := io.ReadAll(detailsFile)
	var courseDetails CourseDetails
	var json = jsoniter.ConfigCompatibleWithStandardLibrary
	json.Unmarshal(detailsData, &courseDetails)

	apiKey := os.Getenv("OPENAI_API_KEY")
	client := openai.NewClient(apiKey)

	var wg sync.WaitGroup
	maxGoroutines := 16
	intermediate := make(chan map[string]interface{}, maxGoroutines*10)
	taskQueue := make(chan map[string]interface{}, len(courseDetails))
	bar := pb.StartNew(len(courseDetails))

	outputFile, err := os.Create("course_details_dataset.jsonl")
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
		go Map(taskQueue, client, intermediate, bar, &wg, i)
	}

	fmt.Println("Queueing course details for processing...")
	for _, detail := range courseDetails {
		taskQueue <- detail
	}

	close(taskQueue)
	fmt.Println("All course details queued. Waiting for processing to complete...")

	// Wait for all worker goroutines to complete
	wg.Wait()

	// Close the intermediate channel after all worker goroutines are done
	close(intermediate)

	// Wait for the Reduce goroutine to finish
	wg.Wait()

	bar.Finish()
	fmt.Println("Dataset generated successfully.")
}

const prompt string = `Your job is to imagine yourself as a student curious about academic course planning. ` +
	`Your goal is to anticipate and simulate what an undergraduate student might have asked ` +
	`to the large language model on the course planning web application. DO NOT PREFACE WITH ANYTHING. ` +
	`Just begin your message with the student's response. That is, carefully and realistically craft a prompt ` +
	`that the student would have most likely been used to generate the following response. ` +
	`The student is interested in learning more about one or potentially multiple of the following attributes of a course: `

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
