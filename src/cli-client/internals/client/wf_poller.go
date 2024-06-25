package client

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/briandowns/spinner"
	"github.com/canonical/oci-factory/cli-client/internals/logger"
)

const workflowRunsURL = "https://api.github.com/repos/canonical/oci-factory/actions/workflows/Image.yaml/runs"
const workflowSingleRunURL = "https://api.github.com/repos/canonical/oci-factory/actions/runs/"
const workflowSingleRunWebURL = "https://github.com/canonical/oci-factory/actions/runs/"

const getWorkflowRunIdMaxTry = 60
const getWorkflowRunTimeWindow = 5 * time.Minute
const spinnerRate = 500 * time.Millisecond
const pollingInterval = 5 * time.Second

type WorkflowRunsScheme struct {
	TotalCount   int                       `json:"total_count"`
	WorkflowRuns []WorkflowSingleRunScheme `json:"workflow_runs"`
}

const (
	StatusCompleted  string = "completed"
	StatusInProgress string = "in_progress"
	StatusQueued     string = "queued"
	StatusRequested  string = "requested"
	StatusWaiting    string = "waiting"
	StatusPending    string = "pending"
)

const (
	ConclusionActionRequired string = "action_required"
	ConclusionCancelled      string = "cancelled"
	ConclusionFailure        string = "failure"
	ConclusionNeutral        string = "neutral"
	ConclusionSkipped        string = "skipped"
	ConclusionStale          string = "stale"
	ConclusionSuccess        string = "success"
	ConclusionTimedOut       string = "timed_out"
)

type WorkflowSingleRunScheme struct {
	Id         int    `json:"id"`
	JobsURL    string `json:"jobs_url"`
	Status     string `json:"status"`
	Conclusion string `json:"conclusion"`
}

type WorkflowJobsScheme struct {
	Jobs []WorkflowSingleJobScheme `json:"jobs"`
}

type WorkflowSingleJobScheme struct {
	Name       string                     `json:"name"`
	Steps      []WorkflowSingleStepScheme `json:"steps"`
	Status     string                     `json:"status"`
	Conclusion string                     `json:"conclusion"`
}

type WorkflowSingleStepScheme struct {
	Name string `json:"name"`
}

// TODO how to implement test for nested http requests locally?
// Maybe an end-to-end test with a mock server?
func GetWorkflowRunID(externalRefID string) (int, error) {
	// Get the current time in UTC and subtract the deltaTime
	timeWindow := time.Now().UTC().Add(-getWorkflowRunTimeWindow).Format("2006-01-02T15:04")
	timeWindowFilter := "?created=%3E" + timeWindow

	s := spinner.New(spinner.CharSets[9], spinnerRate)
	for numTries := 1; numTries < getWorkflowRunIdMaxTry+1; numTries++ {
		responseBody := SendRequest(http.MethodGet, workflowRunsURL+timeWindowFilter, nil, http.StatusOK)

		// logger.Debugf("Workflow run response: %s", string(responseBody))
		var workflowRuns WorkflowRunsScheme
		err := json.Unmarshal(responseBody, &workflowRuns)
		if err != nil {
			logger.Panicf("Unable to unmarshal json: %v", err)
		}

		for _, workFlowSingleRun := range workflowRuns.WorkflowRuns {
			jobsURL := workFlowSingleRun.JobsURL
			responseBody := SendRequest(http.MethodGet, jobsURL, nil, http.StatusOK)

			// logger.Debugf("Workflow jobs response: %s", string(responseBody))
			var workflowJobs WorkflowJobsScheme
			err = json.Unmarshal(responseBody, &workflowJobs)
			if err != nil {
				logger.Panicf("Unable to unmarshal json: %v", err)
			}

			for _, job := range workflowJobs.Jobs {
				if job.Name == "Prepare build" {
					for _, step := range job.Steps {
						logger.Debugf("Step name: %s", step.Name)
						if step.Name == externalRefID {
							s.Stop()
							return workFlowSingleRun.Id, nil
						}
					}
				}
			}
		}
		s.Prefix = fmt.Sprintf("Waiting for task %s to show up (retry %d/%d) ",
			externalRefID, numTries, getWorkflowRunIdMaxTry)
		s.Start()
		time.Sleep(pollingInterval)
		logger.Debugf("Retrying getting workflow run ID for %s (%d/%d)\n",
			externalRefID, numTries, getWorkflowRunIdMaxTry)
	}

	return -1, fmt.Errorf("get workflow run ID failed after max tryouts")
}

// Split out the response handling for testing
func GetWorkflowRunStatusFromResp(responseBody []byte) (string, string) {
	var workflowSingleRun WorkflowSingleRunScheme
	err := json.Unmarshal(responseBody, &workflowSingleRun)
	if err != nil {
		logger.Panicf("Unable to unmarshal json: %v", err)
	}

	return workflowSingleRun.Status, workflowSingleRun.Conclusion
}

// Gets the status and conclusion of a workflow run
func GetWorkflowRunStatus(runId int) (string, string) {
	responseBody := SendRequest(http.MethodGet, workflowSingleRunURL+fmt.Sprint(runId), nil, http.StatusOK)
	return GetWorkflowRunStatusFromResp(responseBody)
}

// Split out the response handling for testing
func GetWorkflowJobsProgressFromResp(responseBody []byte) (int, int, string) {
	var workflowJobs WorkflowJobsScheme
	err := json.Unmarshal(responseBody, &workflowJobs)
	if err != nil {
		logger.Panicf("Unable to unmarshal json: %v", err)
	}

	numJobs := len(workflowJobs.Jobs)
	iInProgress := 0
	for i, job := range workflowJobs.Jobs[iInProgress:] {
		if job.Status == StatusInProgress || job.Status == StatusQueued {
			iInProgress += i
			return iInProgress + 1, numJobs, job.Name
		} else if job.Status == StatusCompleted && i+iInProgress == numJobs-1 {
			// All finished
			return numJobs, numJobs, ""
		}
	}
	return -1, -1, ""
}

// Gets the progress of a workflow run
func GetWorkflowJobsProgress(runId int) (int, int, string) {
	jobsURL := workflowSingleRunURL + fmt.Sprint(runId) + "/jobs"
	responseBody := SendRequest(http.MethodGet, jobsURL, nil, http.StatusOK)
	return GetWorkflowJobsProgressFromResp(responseBody)
}

// TODO how to implement test for calls into GetWorkflowRunID?
func WorkflowPolling(workflowExtRefId string) {
	runId, _ := GetWorkflowRunID(workflowExtRefId)
	logger.Debugf("%d\n", runId)

	fmt.Printf("Task %s started. Details available at %s%d.\n", workflowExtRefId,
		workflowSingleRunWebURL, runId)

	s := spinner.New(spinner.CharSets[9], spinnerRate)
	for {
		status, conclusion := GetWorkflowRunStatus(runId)
		if status == StatusCompleted {
			s.Stop()
			fmt.Printf("Task %s finished with status %s\n", workflowExtRefId, conclusion)
			break
		} else {
			currJob, totalJobs, jobName := GetWorkflowJobsProgress(runId)
			s.Prefix = fmt.Sprintf("Task %s is currently %s: %s (%d/%d) ",
				workflowExtRefId, strings.ReplaceAll(status, "_", " "),
				strings.Split(jobName, " (")[0], currJob, totalJobs)
			s.Start()
			time.Sleep(pollingInterval)
		}
	}
}
