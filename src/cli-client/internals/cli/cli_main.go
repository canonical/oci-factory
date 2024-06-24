package cli

import (
	"bufio"
	"fmt"
	"os"
	"strings"

	"github.com/canonical/go-flags"
	"github.com/canonical/oci-factory/cli-client/internals/logger"
)

type CmdRelease struct {
	Revision int `long:"revision" description:"The revision number of the image release"`
}

var opts struct {
	// TODO: Leave `release` here for now. Should be moved into a `cmd_release.go` in phase 2.
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
		fmt.Printf("%s [y/N]: ", s)

		res, err := r.ReadString('\n')
		if err != nil {
			logger.Panicf("%v", err)
		}

		res = strings.TrimSpace(res)

		if res == "y" || res == "yes" {
			return
		} else if res == "n" || res == "no" || res == "" {
			fmt.Println("Cancelled")
			os.Exit(1)
		} else {
			continue
		}
	}
}
