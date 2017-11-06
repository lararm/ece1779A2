###########################################################
# File:		db.py
# Authors:	Irfan Khan		 999207665
#		Larissa Ribeiro Madeira 1003209173
# Date:		November  2017
# Purpose: 	Database connection calls.
###########################################################

import boto3
from flask import render_template, redirect, url_for, request
from datetime import datetime, timedelta
from operator import itemgetter
from app import webapp
from app import config

def clear_user_data():
    
    # Open DB Connection
    cnx = mysql.connector.connect(user=config.DB_USER, password=config.DB_PASS, host=config.DB_HOST, database=config.DB_NAME)
    cursor = cnx.cursor()

    # Execute DB Setup Script 
    cursor.execute("source /home/ubuntu/A2/ece1779A2/Database/DBSetup.sql")

    # Create an S3 client
    s3 = boto3.client('s3', aws_access_key_id=config.AWS_KEY, aws_secret_access_key=config.AWS_SECRET)
    bucket = s3.Bucket(config.S3_ID)
    
    # Delete data in bucket
    bucket.objects.all().delete()
