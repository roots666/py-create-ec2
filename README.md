# py-create-ec2
Create ec2 vpc, igw, sg, rt, instance with python boto3

# How to use:
- Clone this repo.
- pip3 install -r requirements.txt # better to use virtual env though

- Running script without settings, you get help:
```bash
./aws_create_ec2.py -h
usage: aws_create_ec2.py [-h] [-r REGION] [-a AMI_FILTER] [-t TYPE] [-n NUM]

optional arguments:
  -h, --help            show this help message and exit
  -r REGION, --region REGION
                        AWS Region. Use like: -r ap-southeast-1
  -a AMI_FILTER, --ami AMI_FILTER
                        AWS AMI. Use like: -a amzn2-ami-hvm-2.0.????????-x86_64-gp2
  -t TYPE, --type TYPE  AWS instance type. Use like: -t t2.nano
  -n NUM, --num NUM     number of ec2 instances. Use like: -n 2
```