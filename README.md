# Lookout

Lookout is an intelligent camera based on a Raspberry Pi (with camera module) and AWS.

A detailed blog series can be found on the 2412labs blog at https://2412labs.com/lookout/aws/raspi/2017/10/23/lookout-smart-aws-camera-part1-intro.html.

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
    * An AWS IoT thing (for the camera)
    * Certs for the AWS IoT thing
    * aws credentials in ~/.aws
2.  Get the code:
```bash
git clone https://github.com/2412labs/lookout.git
cd lookout/device/camera
sudo python3 setup.py install
```
3.  Configure the example code - add your values to conf.json:
```bash
cd lookout/device/camera/example
cp -r YOUR_THING_CERTS/ certs/
cp conf_example.json conf.json
vi conf.json
```
4.  Run `python3 -u cameraThingExample.py -c conf.json`
