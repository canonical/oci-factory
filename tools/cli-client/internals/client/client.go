package client

import (
	"bytes"
	"io"
	"net/http"
	"os"
	"time"

	"github.com/canonical/oci-factory/tools/cli-client/internals/logger"
)

const NumRetries = 2
const RetryInterval = 5 * time.Second

func SendRequest(requestType, url string, payload []byte, expectedStatusCode int) []byte {
	client := &http.Client{}

	req, err := http.NewRequest(requestType, url, bytes.NewBuffer(payload))
	if err != nil {
		logger.Panicf("failed to create request: %v", err)
	}
	header := NewGithubAuthHeaderMap()
	SetHeaderWithMap(req, header)

	// Send the request, and retries if the response returns 503
	var respBody []byte
	for i := 0; i < NumRetries; i++ {
		resp, err := client.Do(req)
		if err != nil {
			logger.Panicf("failed to send request: %v", err)
		}
		defer resp.Body.Close()

		respBody, err = io.ReadAll(resp.Body)
		if err != nil {
			logger.Panicf("failed to read response body: %v", err)
		}

		if resp.StatusCode == expectedStatusCode {
			break
		}

		if resp.StatusCode == 503 {
			logger.Noticef("Request failed: %s", resp.Status)
			logger.Noticef("Retrying request %d/%d", i+1, NumRetries)
			time.Sleep(RetryInterval)
			continue
		}

		if resp.StatusCode == 401 {
			logger.Noticef("Request failed: %s", resp.Status)
			logger.Noticef("Please check if your Github token is correct")
			os.Exit(1)
		}

		logger.Noticef("Request failed: %s", resp.Status)
		logger.Panicf("Response: %s", respBody)
	}

	return respBody
}
