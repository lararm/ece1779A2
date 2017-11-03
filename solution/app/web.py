###########################################################
# File:		web.py
# Authors:	Irfan Khan				 999207665
#		   	Larissa Ribeiro Madeira 1003209173
# Date:		October 2017
# Purpose: 	Webpage routes
###########################################################
from flask import render_template, session, request, escape, redirect, url_for
from werkzeug.utils import secure_filename
from app import webapp
from app import db
from app import config
import datetime
import os
import boto3

ALLOWED_IMAGE_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
@webapp.route('/')
def main():
	#session.clear()

	if 'username' in session:
		print ("Session user is: %s" % escape(session['username']))
		return redirect(url_for('homepage'))
	return render_template("login.html")

@webapp.route('/login', methods=['GET','POST'])
def login():
	if 'username' in session:
		print ("Session user is: %s" % escape(session['username']))
		return redirect(url_for('homepage'))
	return render_template("login.html")

@webapp.route('/tests3', methods=['GET', 'POST'])
def tests3():
    # Create an S3 client
    s3 = boto3.client('s3')
    # Call S3 to list current buckets
    response = s3.list_buckets()
    # Get a list of all bucket names from the response
    buckets = [bucket['Name'] for bucket in response['Buckets']]
    bucket = buckets[0]
    # Print out the bucket list
    print("Bucket List: %s" % buckets)
    print("Bucket: %s" % bucket)

    # filename = 'C:/Users/Larissa/Documents/UofT/Intro_Cloud_Computing/A2/solution/app/static/android2.png'
    # bucket_name = bucket
    #
    # # Uploads the given file using a managed uploader, which will split up large
    # # files automatically and upload parts in parallel.
    # s3.upload_file(filename, bucket_name, filename)

    return render_template("login.html")

@webapp.route('/signup', methods=['GET','POST'])
def signup():
	if 'username' in session:
		print ("Session user is: %s" % escape(session['username']))
		return redirect(url_for('homepage'))
	return render_template("signup.html")

@webapp.route('/homepage', methods=['GET','POST'])
def homepage():
	if 'username' not in session:
		return render_template("main.html")
	print ("Session user is: %s" % escape(session['username']))
	username = escape(session['username'])
	image_names = db.get_imagelist(username)
	return render_template("homepage.html",image_names=image_names,username=username)



@webapp.route('/transform_image', methods=['GET','POST'])
def transforms():
	print("#transform")
	# Get User Input
	if request.method == 'GET':
		return render_template("transforms.html")

	image_name = request.form['image_name']

	if 'username' not in session:
		return render_template("main.html")

	username = escape(session['username'])

	image_names = db.get_transforms(username,image_name)
	print(image_name)

	return render_template("transforms.html",image_names=image_names,username=username)


@webapp.route('/login_submit', methods=['POST'])
def login_submit():

	#Get User Input
	username = request.form['username']
	password = request.form['password']
	
	#Login
	if (db.login_user(username, password)):
		session['username'] = request.form['username']
		return redirect(url_for('homepage'))
	else:
		return redirect(url_for('login'))

@webapp.route('/signup_submit', methods=['POST'])
def signup_submit():
	
	#Get User Input
	username = request.form['username']
	password = request.form['password']

	#Add User
	if (db.add_user(username, password)):
		session['username'] = request.form['username']
		return redirect(url_for('homepage'))
	else:
		return redirect(url_for('signup'))

@webapp.route('/logout_submit', methods=['POST'])
def logout_submit():
	
	#Get Session Information
	username = escape(session['username'])

	#Close Session
	session.pop('username',None)
	return redirect(url_for('main'))


@webapp.route('/delete_user_submit', methods=['POST'])
def delete_user_submit():
	
	#Get Session Information
	username = escape(session['username'])

	#Get User Input
	password = request.form['password']

	#Delete the User
	if (db.delete_user(username,password)):
		#Close Session
		session.pop('username',None)
		return redirect(url_for('main'))
	return redirect(url_for('homepage'))

@webapp.route('/upload_image_submit', methods=['POST'])
def upload_image_submit():
	#Get Session Information
	username = escape(session['username'])

	# Get User Input
	image = request.files['image']
	image_name = image.filename
	image_type = image.content_type

	# If user does not select file, browser also
	# submit a empty part without filename
	if image.filename == '':
		return redirect(url_for('homepage', id=id))


	# Create an S3 client
	s3 = boto3.client('s3', aws_access_key_id=config.AWS_KEY, aws_secret_access_key=config.AWS_SECRET)
	id = config.AWS_ID

	# upload image to S3
	image_new_name = username + "/" + image.filename
	s3.upload_fileobj(image, id, image_new_name,
					  ExtraArgs={"Metadata": {"Content-Type": image_type}})
	image_url = (s3.generate_presigned_url('get_object', Params={'Bucket': id, 'Key': image_new_name},
										   ExpiresIn=100)).split('?')[0]
	print(image_url)

	# Download image #TODO change destpath
	destpath = "C:\\Users\\Larissa\\Documents\\UofT\\Intro_Cloud_Computing\\A2\\solution\\app\\static\\images\\";
	new_image_path = destpath + image_name
	s3.download_file(id, image_new_name, new_image_path)

	# Upload Image URL to DB
	db.add_image(username,image_name, image_url)

	# Create Transforms
	db.transform_image(new_image_path, username)

	# Delete Images from Virtual Disk
	if (db.delete_image(username, image_name)):
		print("%s was deleted!" % (image_name))

	return redirect(url_for('homepage'))

@webapp.route('/download_image_submit', methods=['POST'])
def download_image_submit():
	
	#Get Session Information
	username = escape(session['username'])

	#Get User Input
	filename  = request.form['filename']
	filepath  = request.form['filepath']
	transform = request.form['transform']

	#Download Image from Virtual Disk
	image = db.get_image(username,transform,filename)

	return redirect(url_for('homepage'))

@webapp.route('/delete_image_submit', methods=['POST'])
def delete_image_submit():
	
	#Get Session Information
	username = escape(session['username'])
	print(username)

	#Get User Input
	filename = request.form['filename']

	#Delete Images from Virtual Disk
	if (db.delete_image(username,filename)):
		print ("%s was deleted!" % (filename))

	return redirect(url_for('homepage'))

@webapp.route('/test/FileUpload', methods=['GET','POST'])
def file_upload():

    	#Check if user is already logged in
	if 'username' in session:
		print ("Session user is: %s" % escape(session['username']))
		return redirect(url_for('homepage'))

	return render_template("taform.html")

@webapp.route('/test/FileUploadSubmit', methods=['POST'])
def file_upload_submit():

	# Get User Input
	username = request.form['username']
	userpass = request.form['password']

	# Verify Login Credentials
	if not (db.login_user(username, userpass)):
		return redirect(url_for('file_upload'))

	# Attempt to Upload Image
	if 'image' not in request.files:
		return redirect(url_for('file_upload'))

	# Get User Input
	new_file = request.files['image']
	image_name = new_file.filename
	image_type = new_file.content_type
	print(new_file)
	                                                    
	# If user does not select file, browser also
	# submit a empty part without filename
	if new_file.filename == '':
		return redirect(url_for('file_upload', id=id))

	# Create an S3 client
	s3 = boto3.client('s3',aws_access_key_id=config.AWS_KEY,aws_secret_access_key=config.AWS_SECRET)
	id = config.AWS_ID
	                                                                                                                                   
	# Upload image to S3
	s3.upload_fileobj(new_file,id, new_file.filename,
	ExtraArgs = {"Metadata": {"Content-Type":image_type }})
	image_url = (s3.generate_presigned_url('get_object', Params={'Bucket': id, 'Key': new_file.filename},ExpiresIn=100)).split('?')[0]
	print(image_url)

	# Upload Image URL to DB
	db.add_image(username,image_name, image_url)

	#Create Transforms FIXME TODO 
	#db.transform_image(os.path.join(destpath,image_name))

	# Both Login and Upload Successful
	session['username'] = request.form['username']
	return redirect(url_for('homepage'))

def allowed_file(filename): #FIXME TODO rewrite this function to use image_type
	return '.' in filename and \
		   filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
