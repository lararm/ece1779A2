###########################################################
# File:		db.py
# Authors:	Irfan Khan				 999207665
#		   	Larissa Ribeiro Madeira 1003209173
# Date:		October 2017
# Purpose: 	Database connection calls.
###########################################################
from app import webapp
import hashlib
import uuid
import mysql.connector
import random
import os
import shutil
from shutil import copyfile
from wand.image import Image
import re

db_user = 'root'
db_pass = 'ece1779pass'
db_host = '127.0.0.1'
db_name = 'A1'
virtual_disk = '/home/ubuntu/A1/ece1779P1web/solution/app/static/images';

IMAGE_TRANSFORMS = set(['orig', 'redblueshift', 'grayscale', 'overexposed'])


def virtual_diskpath():
	return virtual_disk;


def connector():
	return mysql.connector.connect(user=db_user, password=db_pass, host=db_host, database=db_name)


def add_user(username, password):
	# Open db Connection
	print("Checking if username %s is available..." % (username))
	result = False;
	cnx = connector()
	cursor = cnx.cursor()

	# Retrieve Username Availability
	cursor.execute("SELECT username FROM users WHERE username = '%s'" % (username))
	matching_users = cursor.fetchall()

	if (len(matching_users) == 1):
		print("Sorry username %s is unavailable." % (username))

	elif (len(matching_users) > 1):
		print("More than 1 user with the same username:'%s'. Something bad happened!" % (username))

	else:
		print("Username Available.\nAdding Username: %s" % (username))

		# Encrypt New Password
		passsalt = uuid.uuid4().hex
		hash_object = hashlib.sha1(password.encode('utf-8') + passsalt.encode('utf-8'))
		passhash = hash_object.hexdigest()

		# Add New User
		try:
			cursor.execute("INSERT INTO users (username, passhash, passsalt) VALUES ('%s','%s','%s')" % (
			username, passhash, passsalt))
			cnx.commit()
			result = True;
		except:
			cnx.rollback()

	# Close db connection
	cursor.close()
	cnx.close()
	return result


def login_user(username, password):
	# Open db connection
	print("Attempting to log in as %s..." % (username))
	result = False;
	cnx = connector()
	cursor = cnx.cursor()

	# Retrieve User Information
	cursor.execute("SELECT passhash, passsalt FROM users WHERE username = '%s'" % (username))
	matching_users = cursor.fetchall()

	# Close db connection
	cursor.close()
	cnx.close()

	# Verify Credentials
	if (len(matching_users) == 0):
		print("User Does Not Exist")
	elif (len(matching_users) > 1):
		print("More than 1 user with the same username:'%s'. Something bad happened!" % (username))
	else:
		print("Verifying Credentials...")

		# Recreate Hashed Password
		for row in matching_users:
			passhash = row[0]
			passsalt = row[1]
		hash_object = hashlib.sha1(password.encode('utf-8') + passsalt.encode('utf-8'))
		newhash = hash_object.hexdigest()

		if (passhash == newhash):
			print("User %s authenticated!" % (username))
			result = True
		else:
			print("Password is incorrect!")

	return result


def delete_user(username, password):
	# Check Credentionals before deleting
	if not (login_user(username, password)):
		return False

	# Open db connection
	print("Deleting user %s's account ..." % (username))
	result = False;
	cnx = connector()
	cursor = cnx.cursor()

	# Get user id
	userid = get_userid(username)
	print(userid)

	# Delete user
	try:
		cursor.execute("DELETE FROM users WHERE id = %s " % (userid))
		cnx.commit()
		result = True
	except:
		cnx.rollback

	# Close db connection
	cursor.close()
	cnx.close()

	# Delete Users Directory
	if ((result) and os.path.isdir(os.path.join(virtual_diskpath(), username))):
		shutil.rmtree(os.path.join(virtual_diskpath(), username))

	print("Deleted user %s!" % (username))
	return result;


def get_userid(username):
	# Open db connection
	print("Looking for user %s ..." % (username))
	cnx = connector()
	cursor = cnx.cursor()

	# Retreive id from users table
	cursor.execute("SELECT id FROM users WHERE username = '%s'" % (username))
	matching_users = cursor.fetchall()
	for row in matching_users:
		userid = row[0]

	# Close db connection
	cursor.close()
	cnx.close()

	return userid


def image_exists(username, imagename):
	# Open db connection
	print("Looking for image %s ..." % (imagename))
	cnx = connector()
	cursor = cnx.cursor()

	# Retreive userid From users Table
	userid = get_userid(username)

	# Retrieve image From images Table
	cursor.execute("SELECT imagename FROM images WHERE userid = %s && imagename = '%s'" % (userid, imagename))
	image_list = cursor.fetchall()

	if (len(image_list) == 0):
		print("Image %s does not exist!" % (imagename))
		return False

	print("Image %s does exist!" % (imagename))

	# Close db connection
	cursor.close()
	cnx.close()

	return True


def add_image(username, imagename):
	# Get information about image and user
	userid = get_userid(username)
	imagedir = os.path.join(virtual_diskpath(), username)

	# Open db connection
	print("Uploading image %s ..." % (imagename))
	result = False
	cnx = connector()
	cursor = cnx.cursor()

	# Determine If Image Exists
	if (image_exists(username, imagename)):
		# Close db connection
		cursor.close()
		cnx.close()
		return result

	# Insert filename to images table
	try:
		cursor.execute(
			"INSERT INTO images (userid,imagename,orig,redblueshift,grayscale,overexposed) VALUES (%d,'%s','NULL','NULL','NULL','NULL')" % (
			userid, imagename))
		cnx.commit()
		result = True
	except:
		cnx.rollback()

	# Split the image name into rawname and extension
	(rawname, ext) = os.path.splitext(imagename)

	# Update row with paths to each transform
	for transform in IMAGE_TRANSFORMS:
		transformed_image = os.path.join(imagedir, rawname + "_" + transform + ext)
		print(transformed_image)
		try:
			# print("UPDATE images SET %s = '%s' WHERE imagename = '%s'" % (transform, re.escape(transformed_image), imagename))
			cursor.execute("UPDATE images SET %s = '%s' WHERE imagename = '%s'" % (
			transform, re.escape(transformed_image), imagename))
			cnx.commit()
			result = True
		except:
			cnx.rollback()

	# Close db connection
	cursor.close()
	cnx.close()

# return result

def get_imagelist(username):
	# Open db connection
	print("Loading user %s's images ..." % (username))
	result = False
	cnx = connector()
	cursor = cnx.cursor()

	# Retreive userid From users Table
	userid = get_userid(username)

	# Retrieve image_name From images Table
	cursor.execute("SELECT orig FROM images WHERE userid = %s" % (userid))
	print("SELECT orig FROM images WHERE userid = %s" % (userid))
	image_list = cursor.fetchall()

	# Close db connection
	cursor.close()
	cnx.close()

	newlist = []
	print(image_list)
	for images in image_list:
		newlist.append(images[0].split(
			'/home/ubuntu/A1/ece1779P1web/solution/app/static/',
			1)[1].replace('\\', '/'))
	print(newlist)

	return newlist


def get_transforms(username, imagename):
	print("get_transforms")
	# Open db connection
	print("Loading user %s's images ..." % (username))
	result = False
	cnx = connector()
	cursor = cnx.cursor()
	imagename = imagename[:-1]
	imagename = "/home/ubuntu/A1/ece1779P1web/solution/app/static/" + imagename

	# Retreive userid From users Table
	userid = get_userid(username)

	# Retrieve image_name From images Table
	cursor.execute("SELECT orig,redblueshift,overexposed,grayscale FROM images WHERE userid = %s && orig= '%s'" % (
	userid, re.escape(imagename)))
	transforms = cursor.fetchall()

	# Close db connection
	cursor.close()
	cnx.close()

	# Create a list that is compliant with HTML code
	newlist = []
	newlist2 = []

	for orig, redblueshift, overexposed, grayscale in transforms:
		newlist.append(orig)
		newlist.append(redblueshift)
		newlist.append(overexposed)
		newlist.append(grayscale)

	for image in newlist:
		image = image.split("/home/ubuntu/A1/ece1779P1web/solution/app/static/",1)[1]
		image = image.replace('\\', '/')
		newlist2.append(image)

	return newlist2


def get_image(username, imagename, transform):
	# Open db connection
	print("Retrieving image %s version of %s  ..." % (transform, imagename))
	cnx = connector()
	cursor = cnx.cursor()

	# Retreive userid From users Table
	userid = get_userid(username)

	# Retreive Image Path
	if (image_exists(username, imagename)):
		cursor.execute("SELECT %s FROM images WHERE userid = %s && imagename = '%s'" % (transform, userid, imagename))
		imageinfo = cursor.fetchall()

		for row in imageinfo:
			image = row[0]

	# Return Path to Image
	print("Retreived %s" % (image))
	return image


def delete_image(username, imagename):
	print("Deleting image %s..." % (imagename))

	if not (image_exists(username, imagename)):
		return False

	# Delete image
	filename = os.path.join(virtual_diskpath(), username, imagename)
	print("Deleting %s" % (filename))
	if (os.path.exists(filename)):
		print("Deleting %s" % (filename))
		os.remove(filename)

	# Delete transforms
	for transform in IMAGE_TRANSFORMS:
		filename = get_image(username, imagename, transform)
		print("Deleting %s" % (filename))
		if (os.path.exists(filename)):
			print("Deleting %s" % (filename))
			os.remove(filename)

	# Open db connection
	result = False
	cnx = connector()
	cursor = cnx.cursor()

	# Remove entry from DB
	try:
		userid = get_userid(username)
		cursor.execute("DELETE FROM images WHERE userid = %s && imagename = '%s'" % (userid, imagename))
		cnx.commit()
		result = True
	except:
		cnx.rollback

	# Close db connection
	cursor.close()
	cnx.close()

	return result


def transform_image_orig(image, img):
	destImage = image[:-4] + '_orig' + image[-4:]
	img.save(filename=destImage)


def transform_image_redblueshift(image, img):
	img.evaluate(operator='rightshift', value=1, channel='blue')
	img.evaluate(operator='leftshift', value=1, channel='red')

	destImage = image[:-4] + '_redblueshift' + image[-4:]
	img.save(filename=destImage)


def transform_image_grayscale(image, img):
	img.type = 'grayscale';
	destImage = image[:-4] + '_grayscale' + image[-4:]
	img.save(filename=destImage)


def transform_image_overexposed(image, img):
	img.evaluate(operator='leftshift', value=1, channel='blue')
	img.evaluate(operator='leftshift', value=1, channel='red')
	img.evaluate(operator='leftshift', value=1, channel='green')
	destImage = image[:-4] + '_overexposed' + image[-4:]
	img.save(filename=destImage)


def transform_image_enhancement(image, img):
	img.level(0.2, 0.9, gamma=1.1)
	destImage = image[:-4] + '_enhancement' + image[-4:]
	img.save(filename=destImage)


def transform_image_flip(image, img):
	img.flop()
	destImage = image[:-4] + '_flip' + image[-4:]
	img.save(filename=destImage)


def transform_image(image):
	ImageFormat = re.compile('.*(\.)(.*)')
	ImageFormat_Match = ImageFormat.match(image)
	with Image(filename=image) as img:
		transform_image_orig(image, img.clone())
		transform_image_redblueshift(image, img.clone())
		transform_image_grayscale(image, img.clone())
		transform_image_overexposed(image, img.clone())
