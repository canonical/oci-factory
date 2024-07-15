package cli

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/canonical/go-flags"
)

type CmdRelease struct {
	Revision int `long:"revision" description:"The revision number of the image release"`
}

const longDescription = `
The OCI Factory CLI client is a tool that builds, tests, and releases the OCI
images owned by Canonical using the Github workflow in the OCI Factory repository.
`

var opts struct {
	// TODO: Leave `release` here for now. Should be moved into a `cmd_release.go` in phase 2.
	// CmdRelease       CmdRelease `command:"release" description:"Release (re-tag) the image into the container registries"`
	SkipConfirmation bool `short:"y" description:"Skip the confirmation to upload/release an image"`
}

var parser = flags.NewParser(&opts, flags.Default)

func CliMain() error {
	addHelp(parser)
	if len(os.Args) == 1 {
		parser.WriteHelp(os.Stdout)
		os.Exit(0)
	}
	if _, err := parser.Parse(); err != nil {
		switch flagsErr := err.(type) {
		case flags.ErrorType:
			if flagsErr == flags.ErrHelp {
				os.Exit(0)
			}
			os.Exit(1)
		default:
			os.Exit(1)
		}
	}
	return nil
}

func addHelp(p *flags.Parser) {
	p.ShortDescription = "CLI client to build, test and release OCI images"
	p.LongDescription = longDescription
}

func blockForConfirm(s string) error {
	// check if is a tty
	fi, err := os.Stdin.Stat()
	if err != nil || fi.Mode()&os.ModeNamedPipe == 0 {
		return fmt.Errorf("non-interactive terminal detected, run with -y option")
	} else if err != nil {
		return err
	}

	r := bufio.NewReader(os.Stdin)
	fmt.Printf("%s [y/N]: ", s)
	res, err := r.ReadString('\n')
	if err == io.ErrUnexpectedEOF || err == io.EOF {
		return fmt.Errorf("cancelled")
	} else if err != nil {
		return err
	}

	res = strings.ToLower(strings.TrimSpace(res))

	if res != "y" && res != "yes" {
		return fmt.Errorf("cancelled")
	}
	return nil
}
