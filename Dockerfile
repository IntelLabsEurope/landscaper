# Base Image for Landscaper Docker Deployment

FROM ubuntu:16.04

RUN apt-get update && apt-get install -y git python python-pip python-dev python-pycurl libssl-dev libcurl4-openssl-dev netcat curl

ADD ./ /landscaper/

# Set the working directory to /app
WORKDIR /landscaper
RUN $WORKDIR

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt
