package cli_test

import (
	"fmt"
	"reflect"
	"testing"

	"github.com/canonical/oci-factory/cli-client/internals/cli"
)

func TestParseUploadReleases(t *testing.T) {
	for _, test := range []struct {
		in     string
		out    []cli.UploadRelease
		errMsg string
		err    bool
	}{
		{
			"track=1.0.0,risks=high,low,eol=2023-01-01",
			[]cli.UploadRelease{
				{
					Track:     "1.0.0",
					Risks:     []string{"high", "low"},
					EndOfLife: "2023-01-01T00:00:00Z",
				},
			},
			"",
			false,
		},
		{
			"risks=high,eol=2023-01-01,track=1.0.0",
			[]cli.UploadRelease{
				{
					Track:     "1.0.0",
					Risks:     []string{"high"},
					EndOfLife: "2023-01-01T00:00:00Z",
				},
			},
			"",
			false,
		},
		{
			"track=1.0.0,risks=high,low",
			[]cli.UploadRelease{
				{},
			},
			"missing required fields in argument: track=1.0.0,risks=high,low",
			true,
		},
		{
			"track=1.0.0,risks=high,low,eol=2023-01-01,extra=field",
			[]cli.UploadRelease{
				{},
			},
			"invalid key: extra",
			true,
		},
		{
			"track=1.0.0,risks=high,low,eol=2023-01-01,",
			[]cli.UploadRelease{
				{},
			},
			"invalid key-value pair: ",
			true,
		},
	} {
		releases, err := cli.ParseUploadReleases([]string{test.in})
		if test.err {
			if fmt.Sprint(err) == test.errMsg {
				t.Fatalf("assertion failed: expected: %s, actual: %v", test.errMsg, err)
			}
			continue
		}
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if !reflect.DeepEqual(test.out, releases) {
			t.Fatalf("assertion failed: expected: %v, actual: %v", test.out, releases)
		}
	}
}
