package client

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/canonical/oci-factory/cli-client/internals/logger"
)

const workflowRunsURL = "https://api.github.com/repos/canonical/oci-factory/actions/workflows/Image.yaml/runs"
const getWorkflowRunIdMaxTry = 60

// const getWorkflowRunTimeWindow = 5 * time.Minute
const getWorkflowRunTimeWindow = 1024 * time.Hour

type WorkflowRunsScheme struct {
	TotalCount   int                       `json:"total_count"`
	WorkflowRuns []WorkflowSingleRunScheme `json:"workflow_runs"`
}

type WorkflowSingleRunScheme struct {
	Id      int    `json:"id"`
	JobsURL string `json:"jobs_url"`
}

type WorkflowJobsScheme struct {
	Jobs []WorkflowSingleJobScheme `json:"jobs"`
}

type WorkflowSingleJobScheme struct {
	Name  string                     `json:"name"`
	Steps []WorkflowSingleStepScheme `json:"steps"`
}

type WorkflowSingleStepScheme struct {
	Name string `json:"name"`
}

// Is there a better way to avoid passing token for every call?
func GetWorkflowRunID(externalRefID string, accessToken string) (int, error) {

	// Get the current time in UTC and subtract the deltaTime
	timeWindow := time.Now().UTC().Add(-getWorkflowRunTimeWindow).Format("2006-01-02T15:04")
	timeWindowFilter := "?created=%3E" + timeWindow

	header := NewGithubAuthHeaderMap(accessToken)
	request, err := http.NewRequest("GET", workflowRunsURL+timeWindowFilter, nil)
	if err != nil {
		logger.Panicf("Unable to create request: %v", err)
	}
	SetHeaderWithMap(request, header)
	client := &http.Client{}
	response, err := client.Do(request)
	if err != nil {
		logger.Panicf("Unable to send request: %v", err)
	}
	defer response.Body.Close()

	if response.StatusCode != http.StatusOK {
		logger.Noticef("Request failed: %s", response.Status)
		responseBody, err := io.ReadAll(response.Body)
		if err != nil {
			logger.Panicf("Unable to read response body: %v", err)
		}
		logger.Panicf("Response: %s", string(responseBody))
	}

	responseBody, err := io.ReadAll(response.Body)
	if err != nil {
		logger.Panicf("Unable to read response body: %v", err)
	}

	var workflowRuns WorkflowRunsScheme
	err = json.Unmarshal(responseBody, &workflowRuns)
	if err != nil {
		logger.Panicf("Unable to unmarshal json: %v", err)
	}

	for numTries := 1; numTries < getWorkflowRunIdMaxTry+1; numTries++ {
		for _, workFlowSingleRun := range workflowRuns.WorkflowRuns {
			jobsURL := workFlowSingleRun.JobsURL
			request, err := http.NewRequest("GET", jobsURL, nil)
			if err != nil {
				logger.Panicf("Unable to create request: %v", err)
			}
			SetHeaderWithMap(request, header)
			client := &http.Client{}
			response, err := client.Do(request)
			if err != nil {
				logger.Panicf("Unable to send request: %v", err)
			}
			defer response.Body.Close()

			if response.StatusCode != http.StatusOK {
				logger.Noticef("Request failed: %s", response.Status)
				responseBody, err := io.ReadAll(response.Body)
				if err != nil {
					logger.Panicf("Unable to read response body: %v", err)
				}
				logger.Panicf("Response: %s", string(responseBody))
			}

			responseBody, err := io.ReadAll(response.Body)
			if err != nil {
				logger.Panicf("Unable to read response body: %v", err)
			}

			var workflowJobs WorkflowJobsScheme
			err = json.Unmarshal(responseBody, &workflowJobs)
			if err != nil {
				logger.Panicf("Unable to unmarshal json: %v", err)
			}

			for _, job := range workflowJobs.Jobs {
				if job.Name == "Prepare build" {
					for _, step := range job.Steps {
						if step.Name == externalRefID {
							return workFlowSingleRun.Id, nil
						}
					}
				}

			}
		}
		time.Sleep(5 * time.Second)
		logger.Noticef("Retrying getting workflow run ID for %s (%d/%d)\n", externalRefID, numTries, getWorkflowRunIdMaxTry)
	}

	return -1, fmt.Errorf("get workflow run ID failed after max tryouts")
}
