package cli

import (
	"bufio"
	"fmt"
	"os"
	"strings"

	"github.com/canonical/go-flags"
	"github.com/canonical/oci-factory/cli-client/internals/logger"
)

// Example: oci-factory upload -y --release tracks=1.0-22.04,risks=edge,eol=2025-06-01

type CmdRelease struct {
	Revision int `long:"revision" description:"The integer-typed revision number of the image release"`
}

var opts struct {
	// Leave `release` here for now. Should be moved into a `cmd_release.go` in phase 2.
	CmdRelease CmdRelease `command:"release" description:"Release (re-tag) the image into the container registries"`
	Confirm    bool       `short:"y" description:"Confirm the upload/release action by default"`
}

var parser = flags.NewParser(&opts, flags.Default)

func CliMain() {
	if len(os.Args) == 1 || os.Args[1] == "help" {
		parser.WriteHelp(os.Stdout)
		os.Exit(0)
	}
	parser.Parse()
}

func blockForConfirm(s string, tries int) {
	r := bufio.NewReader(os.Stdin)

	for ; tries > 0; tries-- {
		fmt.Printf("%s [Y/n]: ", s)

		res, err := r.ReadString('\n')
		if err != nil {
			logger.Panicf("%v", err)
		}

		res = strings.TrimSpace(res)

		if res == "y" || res == "yes" || res == "" {
			return
		} else if res == "n" || res == "no" {
			fmt.Println("Cancelled")
			os.Exit(0)
		} else {
			continue
		}
	}
}
