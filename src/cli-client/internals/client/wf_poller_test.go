package client_test

import (
	. "gopkg.in/check.v1"

	"github.com/canonical/oci-factory/src/cli-client/internals/client"
)

type PollerSuite struct{}

// `func Test(t *testing.T) { TestingT(t) }` defined in client_test.go

var _ = Suite(&PollerSuite{})

func (s *PollerSuite) TestGetWorkflowRunStatusFromResp(c *C) {
	mockResponseBody := []byte(`{"status":"completed","conclusion":"success"}`)
	expectedStatus := "completed"
	expectedConclusion := "success"

	status, conclusion := client.GetWorkflowRunStatusFromResp(mockResponseBody)

	// Verify the response
	c.Assert(status, Equals, expectedStatus)
	c.Assert(conclusion, Equals, expectedConclusion)
}

func (s *PollerSuite) TestGetWorkflowJobsProgressFromResp(c *C) {
	mockResponseBody := []byte(`{"jobs":[{"name":"Job 1","status":"completed"},{"name":"Job 2","status":"in_progress"},{"name":"Job 3","status":"queued"}]}`)
	expectedCurrJob := 2
	expectedTotalJobs := 3
	expectedJobName := "Job 2"

	currJob, totalJobs, jobName := client.GetWorkflowJobsProgressFromResp(mockResponseBody)

	// Verify the response
	c.Assert(currJob, Equals, expectedCurrJob)
	c.Assert(totalJobs, Equals, expectedTotalJobs)
	c.Assert(jobName, Equals, expectedJobName)
}
