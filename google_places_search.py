#!/usr/bin/env python3
import sys
import json
from pprint import pprint
from places import SearchPlaces

def main(query):
    with SearchPlaces(query) as sp:
        for result in sp:
            if result is None:
                return 1
            print(f'result size: {len(result)}')
            # print(json.dumps(result, indent=4))
    return 0


if __name__ == '__main__':
    if len(sys.argv) == 0:
        print(f'{os.path.basename(sys.argv[0])} <search string>', file=sys.stderr)
        sys.exit(1)
    sys.exit(main(' '.join(sys.argv[1:])))
