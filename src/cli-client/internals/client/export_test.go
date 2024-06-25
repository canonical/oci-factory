package client

var (
	GetWorkflowRunID                = getWorkflowRunID
	GetWorkflowRunStatusFromResp    = getWorkflowRunStatusFromResp
	GetWorkflowJobsProgressFromResp = getWorkflowJobsProgressFromResp
)

func SetWorkflowDispatchURL(url string) string {
	ret := workflowDispatchURL
	workflowDispatchURL = url
	return ret
}
