===============================
EMS Russian Post Python API
===============================

Simple Python API for EMS Russian Post REST service.

Under heavy development. 

Issue: uses CURL in blocking mode!


Quickstart
----------

Install django-oscar-shipping::

    pip install -e git+https://github.com/okfish/py-emspost-api/py-emspost-api.git#egg=py-emspost-api

Usage::

	from emspost_api import emspost
	
	api = emspost.EmsAPI()
	print api.is_online()

Documentation
-------------

The full REST API documentation available at http://www.emspost.ru/ru/corp_clients/dogovor_docements/api/

TODO: EmsAPI docs


Features
--------

* All API methods implemented:
	* ems.test.echo
	* ems.get.locations
	* ems.get.max.weight
	* ems.calculate

License
-------

* Free software: BSD license
	