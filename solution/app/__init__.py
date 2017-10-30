###########################################################
# File:		__init__.py
# Authors:	Irfan Khan				 999207665
#		   	Larissa Ribeiro Madeira 1003209173
# Date:		October 2017
# Purpose: 	Initializing script for python
###########################################################
from flask import Flask

webapp = Flask(__name__)

# Secret Key
webapp.secret_key = 'A012315r98j/3yXa343790R~XHH!jmsadadasjkdhLWX/,?RT'

from app import web
from app import db
