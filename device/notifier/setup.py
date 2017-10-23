from setuptools import setup, find_packages
from codecs import open
from os import path

setup(
   name="AwsIotNotifierThing",
   version="1.0.0",
   description="AWS IoT thing to play audio notifications",
   author="Ben Lilley",
   author_email="foo@foo.com",
   license="MIT",
   url="",
   classifiers=[
      'Development Status :: 3 - Alpha',
      'License :: OSI Approved :: MIT License',
      'Programming Language :: Python :: 3',
   ],
   py_modules=["AwsIotNotifierThing"],
   data_files=[('audio', ['chime.wav'])],
   install_requires=['boto3', 'simpleaudio'],
)
