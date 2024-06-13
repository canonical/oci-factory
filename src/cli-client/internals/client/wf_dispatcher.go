package client

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/canonical/oci-factory/cli-client/internals/logger"
	"github.com/canonical/oci-factory/cli-client/internals/token"
)

const workflowDispatchURL = "https://api.github.com/repos/canonical/oci-factory/actions/workflows/Image.yaml/dispatches"

type Inputs struct {
	OciImageName    string `json:"oci-image-name"`
	B64ImageTrigger string `json:"b64-image-trigger"`
	Upload          bool   `json:"upload"`
	ExternalRefID   string `json:"external_ref_id"`
}

type Payload struct {
	Ref    string `json:"ref"`
	Inputs Inputs `json:"inputs"`
}

func NewGithubAuthHeaderMap() map[string]string {
	accessToken := token.GetAccessToken()
	return map[string]string{
		"Accept":               "application/vnd.github+json",
		"Authorization":        fmt.Sprintf("Bearer %s", accessToken),
		"X-GitHub-Api-Version": "2022-11-28",
	}
}

func SetHeaderWithMap(request *http.Request, headerMap map[string]string) {
	for key, value := range headerMap {
		request.Header.Set(key, value)
	}
}

// Don't forget to keep the ExternalRefID to track the workflow
func NewPayload(imageName string, uberImageTrigger string) Payload {
	uberImageTriggerB64 := base64.StdEncoding.EncodeToString([]byte(uberImageTrigger))
	payload := Payload{
		Ref: "main",
		Inputs: Inputs{
			OciImageName:    imageName,
			B64ImageTrigger: uberImageTriggerB64,
			Upload:          true,
			ExternalRefID:   fmt.Sprintf("cli-client-%s-%d", imageName, time.Now().Unix()),
		},
	}
	return payload
}

// Split the impl with different URL for testing
func DispatchWorkflowImpl_(payload Payload, url string) {
	payloadJSON, err := json.Marshal(payload)
	if err != nil {
		logger.Panicf("Unable to marshall payload: %s", err)
	}

	SendRequest(http.MethodPost, url, payloadJSON, http.StatusNoContent)
}

// Dispatch GitHub workflow with http request
func DispatchWorkflow(payload Payload) {
	DispatchWorkflowImpl_(payload, workflowDispatchURL)
}
