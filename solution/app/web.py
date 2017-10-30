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
import datetime
import os

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
	print(username)
	print ("OUTPUT FROM DIR IS")
	# image_names = os.listdir('app/static/images/'+username)
	# print (image_names)
	image_names = db.get_imagelist(username)
	print ("OUTPUT FROM DB IS")
	print(tuple(image_names))
	#print(image_names)
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

	#Get User Input
	image = request.files['image']

	#Upload Image to Virtual Disk
	if image and allowed_file(image.filename):
		image_name = secure_filename(image.filename)
		db.add_image(username,image_name)
		destpath = os.path.join(db.virtual_diskpath(),username)
		if not os.path.exists(destpath):
			os.makedirs(destpath)
		image.save(os.path.join(destpath,image_name))

	#Create Transforms
	db.transform_image(os.path.join(destpath,image_name))

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

	#Get User Input
	username = request.form['username']
	userpass = request.form['password']

	# Verify Login Credentials
	if not (db.login_user(username, userpass)):
		return redirect(url_for('file_upload'))

	# Attempt to Upload Image
	if 'image' not in request.files:
		return redirect(url_for('file_upload'))

	image = request.files['image']

	if image.filename == '':
		return redirect(url_for('file_upload'))

	#Upload Image to Virtual Disk
	if image and allowed_file(image.filename):
		image_name = secure_filename(image.filename)
		db.add_image(username,image_name)
		destpath = os.path.join(db.virtual_diskpath(),username)
		if not os.path.exists(destpath):
			os.makedirs(destpath)
		image.save(os.path.join(destpath,image_name))

	#Create Transforms
	db.transform_image(os.path.join(destpath,image_name))

	# Both Login and Upload Successful
	session['username'] = request.form['username']
	return redirect(url_for('homepage'))

def allowed_file(filename):
	return '.' in filename and \
		   filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
