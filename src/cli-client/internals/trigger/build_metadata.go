package trigger

import (
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"strings"

	"github.com/canonical/oci-factory/cli-client/internals/logger"
	git "github.com/go-git/go-git/v5"
	"gopkg.in/yaml.v3"
)

type BuildMetadata struct {
	Source    string
	Commit    string
	Directory string
}

func InferBuildMetadata() BuildMetadata {
	_, err := os.Stat("rockcraft.yaml")
	if os.IsNotExist(err) {
		logger.Panicf("No rockcraft.yaml found in current working directory")
	}
	if err != nil {
		logger.Panicf("OS error: %v", err)
	}
	repo, err := git.PlainOpenWithOptions(".",
		&git.PlainOpenOptions{DetectDotGit: true, EnableDotGitCommonDir: false})
	if err != nil {
		logger.Panicf("Unable to open repository: %v", err)
	}

	// find the source URL
	remotes, err := repo.Remotes()
	if err != nil {
		logger.Panicf("Unable to obtain remotes: %v", err)
	}
	if len(remotes) < 1 || len(remotes[0].Config().URLs) < 1 {
		logger.Panicf("No valid remote exists for this repo")
	}
	remoteURL := remotes[0].Config().URLs[0]
	logger.Debugf("Remote URL: %s", remoteURL)

	// use regex to match the repo location
	regex := regexp.MustCompile("github.com[:/](canonical/.*).git")
	matches := regex.FindStringSubmatch(remoteURL)
	source := matches[1]
	logger.Debugf("Source: %s", source)

	headSha256, err := repo.ResolveRevision("HEAD")
	if err != nil {
		logger.Panicf("Unable to resolve HEAD: %v", err)
	}
	logger.Debugf("HEAD SHA-256: %s", headSha256)

	// find the directory using git rev-parse
	// have to use a subprocess since go-git
	// does not support git rev-parse yet
	prefixBytes, err := exec.Command("git", "rev-parse", "--show-prefix").Output()
	if err != nil {
		logger.Panicf("Subprocess `git rev-parse --show-prefix` failed: %v", err)
	}
	// remote the trailing newline
	prefix := strings.TrimSpace(string(prefixBytes))
	logger.Debugf("Directory: %s", prefix)

	buildMetadata := BuildMetadata{
		Source:    source,
		Commit:    headSha256.String(),
		Directory: prefix,
	}

	return buildMetadata
}

type RockcraftYaml struct {
	Name string `yaml:"name"`
}

func (y *RockcraftYaml) getImageName() string {
	yamlFile, err := os.ReadFile("rockcraft.yaml")
	if err != nil {
		fmt.Errorf("Unable to read rockcraft.yaml in current working directory\n")
	}
	err = yaml.Unmarshal(yamlFile, y)
	if err != nil {
		logger.Panicf("Unable to marshall trigger: %s", err)
	}

	logger.Debugf("Image name: %s", y.Name)
	return y.Name
}

func GetRockcraftImageName() string {
	var y RockcraftYaml
	return y.getImageName()
}
