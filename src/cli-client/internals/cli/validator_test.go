package cli_test

import (
	"testing"

	"github.com/canonical/oci-factory/cli-client/internals/cli"
)

func TestValidateAndFormatDateLegalInput(t *testing.T) {
	inputs := []string{"2006-07-08", "2008-09-10", "2024-05-01"}

	for _, datetime := range inputs {
		_, err := cli.ValidateAndFormatDate(datetime)
		if err != nil {
			t.Fatalf("Failed parsing legal time format yyyy-mm-dd, %v", err)
		}
	}
}

func TestValidateAndFormatDateBadInput(t *testing.T) {
	inputs := []string{"2001-02-29", "2024-05-32", "01-01-2023"}

	for _, datetime := range inputs {
		_, err := cli.ValidateAndFormatDate(datetime)
		if err == nil {
			t.Fatalf("Parsing illegal date input [%s] didn't raise error", datetime)
		}
	}
}
