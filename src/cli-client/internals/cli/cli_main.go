package cli

import (
	"encoding/json"

	"github.com/canonical/oci-factory/cli-client/internals/client"
	"github.com/canonical/oci-factory/cli-client/internals/logger"
	"github.com/canonical/oci-factory/cli-client/internals/trigger"
)

func CliMain() {
	buildMetadata := trigger.InferBuildMetadata()
	risks := [2]string{"stable", "candidate"}
	uploadTrack := trigger.NewUploadReleaseTrack("11.0.0-22.04", risks[:], "2025-05-28T00:00:00Z")
	uploadTrack.AddTrack("10.3.4-22.04", []string{"beta", "edge"}, "2025-05-28T00:00:00Z")
	imageTrigger := trigger.NewUploadImageTrigger(buildMetadata, uploadTrack)
	uploadTrigger := trigger.NewUploadTrigger([]trigger.UploadImageTrigger{imageTrigger})
	logger.Debugf("Trigger:\n%s", uploadTrigger.ToYamlString())

	payload := client.NewPayload("python3.8", uploadTrigger.ToYamlString())
	payloadJson, _ := json.Marshal(payload)
	logger.Debugf("\n%s\n", string(payloadJson))

	workflowExtRefId := "workflow-engine-python-1717508367"
	client.WorkflowPolling(workflowExtRefId)
}
