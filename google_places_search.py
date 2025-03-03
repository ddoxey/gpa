#!/usr/bin/env python3
import os
import csv
import sys
import json
from pprint import pprint
from places import SearchPlaces

COUNTIES_PSV = 'geonames.org/counties.psv'

def main(query):

    locations = set()

    with open(COUNTIES_PSV, encoding='utf-8') as fh:
        counties = csv.reader(fh, delimiter='|')
        for county in counties:
            name = f'{county[-2]}, {county[-3]}'
            lat, long = county[-1].split('/')
            locations.add(SearchPlaces.Location(name, lat, long))
   
    for loc in sorted(list(locations)):
        with SearchPlaces(query, loc) as sp:
            for result in sp:
                if result is None:
                    return 1
                print(f'{loc.name} result size: {len(result)}\n')
    return 0


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print(f'{os.path.basename(sys.argv[0])} <search string>', file=sys.stderr)
        sys.exit(1)
    sys.exit(main(' '.join(sys.argv[1:])))
