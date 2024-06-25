package cli

import (
	"bufio"
	"fmt"
	"io"
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
	CmdRelease       CmdRelease `command:"release" description:"Release (re-tag) the image into the container registries"`
	SkipConfirmation bool       `short:"y" description:"Skip the confirmation to upload/release an image"`
}

var parser = flags.NewParser(&opts, flags.Default)

func CliMain() {
	if len(os.Args) == 1 || os.Args[1] == "help" {
		parser.WriteHelp(os.Stdout)
		os.Exit(0)
	}
	parser.Parse()
}

func blockForConfirm(s string) {
	// check if is a tty
	fi, err := os.Stdin.Stat()
	if err != nil || fi.Mode()&os.ModeNamedPipe == 0 {
		fmt.Fprintln(os.Stderr, "Non-interactive terminal detected. Must run with -y option.")
	}

	r := bufio.NewReader(os.Stdin)
	fmt.Printf("%s [y/N]: ", s)
	res, err := r.ReadString('\n')
	if err == io.ErrUnexpectedEOF || err == io.EOF {
		fmt.Println("Cancelled")
		os.Exit(1)
	} else if err != nil {
		logger.Panicf("failed to read from stdin: %v", err)
	}

	res = strings.ToLower(strings.TrimSpace(res))

	if res == "y" || res == "yes" {
		return
	} else if res == "n" || res == "no" || res == "" {
		fmt.Println("Cancelled")
		os.Exit(1)
	}
}
