package client

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/canonical/oci-factory/cli-client/internals/logger"
)

const workflowDispatchUrl = "https://api.github.com/repos/canonical/oci-factory/actions/workflows/Image.yaml/dispatches"

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

func NewPayload(imageName string, uberImageTrigger string) Payload {
	payload := Payload{
		Ref: "main",
		Inputs: Inputs{
			OciImageName:    imageName,
			B64ImageTrigger: uberImageTrigger,
			Upload:          true,
			ExternalRefID:   fmt.Sprintf("workflow-engine-%s-%d", imageName, time.Now().Unix()),
		},
	}
	return payload
}

// Dispatch GitHub workflow with http request
func DispatchWorkflow(payload Payload, accessToken string) {
	payloadJSON, err := json.Marshal(payload)
	if err != nil {
		logger.Panicf("Unable to marshall payload: %s", err)
	}

	request, err := http.NewRequest("POST", workflowDispatchUrl, bytes.NewBuffer(payloadJSON))
	if err != nil {
		logger.Panicf("Unable to create request: %v", err)
	}
	request.Header.Set("Accept", "application/vnd.github+json")
	request.Header.Set("Authorization", fmt.Sprintf("Bearer %s", accessToken))
	request.Header.Set("X-GitHub-Api-Version", "2022-11-28")

	client := &http.Client{}
	response, err := client.Do(request)
	if err != nil {
		logger.Panicf("Unable to send request: %v", err)
	}
	defer response.Body.Close()

	if response.StatusCode != 200 {
		logger.Noticef("Request failed: %s", response.Status)
		responseBody, err := io.ReadAll(response.Body)
		if err != nil {
			logger.Panicf("Unable to read response body: %v", err)
		}
		logger.Panicf("Response: %s", string(responseBody))
	}
}
