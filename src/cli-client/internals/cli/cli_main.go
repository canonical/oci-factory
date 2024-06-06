package cli

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/briandowns/spinner"
	"github.com/canonical/oci-factory/cli-client/internals/client"
	"github.com/canonical/oci-factory/cli-client/internals/logger"
	"github.com/canonical/oci-factory/cli-client/internals/trigger"
	"golang.org/x/term"
)

func workflowPolling(workflowExtRefId string, accessToken string) {
	runId, _ := client.GetWorkflowRunID(workflowExtRefId, accessToken)
	logger.Noticef("%d\n", runId)

	fmt.Printf("Task %s started. Details available at %s%d.\n", workflowExtRefId,
		"https://github.com/canonical/oci-factory/actions/runs/", runId)

	s := spinner.New(spinner.CharSets[9], 500*time.Millisecond)
	count := 0
	for {
		status, conclusion := client.GetWorkflowRunStatus(runId, accessToken)
		// test
		if count < 2 {
			status = client.StatusQueued
		} else if count < 4 {
			status = client.StatusInProgress
		}
		count += 1
		if status == client.StatusCompleted {
			s.Stop()
			fmt.Printf("\rTask %s finished with status %s\n", workflowExtRefId, conclusion)
			break
		} else {
			s.Prefix = fmt.Sprintf("\rTask %s is currently %s ",
				workflowExtRefId, strings.ReplaceAll(status, "_", " "))
			s.Start()
			time.Sleep(5 * time.Second)
		}
	}
}

func CliMain() {
	buildMetadata := trigger.InferBuildMetadata()
	risks := [2]string{"stable", "candidate"}
	uploadTrack := trigger.NewUploadReleaseTrack("11.0.0-22.04", risks[:], "2025-05-28T00:00:00Z")
	uploadTrack.AddTrack("10.3.4-22.04", []string{"beta", "edge"}, "2025-05-28T00:00:00Z")
	imageTrigger := trigger.NewUploadImageTrigger(buildMetadata, uploadTrack)
	uploadTrigger := trigger.NewUploadTrigger([]trigger.UploadImageTrigger{imageTrigger})
	logger.Noticef("Trigger:\n%s", uploadTrigger.ToYamlString())

	payload := client.NewPayload("python3.8", uploadTrigger.ToYamlString())
	payloadJson, _ := json.Marshal(payload)
	logger.Debugf("\n%s\n", string(payloadJson))

	accessToken := os.Getenv("GITHUB_TOKEN")
	if len(accessToken) == 0 {
		fmt.Print("GitHub personal access token: ")
		accessTokenBytes, err := term.ReadPassword(0)
		if err != nil {
			logger.Panicf("Error handling token: %v", err)
		}
		// Put new logs into the new line
		fmt.Println()
		accessToken = string(accessTokenBytes)
	}

	workflowExtRefId := "workflow-engine-python-1717508367"
	workflowPolling(workflowExtRefId, accessToken)
}
