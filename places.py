"""
The SearchPlaces class provides a caching client to the Google
Maps Places API.

https://developers.google.com/maps/documentation/places/web-service/text-search?hl=en&_gl=1*1mjxmyq*_ga*MTA3NDAyNTQ3Mi4xNzQwODg5MTQz*_ga_NRWSTWS78N*MTc0MDg4OTE0My4xLjEuMTc0MDg4OTE3MC4wLjAuMA..&apix_params=%7B%22fields%22%3A%22*%22%2C%22resource%22%3A%7B%22textQuery%22%3A%22Spicy%20Vegetarian%20Food%20in%20Sydney%2C%20Australia%22%7D%7D

includedType : parameter values defined in Table A

    https://developers.google.com/maps/documentation/places/web-service/place-types#table-a

locationBias : bias which means results around the specified location can be returned

    Note: If you omit both locationBias and locationRestriction, then the API uses IP
          biasing by default. With IP biasing, the API uses the device's IP address to
          bias the results.
    Note: The locationBias parameter can be overridden if the textQuery contains an
          explicit location such as Market in Barcelona. In this case, locationBias is
          ignored.

regionCode : code used to format the response

    https://www.unicode.org/cldr/charts/46/supplemental/territory_language_information.html



"""
import os
import re
import sys
import pickle
import hashlib
import httplib2
import google_auth_httplib2
from pprint import pprint
from google.oauth2 import service_account
from googleapiclient.discovery import build

class SearchPlaces:

    home = os.environ.get('HOME', None)
    CACHE_DIR = os.path.join(home, 'google-places-cache')
    SERVICE_ACCOUNT_FILE = os.path.join(home, 'dealer-db-e412904af5d6.json')


    class Cache:
        def __init__(self, key, default=None):
            os.makedirs(SearchPlaces.CACHE_DIR, exist_ok=True)
            filename = os.path.join(SearchPlaces.CACHE_DIR, f'{key}.pkl')
            if not os.path.exists(filename) and default is not None:    
                with open(filename, 'wb') as f:
                    pickle.dump(default, f)
            self.filename = filename

        def __len__(self):
            data = self.read()
            if data is not None:
                return len(data)
            return 0

        def read(self):
            data = None
            if os.path.exists(self.filename):
                with open(self.filename, 'rb') as f:
                    data = pickle.load(f)
                # print(f'Read {len(data)} items from: {os.path.basename(self.filename)}',
                #       file=sys.stderr, flush=True)
            return data

        def store(self, data):
            with open(self.filename, 'wb') as f:
                pickle.dump(data, f)
                # print(f'Wrote {len(data)} items to: {os.path.basename(self.filename)}',
                #       file=sys.stderr, flush=True)
                return True
            return False

        def append(self, datum):
            data = self.read()
            if isinstance(data, list):
                data.append(datum)    
            elif isinstance(data, dict):
                data = data | datum
            else:
                data = [datum]
            return self.store(data)

        def last(self):
            data = self.read()
            if data is not None and len(data) > 0:
                if isinstance(data, list):
                    return data[-1]
                elif isinstance(data, dict):
                    return data.keys()[-1]
            return data


    class Page:
        def __init__(self, token, number):
            self.token = token
            self.number = number
            if token is None and number is None:
                self.md5 = None
            elif token is None or number is None:
                self.md5 = f'{token}/{number}'
            else:
                self.md5 = hashlib.md5(token.encode('utf-8')).hexdigest() + f'/{number}'
        def __str__(self):
            if self.token is None:
                return f'[{self.token}, {self.number}]'
            return f'[{len(self.token)} byte token, {self.number}]'
        def __repr_(self):
            return f'{self.__class__.__name__}("{self.token}", {self.number})'
        def is_last(self):
            return self.md5 == None

    class CustomHttp(httplib2.Http):
        def request(self, uri, method="GET", body=None, headers=None, **kwargs):
            if headers is None:
                headers = {}
            # custom header
            headers["X-Goog-FieldMask"] = "*"
            return super().request(uri, method=method, body=body,
                                        headers=headers, **kwargs)

    def __init__(self, query):
        credentials = service_account.Credentials.from_service_account_file(
            self.SERVICE_ACCOUNT_FILE,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        custom_http = self.CustomHttp()
        authorized_http = google_auth_httplib2.AuthorizedHttp(credentials,
                                                              http=custom_http)
        self.id = None
        self.pages = None
        self.query = query
        self.service = build('places', 'v1', http=authorized_http)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def __iter__(self):
        return self

    def __next__(self):
        result = self.search()
        if result is None:
            raise StopIteration
        return result

    def get_id(self):
        """
        The ID is an MD5 hash based on the query text.
        """
        if self.id is None:
            query = re.sub(r'\s+', " ", self.query.lower().strip())
            self.id = hashlib.md5(query.encode('utf-8')).hexdigest()
        return self.id

    def get_page(self):
        """
        The page token is provided by the 'nextPageToken' field in the results.
        The first page is {"", 0}, and subsequent pages {nextPageToken, n}.
        """
        if self.pages is None: 
            query_id = self.get_id()
            self.pages = self.Cache(f'{query_id}-pages',
                                    default=[self.Page(None, 0)])
        return self.pages.last()

    def search(self):
        page = self.get_page()

        if page.is_last():
            return None

        print(f'Current page: {page.md5}',
              file=sys.stderr, flush=True)

        result = self.cache(self.query, page)

        cache_ok = result != None

        print(f'search() page: {page.md5}, cache: {cache_ok}',
              file=sys.stderr, flush=True)

        if result is None:
            request_body = {
                "textQuery": self.query,
            }
            if page.token is not None:
                request_body['pageToken'] = page.token
                print(f'search() requesting pageToken: {page.md5}',
                      file=sys.stderr, flush=True)
            request = self.service.places().searchText(body=request_body)
            result = request.execute()
            if result is not None:
                self.cache(self.query, page, result)

        return result

    def cache(self, query, page, result=None):
        query_id = self.get_id()
        cache = self.Cache(f'{query_id}-{page.number}')
        if result is None:
            result = cache.read()
        else:
            cache.store(result)
            if 'nextPageToken' in result:
                self.pages.append(self.Page(result['nextPageToken'], len(self.pages)))
            else:
                self.pages.append(self.Page(None, None))
            print(f'Next page: {self.pages.last().md5}',
                    file=sys.stderr, flush=True)
        return result
