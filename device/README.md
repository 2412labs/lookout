# Devices

This folder contains code that runs on IoT connected devices.  

The camera device utilizes video-based motion detection to feed motion event data to Lookout. The code is designed for the Raspberry Pi camera and was tested with a Raspberry Pi3 and camera modules v1 and v2.

The notifier device receives mqtt messages and announces events with alert tones and speech synthesized by AWS Polly.  The notifier code can run on any device that supports Python and the AWSIoTPythonSDK module.

IoT devices are logical devices, so if physical location allows the same Raspberry Pi unit can act as the camera and notifier devices simultaneously.

# Camera Setup

todo

# Notifier Setup

todo
