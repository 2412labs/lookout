# Lookout

Lookout monitors a video stream for movement and uses AWS Rekognition to identify vehicles and people.  If people are detected, Lookout attempts to identify them using facial recognition.

IoT connected devices receive notifications and can take appropriate actions (tell you a car is in your driveway, tell you who is at your front door, greet a visitor, automatically open a door, etc.).

Cloud-based services can also act on notifications, like sending a text if you get a visitor when you are not home.

# How does it work

Video is gathered by a Raspberry Pi with a camera module. The Raspberry Pi utilizes video-based motion detection algorithms to detect potential movement events.  Moving objects are cropped from images and pushed to an S3 bucket.  An iot-data mqtt message containing detailed information about the motion event is also sent to a Lambda method.

The Lambda uses Rekognition to determine if the cropped image contains a vehicle or person, if it does an initial iot-data message is published indicating what objects are in the image.

If the image contained a person, Rekognition is used again to attempt a facial match.  If a known face is matched, a followup iot-data message is sent with the person's name.  If the image contains a face that is not known to Lookout, the face information is saved so that a user can choose to identify the face and add it to the Rekognition collection for future matching.

Any IoT connected device can receive and act on notifications.  This project demonstrates a "notifier" device that plays an alert sound when a vehicle or person is detected, and uses AWS Polly synthesized speech to announce a person if their face is matched.

# Alexa Skill

Notifications are kept in a DynamoDb table for 7 days.  The Lookout Alexa skill can provide information about recent alerts.

AWS has recently released Alexa push notifications for the device SDK so that device makers can prepare for the push notification feature.  When push notifications are added to the Alexa Skills Kit, the Lookout skill can be updated to receive push notifications from iot-data messages (exactly how is unknown at this time).
