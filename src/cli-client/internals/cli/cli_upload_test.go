package cli_test

import (
	. "gopkg.in/check.v1"

	"github.com/canonical/oci-factory/cli-client/internals/cli"
)

// `func Test(t *testing.T) { TestingT(t) }` defined in validator_test.go

type CmdUploadSuite struct{}

var _ = Suite(&CmdUploadSuite{})

func (s *CmdUploadSuite) TestParseUploadReleases(c *C) {
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
			"risks=high,eol=2023-01-02,track=1.0.0",
			[]cli.UploadRelease{
				{
					Track:     "1.0.0",
					Risks:     []string{"high"},
					EndOfLife: "2023-01-02T00:00:00Z",
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
			"invalid argument: track=1.0.0,risks=high,low",
			true,
		},
		{ // TODO this should fail when proper regex is implemented
			"track=1.0.0,risks=high,low,eol=2023-01-03,extra=field",
			// TODO change to empty cli.UploadRelease
			[]cli.UploadRelease{
				{
					Track:     "1.0.0",
					Risks:     []string{"high", "low"},
					EndOfLife: "2023-01-03T00:00:00Z",
				},
			},
			"invalid key: extra",
			// TODO change to true
			false,
		},
		{
			"noname=1.0.0,risks=high,low,eol=2023-01-04",
			[]cli.UploadRelease{
				{},
			},
			"invalid argument: noname=1.0.0,risks=high,low,eol=2023-01-04",
			true,
		},
		{
			"track==1.0.0,risks=high,low,eol=2023-01-05,",
			[]cli.UploadRelease{
				{},
			},
			"invalid key-value pair: track==1.0.0",
			true,
		},
	} {
		releases, err := cli.ParseUploadReleases([]string{test.in})
		if test.err {
			c.Assert(err, ErrorMatches, test.errMsg)
			continue
		}
		c.Assert(err, IsNil)
		c.Assert(releases, DeepEquals, test.out)
	}
}
