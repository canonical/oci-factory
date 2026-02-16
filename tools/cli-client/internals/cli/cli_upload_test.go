package cli_test

import (
	. "gopkg.in/check.v1"

	"github.com/canonical/oci-factory/tools/cli-client/internals/cli"
)

// `func Test(t *testing.T) { TestingT(t) }` defined in validator_test.go

type CmdUploadSuite struct{}

var _ = Suite(&CmdUploadSuite{})

func (s *CmdUploadSuite) TestParseUploadReleases(c *C) {
	for _, test := range []struct {
		in     []string
		out    []cli.UploadRelease
		errMsg string
		err    bool
	}{
		{
			[]string{"track=1.0.0,risks=beta,stable,eol=2023-01-01"},
			[]cli.UploadRelease{
				{
					Track:     "1.0.0",
					Risks:     []string{"beta", "stable"},
					EndOfLife: "2023-01-01T00:00:00Z",
				},
			},
			"",
			false,
		},
		{
			[]string{"risks=high,eol=2023-01-02,track=1.0.0"},
			[]cli.UploadRelease{
				{},
			},
			"invalid risk value: high",
			true,
		},
		{
			[]string{"track=some-track_22.04"},
			[]cli.UploadRelease{
				{},
			},
			"missing fields: risks, eol",
			true,
		},
		{ // TODO this should fail when proper regex is implemented
			[]string{"track=1.0.0,risks=stable,candidate,eol=2023-01-03,extra=field"},
			// TODO change to empty cli.UploadRelease
			[]cli.UploadRelease{
				{
					Track:     "1.0.0",
					Risks:     []string{"stable", "candidate"},
					EndOfLife: "2023-01-03T00:00:00Z",
				},
			},
			"invalid key-value pair: extra=field",
			// TODO change to true
			true,
		},
		{
			[]string{"noname=1.0.0,risks=high,low,eol=2023-01-04"},
			[]cli.UploadRelease{
				{},
			},
			"invalid key-value pair: noname=1.0.0",
			true,
		},
		{
			[]string{"track==1.0.0,risks=beta,eol=2023-01-05"},
			[]cli.UploadRelease{
				{},
			},
			"invalid track value: ",
			true,
		},
		{
			[]string{"track=1.0.0,risks=beta,eol=,2023-01-05"},
			[]cli.UploadRelease{
				{},
			},
			"invalid eol value: ,2023-01-05",
			true,
		},
		{
			[]string{"track=1.0.0,risks=stable,eol=2023-01-06,,,"},
			[]cli.UploadRelease{
				{
					Track:     "1.0.0",
					Risks:     []string{"stable"},
					EndOfLife: "2023-01-06T00:00:00Z",
				},
			},
			"",
			false,
		},
		{
			[]string{"track=aaa23345,,,,,,risks=edge,,,,,eol=2023-01-07,,,,,,"},
			[]cli.UploadRelease{
				{
					Track:     "aaa23345",
					Risks:     []string{"edge"},
					EndOfLife: "2023-01-07T00:00:00Z",
				},
			},
			"",
			false,
		},
		{
			[]string{"track=1.0.0,risks=stable,eol=2023-01-08",
				"track=1.0.1,risks=stable,eol=2023-01-09"},
			[]cli.UploadRelease{
				{
					Track:     "1.0.0",
					Risks:     []string{"stable"},
					EndOfLife: "2023-01-08T00:00:00Z",
				},
				{
					Track:     "1.0.1",
					Risks:     []string{"stable"},
					EndOfLife: "2023-01-09T00:00:00Z",
				},
			},
			"",
			false,
		},
		{
			[]string{"track=1.0.0,risks=stable,eol=2023-01-10,track=2.0.0"},
			[]cli.UploadRelease{
				{},
			},
			"duplicated value for track",
			true,
		},
		{
			[]string{"track=1.0.0,risks=stable,eol=2023-01-10,risks=candidate"},
			[]cli.UploadRelease{
				{},
			},
			"duplicated value for risks",
			true,
		},
		{
			[]string{"eol=2024-05-31,track=1.0.0,risks=stable,eol=2023-01-10"},
			[]cli.UploadRelease{
				{},
			},
			"duplicated value for eol",
			true,
		},
		{
			[]string{"track=1.0.0,eol=2024-05-31,risks=stable,eol=2023-01-10,track=2.0.0"},
			[]cli.UploadRelease{
				{},
			},
			"duplicated value for eol",
			true,
		},
	} {
		releases, err := cli.ParseUploadReleases(test.in)
		if test.err {
			c.Assert(err, ErrorMatches, test.errMsg)
			continue
		}
		c.Assert(err, IsNil)
		c.Assert(releases, DeepEquals, test.out)
	}
}

func (s *CmdUploadSuite) TestParseIgnoredVulnerabilities(c *C) {
	for _, test := range []struct {
		in  string
		out []string
	}{
		{"FINDING-1", []string{"FINDING-1"}},
		{",,FINDING-1", []string{"FINDING-1"}},
		{"FINDING-1,FINDING-2", []string{"FINDING-1", "FINDING-2"}},
		{"FINDING-1,FINDING-2,,", []string{"FINDING-1", "FINDING-2"}},
		{"", []string{}},
		{",,,", []string{}},
	} {
		out := cli.ParseIgnoredVulnerabilities(test.in)
		c.Assert(out, DeepEquals, test.out)
	}
}
