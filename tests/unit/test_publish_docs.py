"""Exercise publishing control flow without network access or registry writes."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml


SCRIPT = Path(__file__).resolve().parents[2] / "src/docs/publish_docs.sh"
MARKDOWN = '# Example\n\n```sh\ndocker run \\\n    example:8.0_stable "quoted"\n```\n\nUnicode: café\nTab:\tend\n'


@pytest.fixture
def publisher(tmp_path):
    if not shutil.which("jq"):
        pytest.skip("jq is required by publish_docs.sh")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    data = tmp_path / "data"
    data.mkdir()
    calls = tmp_path / "calls"

    def stub(name, body):
        path = bin_dir / name
        path.write_text(f"#!{sys.executable}\n" + body)
        path.chmod(0o755)

    stub("yq", """import sys, yaml
with open(sys.argv[-1] if sys.argv[-1].endswith('.yaml') else 0) as stream:
    data = yaml.safe_load(stream)
if 'dry_run' in sys.argv[2]:
    print(str(data.get('dry_run', False)).lower())
else:
    print('\\n'.join(arch for release in data['releases'] for arch in release['architectures']))
""")
    stub("git", "from pathlib import Path\nimport sys\nPath(sys.argv[-1].rsplit('/', 1)[-1]).mkdir()\n")
    stub("pip", "pass\n")
    stub("make", f"""from pathlib import Path
for folder in ['docs/docker.io/ubuntu', 'docs/public.ecr.aws/ubuntu', 'docs/public.ecr.aws/ubuntu/usage']:
    path = Path(folder)
    path.mkdir(parents=True, exist_ok=True)
    (path / 'example_doc_data.md').write_text({MARKDOWN!r})
""")
    for name in ("curl", "aws"):
        stub(name, f"""import json, sys
with open({str(calls)!r}, 'a') as stream:
    stream.write(json.dumps([{name!r}] + sys.argv[1:]) + '\\n')
print('{{"token": "test-token"}}')
""")
    env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ['PATH'],
               RUNNER_DEBUG='0', DOCKER_HUB_CREDS_USR_DOC='test', DOCKER_HUB_CREDS_PSW_DOC='test',
               DOCKER_HUB_NAMESPACE='docker.io/test', ECR_CREDS_USR='test', ECR_CREDS_PSW='test',
               ECR_REGISTRY_ID='test')

    def run(dry_run, marked=False, architectures=None):
        content = {'releases': [{'architectures': architectures if architectures is not None else ['amd64', 'arm64']}]}
        if marked:
            content['dry_run'] = True
        (data / 'example_doc_data.yaml').write_text(yaml.safe_dump(content))
        return subprocess.run(
            ['bash', '-e', str(SCRIPT), 'example', 'example_doc_data.yaml', str(data)],
            cwd=tmp_path, env=dict(env, DRY_RUN=str(dry_run).lower()), text=True, capture_output=True,
        )

    return run, data, calls


@pytest.mark.parametrize('dry_run', [False, True])
@pytest.mark.parametrize('architectures', [[], ['amd64', 'arm64']])
def test_payload_round_trip_and_publish_boundary(publisher, dry_run, architectures):
    run, data, calls = publisher
    result = run(dry_run, marked=dry_run, architectures=architectures)
    assert result.returncode == 0, result.stderr
    assert (data / 'example_doc_data.yaml').exists()
    dh = json.loads((data / 'dockerhub-docs.json').read_text())
    ecr = json.loads((data / 'ecr-docs.json').read_text())
    assert dh['full_description'] == (data / 'doc-preview.md').read_text() == MARKDOWN
    assert ecr['usageText'] == (data / 'ecr-usage-preview.md').read_text() == MARKDOWN
    assert ecr['aboutText'] == (data / 'ecr-about-preview.md').read_text() == MARKDOWN
    assert ('operatingSystems' in ecr) == bool(architectures)
    if dry_run:
        assert not calls.exists(), 'Dry-run must not authenticate or write to registries'
    else:
        commands = [json.loads(line) for line in calls.read_text().splitlines()]
        assert [command[0] for command in commands] == ['curl', 'curl', 'aws']
        assert '@' + str(data / 'dockerhub-docs.json') in commands[1]
        assert 'file://' + str(data / 'ecr-docs.json') in commands[2]


def test_dry_run_data_is_rejected_in_live_mode(publisher):
    run, data, calls = publisher
    result = run(False, marked=True)
    assert result.returncode != 0
    assert 'Dry-run documentation data cannot be published' in result.stdout + result.stderr
    assert not calls.exists()
    assert not (data / 'dockerhub-docs.json').exists()
