# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
# EMS API SDK
# EMS Russian Post state company  API wrapper
# Created from scratch using docs http://www.emspost.ru/ru/corp_clients/dogovor_docements/api/
# for Teleme Team project
# Author Oleg Rybkin aka Fish (okfish@yandex.ru)

import os
import json
from urllib import urlencode

import pycurl

try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO

location = lambda x: os.path.join(
    os.path.dirname(os.path.realpath(__file__)), x)


API_VERSION = '1.0'
API_BASE_URL = 'http://emspost.ru/api/rest/'

API_METHODS = {'echo'       : 'ems.test.echo',
               'locations'  : 'ems.get.locations',
               'maxweight'     : 'ems.get.max.weight',
               'calculate'  : 'ems.calculate'}

# Source: http://www.emspost.ru/ru/corp_clients/dogovor_docements/api/
API_CALC_OPTIONS = { 
# from (обязательный, кроме международной доставки) — идентификатор пункта отправления. 
#    Для получения списка допустимых идентификаторов используется метод ems.get.locations.
    'from' : 0,
# to (обязательный) - идентификатор пункта назначения. 
#    Для получения списка допустимых идентификаторов используется метод ems.get.locations.
    'to' : 0,
# weight (обязательный) — вес отправления. 
#    Значение не должно превышать максимально допустимый вес отправления, 
#    значение которого возвращается методом ems.get.max.weight.
    'weight' : 1, # kg 
# type (обязательный для международной доставки) — тип международного отправления. 
#    Допустимые значения:
#    doc — документы (до 2-х килограм),
#    att — товарные вложения.
    'type' : 'att',
}

def curl_setopt_array(curl, opts):
    for key in opts:
        curl.setopt(getattr(curl, key), opts[key])
        
class EmsAPIException(Exception):
    """
    EmsAPI class can raise this exception
    """
    pass

class EmsAPI(object):
    """
    Main EMS API SDK class. 
    Handles calls to the EMSPost API via pycURL.
    """

    # Base URL
    __api_url = '';

    # CURL options overrides
    __curl_opts = {}
    
    # CURL instance
    __ch = None;
    
    # CURL IO buffer
    __buffer = None
    
    def __init__(self, api_url=None, curl_opts={}):
        """
        API class constructor.
        Opional parameters: api_url, curl_opts
        """
        self.__api_url = api_url or API_BASE_URL
        self.__curl_opts = curl_opts
        self.__buffer = BytesIO()
  
    def __init_curl(self):
       self.__ch = pycurl.Curl()
       opts = {'WRITEDATA':  self.__buffer,
               'HTTPHEADER': ['Content-Type: application/json; charset=utf-8',],
               'NOSIGNAL' : 1 # see http://stackoverflow.com/questions/9191668/error-longjmp-causes-uninitialized-stack-frame
               }
       opts.update(self.__curl_opts)
       curl_setopt_array(self.__ch, opts)

    def __construct_api_url(self, method, data):
        data['method'] = API_METHODS[method]
        return '%s?%s' % (self.__api_url, urlencode(data))
    
    def filter(self, data, predicate=lambda k, v: True):
        """
            Attemp to mimic django's queryset.filter() for simple lists
            proudly stolen from http://stackoverflow.com/a/1215039
            Usage:
                list(filter_data(test_data, lambda k, v: k == "key1" and v == "value1"))
        """
        for d in data:
             for k, v in d.items():
                   if predicate(k, v):
                        yield d
    
    
    def close(self):
        if self.__ch:
            self.__ch.close()
        if not self.__buffer.closed:
            self.__buffer.close()

    def call(self, method, data, plain=False):
        """
            Makes a call to remote API. 
        """
        result = None
        if plain:
            data['plain'] = plain
        #if self.__buffer.closed:
        #    self.__buffer = BytesIO()
                    
        if self.__ch is None:
            self.__init_curl()

        #json_data = json.dumps(data)
        curl_setopt_array(self.__ch, { 'URL' : self.__construct_api_url(method, data),
                                       })
        try:
            self.__ch.perform()
        except pycurl.error as e:
            raise EmsAPIException(e)
        result = self.__buffer.getvalue()
        if self.__ch.errstr():
            raise EmsAPIException(self.__ch.c.errstr())
        else:
            http_code = self.__ch.getinfo(pycurl.HTTP_CODE)
            if http_code <> 200:
                raise EmsAPIException("HTTP Error code: %d" % http_code)
            else:
                result = json.loads(result)
        self.__buffer.truncate(0)
        self.__buffer.seek(0)
        return result
    
    def is_online(self):
        """
            Check if API is online or not. 
            Returns boolean.
        """
        res = self.call('echo', {})
        if 'rsp' in res.keys():
            ok = res['rsp'].get('stat', False)
            if ok == 'ok':
                return True
        return False

    def findbytitle(self, title=None, type='cities'):
        """
        Finds EMS city code by title or returns all of them.
        
        Return tuple (result, error), where result is a list of tuples
        (id, title, type)
        Use type='russia' and None title to get all codes or '<title>', 'regions'
        to search over russian regions.
        """
        result = []
        data = { 'type' : type }
        try:
            res = self.call('locations', data, True)
        except EmsAPIException as e:
            return None, e
        if 'rsp' in res.keys():
            if res['rsp'].get('stat', False) == 'ok':
                locs = res['rsp']['locations']
                if title:
                    locs = self.filter(locs, 
                                       lambda k,v: k == u'name' and title.lower() in v.lower() )
            
                for city in locs:
                    result.append((city['value'],
                                   city['name'],
                                   city['type'],
                                  ))
                if len(result)>0:
                    return result, 0
                else:
                    return None, 'not_found'
            else:
                return None, res['rsp']['err']
        else:
            return None, 'not_found'

    def get_branches(self):
        """
        Returns a tuple of (list, error) of all EMS regions 
        and cities where list of tuples (id, title, type).
        """
        return self.findbytitle('','russia')

    def calculate(self, payload):
        """
        Calculates shipping charge using API.

        """
        data = API_CALC_OPTIONS
        data.update(payload)
        
        res = []
        
        try:
            res = self.call('calculate', data, True)
        except EmsAPIException as e:
            return None, e
        return res, 0
    
    def get_max_weight(self):
        """
        Return maximum weight per package (in kg)
        """
        res = []
        
        try:
            res = self.call('maxweight', {}, True)
        except EmsAPIException as e:
            return None, e
        if 'rsp' in res.keys():
            if res['rsp'].get('stat', False) == 'ok':
                return res['rsp']['max_weight'], 0
            else:
                return None, res['rsp']['err']
        else:
            return None, 'api_error'
