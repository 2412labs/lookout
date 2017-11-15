# Lookout

Lookout is an intelligent camera based on a Raspberry Pi (with camera module) and AWS.

Detailed information and configuration steps can be found on the 2412labs blog at https://2412labs/lookout/aws/raspi/2017/10/23/lookout-smart-aws-camera-part1-intro.html.

# TL;DR - install aws stack:

1.  Clone the lookout repo.
```bash
git clone https://github.com/2412labs/lookout.git
cd lookout
```
2.  Edit the Makefile (`vi Makefile`) and update these variables with your S3 bucket and region:
```bash
BUCKET := YOUR-BUCKET
REGION := us-east-1
```
3.  Run the release target - this will package, deploy, copy test images and faces, and index faces from img/faces (you can add your own jpg files to this folder for facial recognition and announce by name):
```bash
make release
```

# TL;DR - raspi camera

1.  Requirements:
    * Python3
    * AWSIoTPythonSDK, Boto3, OpenCV, Numpy and picamera modules
    * aws credentials in ~/.aws
2.  
