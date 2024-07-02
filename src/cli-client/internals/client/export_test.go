package client

var (
	GetWorkflowRunID                = getWorkflowRunID
	GetWorkflowRunStatusFromResp    = getWorkflowRunStatusFromResp
	GetWorkflowJobsProgressFromResp = getWorkflowJobsProgressFromResp
)

func SetWorkflowDispatchURL(url string) (restore func()) {
	orig := workflowDispatchURL
	workflowDispatchURL = url
	return func() { workflowDispatchURL = orig }
}
