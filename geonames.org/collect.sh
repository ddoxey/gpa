#!/bin/bash
##
# Collect zip codes and lat/long for
# all the counties in all the states.
##
BASE_URL="https://www.geonames.org"

# https://github.com/ddoxey/ccurl
CCURL="$(which ccurl)"

if [[ -z $CCURL ]]
then
    echo "Can't find: ccurl" >&2
    exit 1
fi

function parse_states() {
    grep -A1 '^<div'         | \
        grep '^<a '          | \
        sed "s/, /\n/g"      | \
        grep '^<a '          | \
        sed -e 's|<[^">]*>||g' \
            -e 's|">|"|'     | \
            awk -F'"' -v B="$BASE_URL" '{print B $2 "|" $3}'
}

function parse_counties() {
    grep '<small>'              | \
        grep -v '<small>Either' | \
        sed -e 's/<[^>]*>/|/g'    \
            -e 's/[|][|]*/|/g'    \
            -e 's/^[|]//'         \
            -e 's/[|]$//'         \
            -e 's/&nbsp;/ /g'     \
            -e 's/|[ ][ ]*|/|/g'
}

function run() {

    pushd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null

    if [[ ! -f states.psv ]]
    then
        echo "URL|State" > states.psv

        $CCURL -L "{$BASE_URL}/postal-codes/postal-codes-us.html" 2>/dev/null | \
            parse_states >> states.psv

        wc -l states.psv
    fi

    if [[ ! -f counties.psv ]]
    then
        echo "Index|City|Zip|Country|State|County|Lat/Long" > counties.psv

        awk -F'|' '{print $1}' states.psv | \
            while IFS=$'\n' read -r url
            do
                $CCURL "$url" 2>/dev/null | parse_counties >> counties.psv
            done

        wc -l counties.psv
    fi

    popd >/dev/null
}

run "$@"
