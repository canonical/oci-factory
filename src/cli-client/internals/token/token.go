package token

import (
	"fmt"
	"os"

	"github.com/canonical/oci-factory/cli-client/internals/logger"
	"golang.org/x/term"
)

const TokenVarName = "GITHUB_TOKEN"

var _accessToken = ""

func readAccessToken() string {
	envAccessToken := os.Getenv(TokenVarName)
	if len(envAccessToken) == 0 {
		fmt.Print("GitHub personal access token: ")
		accessTokenBytes, err := term.ReadPassword(0)
		if err != nil {
			logger.Panicf("Error handling token: %v", err)
		}
		// Put new logs into the new line
		fmt.Println()
		return string(accessTokenBytes)
	} else {
		fmt.Println("Using environment variable GITHUB_TOKEN")
		return envAccessToken
	}
}

func GetAccessToken() string {
	if len(_accessToken) == 0 {
		_accessToken = readAccessToken()
	}
	return _accessToken
}

func SetEnvToken(token string) (restore func()) {
	saveToken := os.Getenv(TokenVarName)
	os.Setenv(TokenVarName, token)
	return func() {
		if len(saveToken) == 0 {
			os.Unsetenv(TokenVarName)
		} else {
			os.Setenv(TokenVarName, saveToken)
		}
	}
}
