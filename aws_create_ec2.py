#!/usr/bin/env python3

import argparse
import boto3
import os
from operator import itemgetter

parser = argparse.ArgumentParser()

parser.add_argument('-r','--region', action='store', dest='region', type=str,
                    help='AWS Region. Use like: -r ap-southeast-1', default='us-east-1')
parser.add_argument('-a','--ami', action='store', dest='ami_filter', type=str,
                    help='AWS AMI. Use like: -a amzn2-ami-hvm-2.0.????????-x86_64-gp2', default='amzn2-ami-hvm-2.0.????????-x86_64-gp2')
parser.add_argument('-t','--type', action='store', dest='type', type=str,
                    help='AWS instance type. Use like: -t t2.nano', default='t2.micro')
parser.add_argument('-n','--num', action='store', dest='num', type=int,
                    help='number of ec2 instances. Use like: -n 2', default=1)
arg = parser.parse_args()

# variables
aws_region = arg.region
aws_az1 = arg.region + "a"
aws_az2 = arg.region + "b"
vpc_cidr = "10.0.0.0/16"
public_subnet_cidr = "10.0.1.0/24"
private_subnet_cidr = "10.0.2.0/24"
source_cidr = '0.0.0.0/0'
fp = open('userdata.txt')
user_data_content = fp.read()

#initialize boto3 ec2 client and resource
ec2_resource = boto3.resource('ec2', aws_region)
ec2_client = boto3.client('ec2', aws_region)
 
# get the latest AMI ID for Amazon Linux 2
ec2_ami_ids = ec2_client.describe_images(
    Filters=[{'Name':'name','Values':[arg.ami_filter]},{'Name':'state','Values':['available']}],
    Owners=['amazon']
)
image_details = sorted(ec2_ami_ids['Images'],key=itemgetter('CreationDate'),reverse=True)
ec2_ami_id = image_details[0]['ImageId']

sg_group_name = 'myvpc_security_group'
response = ec2_client.describe_security_groups(
    Filters=[
        dict(Name='group-name', Values=[sg_group_name])
    ]
)
sg_group_id = response['SecurityGroups'][0]['GroupId']

public_subnet_id = list(ec2_resource.subnets.filter(Filters=filters))

#--------------------Create-Ec2-Instance---------------------------
# create an ec2 instance
def ec2_instance_create():
    ec2_instance = ec2_resource.create_instances(
        ImageId=ec2_ami_id,
        InstanceType=arg.type,
        KeyName='my_keypair',
        Monitoring={'Enabled':False},
        SecurityGroupIds=[sg_group_id],
        SubnetId=public_subnet_id,
        UserData=user_data_content,
        MaxCount=1,
        MinCount=1,
        #PrivateIpAddress='10.0.1.10'
    )
    ec2_instance_id = ec2_instance[0].id
    print('Creating EC2 instance')
    
    #wait untill the ec2 is running
    waiter = ec2_client.get_waiter('instance_running')
    waiter.wait(InstanceIds=[ec2_instance_id])
    print('EC2 Instance created successfully with ID: ' + ec2_instance_id)
    
    ec2_client.create_tags(Resources=[ec2_instance_id], Tags=[{'Key': 'Name','Value': 'myvpc_ec2_instance'}])
    
    # print instance dns name
    ec2_instance = ec2_client.describe_instances(
        Filters=[{'Name': 'tag:Name','Values': ['myvpc_ec2_instance']},
        {'Name': 'instance-state-name','Values': ['running']}]
    )
    ec2_public_dns_name = ec2_instance["Reservations"][0]["Instances"][0]["PublicDnsName"]
    print('instance URL: ' + ec2_public_dns_name)

if __name__ == '__main__':
    for _ in range(arg.num):
        ec2_instance_create()