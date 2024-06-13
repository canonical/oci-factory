package token_test

import (
	"os"
	"testing"

	"github.com/canonical/oci-factory/cli-client/internals/token"
)

func TestReadAccessTokenEnv(t *testing.T) {
	expectedToken := "ghp_test123ToKeN"
	saveToken := token.UpdateEnvToken(expectedToken)
	err := os.Setenv(token.TokenVarName, expectedToken)
	if err != nil {
		t.Fatalf("Unable to set env variable: %v", err)
	}
	resultToken := token.GetAccessToken()
	if resultToken != expectedToken {
		t.Fatalf("")
	}
	token.RestoreTokenEnv(saveToken)
	if os.Getenv(token.TokenVarName) != saveToken {
		t.Fatalf("Unable to restore saved env variable")
	}
}
