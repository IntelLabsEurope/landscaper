# Use landscaper base image
FROM landscaper_base:latest

RUN echo $WORKDIR
# Set PYTHONPATH as root directory
ENV PYTHONPATH .

WORKDIR /landscaper

# Start.sh waits for neo4j to run the landscaper.py
ADD start.sh /start.sh
CMD ["/start.sh"]





