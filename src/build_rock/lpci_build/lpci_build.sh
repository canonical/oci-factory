#! /bin/bash


set -e

source $(dirname $0)/../../shared/logs.sh

function usage(){
    echo
    echo "$(basename "$0") -d <rockcraft directory> -c <launchpad credentials>"
    echo
    echo "Build local rockcraft project on Launchpad."
    echo
    echo -e "-d \\t Directory to rockcraft project file. "
    echo -e "-c \\t Launchpad credentials. "
}

while getopts "c:d:" opt
do
    case $opt in
        d)
            ROCKCRAFT_DIR="$OPTARG"
            ;;
        c)
            LP_CREDENTIALS_B64="$OPTARG"
            ;;
        ?)
            usage
            exit 1
            ;;
    esac
done

if [ -z "$ROCKCRAFT_DIR" ]
then
    log_error "Missing rockcraft project directory argument (-d)"
    usage
    exit 1
fi

if [ -z "$LP_CREDENTIALS_B64" ]
then
    log_error "Missing launchpad credentials argument (-c)"
    usage
    exit 1
fi


cd "$ROCKCRAFT_DIR"
rocks_toolbox="$(mktemp -d)"

# install dependencies
git clone --depth 1 --branch lpci-build-log https://github.com/canonical/rocks-toolbox $rocks_toolbox
${rocks_toolbox}/rockcraft_lpci_build/requirements.sh
pip3 install -r ${rocks_toolbox}/rockcraft_lpci_build/requirements.txt

python3 ${rocks_toolbox}/rockcraft_lpci_build/rockcraft_lpci_build.py \
    --lp-credentials-b64 "$LP_CREDENTIALS_B64" \
    --launchpad-accept-public-upload
