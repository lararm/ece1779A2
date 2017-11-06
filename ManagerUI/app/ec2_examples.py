from flask import render_template, redirect, url_for, request
from app import webapp

import boto3
from app import config
from datetime import datetime, timedelta
from operator import itemgetter
from app import elb
from app import cloudWatch
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

    # Add instance to elb
    # elb.elb_add_instance('i-010cee1c733265058')
    # Remove instance from elb
    # elb.elb_remove_instance('i-010cee1c733265058')

    #Test CloudWatch avgs
    workers_list = []
    for instance in instances:
        # filter db and mananger
        if (instance.id != config.DATABASE_ID and instance.id != config.MANAGER_ID):
             if(( instance.tags[0]['Value'] == 'A2WorkerNode' ) and (instance.state['Name'] != 'terminated')):
                workers_list.append(instance.id)

    return render_template("ec2_examples/list.html", title="EC2 Instances", instances=instances, buckets=buckets,
                           manager=config.MANAGER_ID,
                           database=config.DATABASE_ID)


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