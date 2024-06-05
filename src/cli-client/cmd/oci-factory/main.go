package main

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/canonical/oci-factory/cli-client/internals/client"
	"github.com/canonical/oci-factory/cli-client/internals/logger"
	"github.com/canonical/oci-factory/cli-client/internals/trigger"
	"golang.org/x/crypto/ssh/terminal"
)

func main() {
	// // We declare a subcommand using the `NewFlagSet`
	// // function, and proceed to define new flags specific
	// // for this subcommand.
	// fooCmd := flag.NewFlagSet("foo", flag.ExitOnError)
	// fooEnable := fooCmd.Bool("--enable", false, "enable")
	// fooName := fooCmd.String("--name", "", "name")

	// // For a different subcommand we can define different
	// // supported flags.
	// barCmd := flag.NewFlagSet("bar", flag.ExitOnError)
	// barLevel := barCmd.Int("level", 0, "level")

	// // The subcommand is expected as the first argument
	// // to the program.
	// if len(os.Args) < 2 {
	// 	fmt.Println("expected 'foo' or 'bar' subcommands")
	// 	os.Exit(1)
	// }

	// // Check which subcommand is invoked.
	// switch os.Args[1] {

	// // For every subcommand, we parse its own flags and
	// // have access to trailing positional arguments.
	// case "foo":
	// 	fooCmd.Parse(os.Args[2:])
	// 	fmt.Println("subcommand 'foo'")
	// 	fmt.Println("  enable:", *fooEnable)
	// 	fmt.Println("  name:", *fooName)
	// 	fmt.Println("  tail:", fooCmd.Args())
	// case "bar":
	// 	barCmd.Parse(os.Args[2:])
	// 	fmt.Println("subcommand 'bar'")
	// 	fmt.Println("  level:", *barLevel)
	// 	fmt.Println("  tail:", barCmd.Args())
	// default:
	// 	fmt.Println("expected 'foo' or 'bar' subcommands")
	// 	os.Exit(1)
	// }

	logger.SetLogger(logger.New(os.Stderr, fmt.Sprintf("[%s] ", "oci-factory")))

	buildMetadata := trigger.InferBuildMetadata()
	risks := [2]string{"stable", "candidate"}
	uploadTrack := trigger.NewUploadReleaseTrack("11.0.0-22.04", risks[:], "2025-05-28T00:00:00Z")
	uploadTrack.AddTrack("10.3.4-22.04", []string{"beta", "edge"}, "2025-05-28T00:00:00Z")
	imageTrigger := trigger.NewUploadImageTrigger(buildMetadata, uploadTrack)
	uploadTrigger := trigger.NewUploadTrigger([]trigger.UploadImageTrigger{imageTrigger})
	logger.Noticef("Trigger:\n%s", uploadTrigger.ToYamlString())

	payload := client.NewPayload("python3.8", uploadTrigger.ToYamlString())
	payloadJson, _ := json.Marshal(payload)
	logger.Noticef("\n%s\n", string(payloadJson))

	logger.Noticef("Getting run ID for workflow workflow-engine-python-1717508367")
	fmt.Print("GitHub personal access token: ")
	accessTokenBytes, err := terminal.ReadPassword(0)
	if err != nil {
		logger.Panicf("Error handling token: %v", err)
	}
	// Put new logs into the new line
	fmt.Println()
	accessToken := string(accessTokenBytes)
	runID, _ := client.GetWorkflowRunID("workflow-engine-python-1717508367", accessToken)
	logger.Noticef("%d\n", runID)

	// client.DispatchWorkflow(payload, "AAAAAAAA")
}
