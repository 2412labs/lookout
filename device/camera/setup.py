from setuptools import setup, find_packages
from codecs import open
from os import path

setup(
   name="AwsIotCameraThing",
   version="1.0.0",
   description="AWS IoT Camera Thing",
   author="Ben Lilley",
   author_email="foo@foo.com",
   license="MIT",
   url="",
   classifiers=[
      'Development Status :: 3 - Alpha',
      'License :: OSI Approved :: MIT License',
      'Programming Language :: Python :: 3',
   ],
   py_modules=["AwsIotCameraThing"],
   packages=find_packages(),
   install_requires=['picamera', 'numpy'],
)
