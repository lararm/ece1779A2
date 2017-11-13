import boto3
import mysql.connector
from flask import render_template, redirect, url_for, request,flash
from datetime import datetime, timedelta
from operator import itemgetter
from app import config
from app import webapp
from app import elb
import threading

global CW_THRESHOLD


@webapp.route('/ec2_examples', methods=['GET'])
# Display an HTML list of all ec2 instances
def ec2_list():
    aws_session = boto3.Session(aws_access_key_id=config.AWS_KEY, aws_secret_access_key=config.AWS_SECRET)
    # create connection to ec2
    ec2 = aws_session.resource('ec2')

    instances = ec2.instances.filter(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    instances = ec2.instances.all()
    # Display S3 info
    # Let's use Amazon S3
    s3 = aws_session.resource('s3')

    # Print out bucket names
    buckets = s3.buckets.all()

    for b in buckets:
        name = b.name

    buckets = s3.buckets.all()

    #Test CloudWatch avgs
    workers_list = []
    for instance in instances:
        # filter db and mananger
        if (instance.id != config.DATABASE_ID and instance.id != config.MANAGER_ID):
             if(( instance.tags[0]['Value'] == 'A2WorkerNode' ) and (instance.state['Name'] != 'terminated')):
                workers_list.append(instance.id)
	
    # Open DB Connection
    cnx    = mysql.connector.connect(user=config.DB_USER, password=config.DB_PASS, host=config.DB_HOST, database=config.DB_NAME)
    cursor = cnx.cursor()

    # Query DB for Autoscale settings
    cursor.execute("SELECT scale,upper_bound,lower_bound,scale_up,scale_down FROM autoscale WHERE id = 1")   
    auto_scale_data = cursor.fetchall()

    if (len(auto_scale_data) == 0):
        flash ("Database is missing autoscale data")

    for scale,upper_bound,lower_bound,scale_up,scale_down in auto_scale_data:
        AUTO_scale       = scale
        AUTO_upper_bound = upper_bound
        AUTO_lower_bound = lower_bound
        AUTO_scale_up    = scale_up
        AUTO_scale_down  = scale_down

    # Close DB Connection
    cursor.close()
    cnx.close()
    return render_template("ec2_examples/list.html", title="Manager UI Dashboard", instances=instances, buckets=buckets,
                           manager=config.MANAGER_ID,
                           database=config.DATABASE_ID,
                           upperBound = AUTO_upper_bound,
                           lowerBound = AUTO_lower_bound,
                           scaleUp = AUTO_scale_up,
                           scaleDown = AUTO_scale_down,
                           scaleStatus = AUTO_scale
                           )



@webapp.route('/ec2_examples/<id>', methods=['GET'])
# Display details about a specific instance.
def ec2_view(id):
    aws_session = boto3.Session(aws_access_key_id=config.AWS_KEY, aws_secret_access_key=config.AWS_SECRET)
    ec2 = aws_session.resource('ec2')

    instance = ec2.Instance(id)

    client = aws_session.client('cloudwatch')

    metric_name = 'CPUUtilization'

    ##    CPUUtilization, NetworkIn, NetworkOut, NetworkPacketsIn,
    #    NetworkPacketsOut, DiskWriteBytes, DiskReadBytes, DiskWriteOps,
    #    DiskReadOps, CPUCreditBalance, CPUCreditUsage, StatusCheckFailed,
    #    StatusCheckFailed_Instance, StatusCheckFailed_System

    namespace = 'AWS/EC2'
    statistic = 'Average'  # could be Sum,Maximum,Minimum,SampleCount,Average

    cpu = client.get_metric_statistics(
        Period=1 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=60 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName=metric_name,
        Namespace=namespace,  # Unit='Percent',
        Statistics=[statistic],
        Dimensions=[{'Name': 'InstanceId', 'Value': id}]
    )

    cpu_stats = []

    for point in cpu['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute / 60
        cpu_stats.append([time, point['Average']])

    cpu_stats = sorted(cpu_stats, key=itemgetter(0))

    statistic = 'Sum'  # could be Sum,Maximum,Minimum,SampleCount,Average

    network_in = client.get_metric_statistics(
        Period=1 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=60 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName='NetworkIn',
        Namespace=namespace,  # Unit='Percent',
        Statistics=[statistic],
        Dimensions=[{'Name': 'InstanceId', 'Value': id}]
    )

    net_in_stats = []

    for point in network_in['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute / 60
        net_in_stats.append([time, point['Sum']])

    net_in_stats = sorted(net_in_stats, key=itemgetter(0))

    network_out = client.get_metric_statistics(
        Period=5 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=60 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName='NetworkOut',
        Namespace=namespace,  # Unit='Percent',
        Statistics=[statistic],
        Dimensions=[{'Name': 'InstanceId', 'Value': id}]
    )

    net_out_stats = []

    for point in network_out['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute / 60
        net_out_stats.append([time, point['Sum']])

        net_out_stats = sorted(net_out_stats, key=itemgetter(0))

    return render_template("ec2_examples/view.html", title="Instance Info",
                           instance=instance,
                           cpu_stats=cpu_stats,
                           net_in_stats=net_in_stats,
                           net_out_stats=net_out_stats)


@webapp.route('/ec2_examples/create', methods=['POST'])
# Start a new EC2 instance
def ec2_create():
    aws_session = boto3.Session(aws_access_key_id=config.AWS_KEY, aws_secret_access_key=config.AWS_SECRET)
    ec2 = aws_session.resource('ec2')

    new_instances = ec2.create_instances(ImageId=config.EC2_ami_id,
                                         MinCount=config.EC2_num_instances,
                                         MaxCount=config.EC2_num_instances,
                                         UserData=config.EC2_user_data,
                                         InstanceType=config.EC2_instance_type,
                                         KeyName=config.EC2_key_name,
                                         SubnetId=config.EC2_subnet_id,
                                         SecurityGroupIds=config.EC2_security_group_ids,
                                         Monitoring={'Enabled': config.EC2_monitoring},
                                         TagSpecifications=[{'ResourceType': 'instance', 'Tags': [
                                             {'Key': config.EC2_tagkey, 'Value': config.EC2_tagvalue}, ]}, ])

    for instance in new_instances:
        elb.elb_add_instance(instance.id)  # Add New Instance to ELB

    return redirect(url_for('ec2_list'))


@webapp.route('/ec2_examples/delete/<id>', methods=['POST'])
# Terminate a EC2 instance
def ec2_destroy(id):
    # create connection to ec2
    aws_session = boto3.Session(aws_access_key_id=config.AWS_KEY, aws_secret_access_key=config.AWS_SECRET)
    ec2 = aws_session.resource('ec2')

    del_instances = ec2.instances.filter(InstanceIds=[id])

    for instance in del_instances:
        elb.elb_remove_instance(instance.id)  # Remove Instance from ELB
        instance.terminate()  # Terminate Instance

    return redirect(url_for('ec2_list'))

@webapp.route('/ec2_examples/deleteAll/', methods=['POST'])
# Terminate all instances and clear S3 data
def delete_all_userdata():
    
    print("Deleting All User Data")
    # Open DB Connection
    cnx = mysql.connector.connect(user=config.DB_USER, password=config.DB_PASS, host=config.DB_HOST, database=config.DB_NAME)
    cursor = cnx.cursor()
    
    # Execute DB Setup Script
    try:
        cursor.execute("drop table images;")
        cursor.execute("drop table users;")
        cursor.execute("CREATE TABLE users (id INT NOT NULL AUTO_INCREMENT, username char(100) NOT NULL, passhash char(100) NOT NULL, passsalt char(100) NOT NULL, PRIMARY KEY (id)) ENGINE = InnoDB;")
        cursor.execute("CREATE TABLE images(userid INT, imagename char(200) NOT NULL, orig char(200) NOT NULL, redblueshift char(200) NOT NULL, grayscale char(200) NOT NULL, overexposed char(200) NOT NULL, INDEX par_ind (userid), FOREIGN KEY (userid) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE) ENGINE = InnoDB;")
        cnx.commit()
    except:
        cnx.rollback

    # Close db connection
    cursor.close()
    cnx.close()
    
    # Create an S3 client
    s3 = boto3.resource('s3', aws_access_key_id=config.AWS_KEY, aws_secret_access_key=config.AWS_SECRET)
    bucket = s3.Bucket(config.S3_ID)
    
    # Delete data in bucket
    bucket.objects.all().delete()

    return redirect(url_for('ec2_list'))

@webapp.route('/ec2_examples/scaling/', methods=['POST'])
def scaling_modified():
    
    # Get User Data
    newUpperBound = request.form['upperBound']
    newlowerBound = request.form['lowerBound']
    newScaleUp = request.form['scaleUp']
    newScaleDown = request.form['scaleDown']

    update_prefix = "UPDATE autoscale SET "
    update_suffix = " WHERE id = 1"
    update_entry  = []
    
    # Update Parameters Check
    if newUpperBound:
        if not (newUpperBound.isdigit()):
            flash ("Upper Bound %s is not a valid number. Entry was not updated." % (newUpperBound))
        elif (int (newUpperBound) > 100 or int(newUpperBound) < 0):
            flash ("Upper Bound %s must be between 0-100. Entry was not updated." % (newUpperBound))
        else:
            update_entry.append ("upper_bound = " + newUpperBound)
    if newlowerBound:
        if not (newlowerBound.isdigit()):
            flash ("Lower Bound %s is not a valid  number. Entry was not updated." % (newlowerBound))
        elif (int (newlowerBound) > 100 or int(newlowerBound) < 0):
            flash ("Lower Bound %s must be between 0-100. Entry was not updated." % (newlowerBound))
        else: 
            update_entry.append ("lower_bound = " + newlowerBound)
    if newScaleUp:
        if not (newScaleUp.isdigit()):
            flash ("Scale Up %s is not a valid number. Entry was not updated." % (newScaleUp))
        elif (int(newScaleUp) < 1 or int(newScaleUp) > 10):
            flash ("Scale Up %s must be between 1-10. Entry was not updated." % (newScaleUp))
        else: 
            update_entry.append ("scale_up = " + newScaleUp)
    if newScaleDown:
        if not (newScaleDown.isdigit()):
            flash ("Scale Down %s is not a valid number. Entry was not updated." % (newScaleDown))
        elif (int(newScaleDown) < 1 or int(newScaleDown) > 10):
            flash ("Scale Down %s must be between 1-10. Entry was not updated." % (newScaleDown))
        else:
            update_entry.append("scale_down = " + newScaleDown)

    # Open DB Connection
    cnx    = mysql.connector.connect(user=config.DB_USER, password=config.DB_PASS, host=config.DB_HOST, database=config.DB_NAME)
    cursor = cnx.cursor()
    
    # Update Fields that were valid
    for update_middle in update_entry:
        update_command = update_prefix + update_middle + update_suffix
        try:
            cursor.execute(update_command)
            cnx.commit()
        except:
            cnx.rollback()                                            	                                                                                                                            
    # Query DB for Autoscale settings
    cursor.execute("SELECT scale,upper_bound,lower_bound,scale_up,scale_down FROM autoscale WHERE id = 1")   
    auto_scale_data = cursor.fetchall()
                                                                                                                                 
    if (len(auto_scale_data) == 0):
        flash ("Database is missing autoscale data")
                                                                                                                                 
    for scale,upper_bound,lower_bound,scale_up,scale_down in auto_scale_data:
        AUTO_scale       = scale
        AUTO_upper_bound = upper_bound
        AUTO_lower_bound = lower_bound
        AUTO_scale_up    = scale_up
        AUTO_scale_down  = scale_down
                                                                                                                                 
    # Close DB Connection
    cursor.close()
    cnx.close()

    return redirect(url_for('ec2_list'))

@webapp.route('/ec2_examples/configscaling', methods=['POST'])
def config_scaling():
    print("#configscaling")
    newautoScaling = request.form['autoScaling']

    #TODO add method to change auto scaling - Change DB
    if newautoScaling == "ON":
        scaleStatus = "ON"
        print("auto scaling on")
    if newautoScaling =="OFF" :
        scaleStatus = "OFF"
        print("auto scaling off")

    return redirect(url_for('ec2_list'))

