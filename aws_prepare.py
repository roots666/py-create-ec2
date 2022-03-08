#!/usr/bin/env python3

import argparse
import boto3
import os
from operator import itemgetter

parser = argparse.ArgumentParser()

parser.add_argument('-r','--region', action='store', dest='region', type=str,
                    help='AWS Region. Use like: -r ap-southeast-1', default='us-east-1')
arg = parser.parse_args()

# variables
aws_region = arg.region
aws_az1 = arg.region + "a"
aws_az2 = arg.region + "b"
vpc_cidr = "10.0.0.0/16"
public_subnet_cidr = "10.0.1.0/24"
private_subnet_cidr = "10.0.2.0/24"
source_cidr = '0.0.0.0/0'

#initialize boto3 ec2 client and resource
ec2_resource = boto3.resource('ec2', aws_region)
ec2_client = boto3.client('ec2', aws_region)
 
#-------------------Create-VPC-------------------------------
vpc = ec2_resource.create_vpc(CidrBlock=vpc_cidr)
vpc.wait_until_available()
print('VPC created successfully with VPC ID: ' + vpc.id)
 
# modify vpc to enable dns hostname
vpc.modify_attribute(EnableDnsHostnames={'Value':True})

#--------------------Create-Subnets---------------------------
# create public subnet
public_subnet = vpc.create_subnet(AvailabilityZone=aws_az1,CidrBlock=public_subnet_cidr)
ec2_client.modify_subnet_attribute(MapPublicIpOnLaunch={'Value': True},SubnetId=public_subnet.id)
print('Public Subnet created successfully with SUBNET ID: ' + public_subnet.id)
 
# create a private subnet
private_subnet = vpc.create_subnet(AvailabilityZone=aws_az2,CidrBlock=private_subnet_cidr)
print('Private Subnet created successfully with SUBNET ID: ' + private_subnet.id)

#-------------------InternetGateway-------------------------
# create an internet gateway and attach to the vpc
internet_gateway = ec2_resource.create_internet_gateway()
internet_gateway.attach_to_vpc(VpcId=vpc.id)
print('Internet Gateway created successfully with GATEWAY ID: ' + internet_gateway.id)

#---------------------RouteTable------------------------------
# create a public route table and assosiate to public subnet
public_route_table = ec2_resource.create_route_table(VpcId=vpc.id)
public_route_table.associate_with_subnet(SubnetId=public_subnet.id)

# create route to Internet Gateway in public route table
public_route = ec2_client.create_route(RouteTableId=public_route_table.id,DestinationCidrBlock=source_cidr,GatewayId=internet_gateway.id)
print('Public Route Table with ID ' + public_route_table.id + ' created successfully')
 
# create a private route table and assosiate to private subnet
private_route_table = ec2_resource.create_route_table(VpcId=vpc.id)
private_route_table.associate_with_subnet(SubnetId=private_subnet.id)
print('Private Route Table with ID ' + private_route_table.id + ' created successfully')

#------------------Create-SecurityGroup---------------------------
# create a security group
security_group = ec2_resource.create_security_group(GroupName='myvpc_security_group',Description='Used by Me',VpcId= vpc.id)
 
# create ssh ingress rules
ec2_client.authorize_security_group_ingress(GroupId=security_group.id,IpProtocol='tcp',FromPort=22,ToPort=22,CidrIp=source_cidr)
print('Security Group with ID ' + security_group.id + ' created successfully')
 
# create a key pair
try:
    outfile = open('my_keypair.pem','w')
except IOError as e:
    print(u'IOError')
else:
    keypair = ec2_client.create_key_pair(KeyName='my_keypair')
    keyval = keypair['KeyMaterial']
    outfile.write(keyval)
    outfile.close()
    os.chmod('my_keypair.pem', 400)
    print('Key Pair my_keypair created successfully')

# create tags
vpc.create_tags(Tags=[{"Key": "Name", "Value": "myvpc"}])
public_subnet.create_tags(Tags=[{"Key": "Name", "Value": "myvpc_public_subnet"}])
private_subnet.create_tags(Tags=[{"Key": "Name", "Value": "myvpc_private_subnet"}])
internet_gateway.create_tags(Tags=[{"Key": "Name", "Value": "myvpc_internet_gateway"}])
public_route_table.create_tags(Tags=[{"Key": "Name", "Value": "myvpc_public_route_table"}])
private_route_table.create_tags(Tags=[{"Key": "Name", "Value": "myvpc_private_route_table"}])
security_group.create_tags(Tags=[{"Key": "Name", "Value": "myvpc_security_group"}])

