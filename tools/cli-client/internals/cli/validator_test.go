package cli_test

import (
	"testing"

	. "gopkg.in/check.v1"

	"github.com/canonical/oci-factory/src/cli-client/internals/cli"
)

func Test(t *testing.T) { TestingT(t) }

type ValidatorSuite struct{}

func (vs *ValidatorSuite) TestValidateAndFormatDateInput(c *C) {
	for _, date := range []struct {
		in  string
		err bool
	}{
		{"2006-07-08", false},
		{"2008-09-10", false},
		{"2024-05-01", false},
		{"2001-02-29", true},
		{"2024-05-32", true},
		{"01-01-2023", true},
	} {
		_, err := cli.ValidateAndFormatDate(date.in)
		if date.err {
			c.Assert(err, Equals, date.err)
			break
		}
		c.Assert(err, IsNil)
	}
}
