package main

import (
	"fmt"
	"os"

	"github.com/canonical/oci-factory/cli-client/internals/cli"
	"github.com/canonical/oci-factory/cli-client/internals/logger"
)

func main() {
	logger.SetLogger(logger.New(os.Stderr, fmt.Sprintf("[%s] ", "oci-factory")))
	cli.CliMain()
}
