from StringIO import StringIO
from textwrap import dedent
from urlparse import urlparse
import email.utils
import httplib
import mimetypes
import os
import json
import logging

from KASignature import KASignature

version = '1.2.0'

# Configuration 

# with KA auth, both http and https are possible
UPLOAD_ENDPOINT = 'https://upload-api.kooaba.com/'
QUERY_ENDPOINT= 'https://query-api.kooaba.com/v4/query'

logger = logging.getLogger(__name__)

class BasicAPIClient:
    """ Client for kooaba  API V4. """

    def __init__(self, secret_token, key_id=None):
        self.KA = KASignature(secret_token)
        self.key_id = key_id
        self.secret_token = secret_token


    #### QUERY API   

    def query(self,filename, auth_method='Token'):
        data, content_type = self.data_from_file(filename)
        content_type, body = self.encode_multipart_formdata([],[('image', filename, data)])

        (response, body) = self._send_request('POST', QUERY_ENDPOINT, bytearray(body), content_type, auth_method)
        return json.loads(body)


    #### UPLOAD API (subset of available methods)

    def create_item(self, bucket_id, title, refid, json_string):
        url = UPLOAD_ENDPOINT+'api/v4/buckets/'+bucket_id+'/items'

        metadata = json.loads(json_string)
        data = {"title":title, "reference_id":refid, "metadata":metadata}

        (response, body) = self._send_request('POST', url, json.dumps(data), 'application/json')
        return json.loads(body)


    def attach_image(self, bucket_id, item_id, content_type, data):
        url = UPLOAD_ENDPOINT+'api/v4/items/'+item_id+'/images'

        (response, body) = self._send_request('POST', url, bytearray(data), content_type)
        return json.loads(body)

   
    def replace_metadata(self, item_id, json_string):
        url = UPLOAD_ENDPOINT+'api/v4/items/'+item_id
        metadata = json.loads(json_string)
        data = {"metadata": metadata}
        (response, body) = self._send_request('PUT', url, json.dumps(data), 'application/json')
        return json.loads(body)

    
    ## HELPER METHODS
    
    def data_from_file(self,filename):
        content_type, _encoding = mimetypes.guess_type(filename)
        with open(filename, 'rb') as f:
            return f.read() , content_type

    def _send_request(self, method, api_path, data=None, content_type=None, auth_method='Token'):
        """ Send (POST/PUT/GET/DELETE according to the method) data to an API
        node specified by api_path.

        Returns tuple (response, body) as returned by the API call. The
        response is a HttpResponse object describint HTTP headers and status
        line.

        Raises exception on error:
            - IOError: Failure performing HTTP call
            - RuntimeError: Unsupported transport scheme.
            - RuntimeError: API call returned an error.
        """

        if data is None:
            logger.info("> %s %s", method, api_path) 
        elif len(data) < 4096:
            logger.info("> %s %s: > %s", method, api_path, data)
        else:
            logger.info("> %s %s: %sB", method, api_path, len(data))
        
        parsed_url = urlparse(api_path)
        
        if ((parsed_url.scheme != 'https') and (parsed_url.scheme != 'http')):
            raise RuntimeError("URL scheme '%s' not supported" % parsed_url.scheme)
       
        port = parsed_url.port
        if port is None:
            port = 80 
            if (parsed_url.scheme == 'https'):
               port = 443

        host = parsed_url.hostname

        if (parsed_url.scheme == 'https'):
            http = httplib.HTTPSConnection(host, port )
        elif (parsed_url.scheme == 'http'):
            http = httplib.HTTPConnection(host, port )
        else:
            raise RuntimeError("URL scheme '%s' not supported" % parsed_url.scheme)
        
        try:
            date = email.utils.formatdate(None, localtime=False, usegmt=True)

            if auth_method=='KA':
                signature = self.KA.sign(method, data, content_type, date, parsed_url.path)
                headers = {'Authorization': 'KA %s:%s' % (self.key_id,signature),'Date': date}
                logger.info("signature: %s", headers['Authorization'])
            else: # Token
                headers = {'Authorization': 'Token %s' % (self.secret_token),'Date': date}

            if content_type is not None:
                headers['Content-Type'] = content_type

            if data is not None:
                headers['Content-Length'] = str(len(data))

            try:
                http.request(method, parsed_url.path, body=data,  headers=headers)
            except Exception, e:
                raise  #IOError("Error during request: %s: %s" % (type(e), e))

            response = http.getresponse()
            # we have to read the response before the http connection is closed
            body = response.read()
            logger.info("< %d %s", response.status, response.reason)
            logger.info("< %s", body)

            return (response, body)
        finally:
            http.close()


    def encode_multipart_formdata(self, fields, files):
        """
        fields is a sequence of (name, value) elements for regular form fields.
        files is a sequence of (name, filename, value) elements for data to be uploaded as files
        Return (content_type, body) ready for httplib.HTTP instance
        """

        BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
        CRLF = '\r\n'
        L = []
        for (key, value) in fields:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"' % key)
            L.append('')
            L.append(value)
        for (key, filename, value) in files:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
            L.append('Content-Type: %s' % self.get_content_type(filename))
            L.append('')
            L.append(value)
        L.append('--' + BOUNDARY + '--')
        L.append('')
        body = CRLF.join(L)
        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
        return content_type, body

    def get_content_type(self, filename):
        return mimetypes.guess_type(filename)[0] or 'application/octet-stream' 

