#! /bin/bash

set -e

source $(dirname $0)/../../shared/logs.sh

function usage(){
    echo
    echo "$(basename "$0") -d <rock directory> -n <archive name>"
    echo
    echo "Merge multiple OCI rock images into one multi arch image."
    echo
    echo -e "-d \\t Directory to search for rock OCI images in."
    echo -e "-n \\t Final output archive name. "
}

while getopts "d:n:" opt
do
    case $opt in
        d)
            ROCK_DIR="$OPTARG"
            ;;
        n)
            ARCHIVE_NAME="$OPTARG"
            ;;
        ?)
            usage
            exit 1
            ;;
    esac
done

if [ -z "$ROCK_DIR" ]
then
    log_error "Missing rock search directory argument (-d)"
    usage
    exit 1
fi

if [ -z "$ARCHIVE_NAME" ]
then
    log_error "Missing final archive name (-n)"
    usage
    exit 1
fi

buildah manifest create multi-arch-rock

for rock in `find "$ROCK_DIR" -name "*.rock" -type f`
do
    buildah manifest add multi-arch-rock oci-archive:$rock
done

buildah manifest push --format oci --all multi-arch-rock "oci-archive:$ARCHIVE_NAME"
