package client_test

import (
	"testing"

	"github.com/canonical/oci-factory/cli-client/internals/client"
)

func TestGetWorkflowRunStatusFromResp(t *testing.T) {
	mockResponseBody := []byte(`{"status":"completed","conclusion":"success"}`)
	expectedStatus := "completed"
	expectedConclusion := "success"

	status, conclusion := client.GetWorkflowRunStatusFromResp(mockResponseBody)

	// Verify the response
	if status != expectedStatus {
		t.Errorf("unexpected status, want %s, got %s", expectedStatus, status)
	}
	if conclusion != expectedConclusion {
		t.Errorf("unexpected conclusion, want %s, got %s", expectedConclusion, conclusion)
	}
}

func TestGetWorkflowJobsProgressFromResp(t *testing.T) {
	mockResponseBody := []byte(`{"jobs":[{"name":"Job 1","status":"completed"},{"name":"Job 2","status":"in_progress"},{"name":"Job 3","status":"queued"}]}`)
	expectedCurrJob := 2
	expectedTotalJobs := 3
	expectedJobName := "Job 2"

	currJob, totalJobs, jobName := client.GetWorkflowJobsProgressFromResp(mockResponseBody)

	// Verify the response
	if currJob != expectedCurrJob {
		t.Errorf("unexpected current job, want %d, got %d", expectedCurrJob, currJob)
	}
	if totalJobs != expectedTotalJobs {
		t.Errorf("unexpected total jobs, want %d, got %d", expectedTotalJobs, totalJobs)
	}
	if jobName != expectedJobName {
		t.Errorf("unexpected job name, want %s, got %s", expectedJobName, jobName)
	}
}
