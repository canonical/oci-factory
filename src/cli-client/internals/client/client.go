package client

import (
	"bytes"
	"io"
	"net/http"

	"github.com/canonical/oci-factory/cli-client/internals/logger"
)

func SendRequest(requestType, url string, payload []byte, expectedStatusCode int) []byte {
	client := &http.Client{}

	req, err := http.NewRequest(requestType, url, bytes.NewBuffer(payload))
	if err != nil {
		logger.Panicf("failed to create request: %v", err)
	}
	header := NewGithubAuthHeaderMap()
	SetHeaderWithMap(req, header)

	resp, err := client.Do(req)
	if err != nil {
		logger.Panicf("failed to send request: %v", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		logger.Panicf("failed to read response body: %v", err)
	}

	if resp.StatusCode != expectedStatusCode {
		logger.Noticef("Request failed: %s", resp.Status)
		logger.Panicf("Response: %s", respBody)
	}

	return respBody
}
