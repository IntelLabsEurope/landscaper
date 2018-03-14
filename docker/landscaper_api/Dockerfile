#Gunicorn docker file

FROM landscaper_base:latest

# Make port 9001 available to the world outside this container
EXPOSE 9001

# Define environment variable
ENV PYTHONPATH=/landscaper

WORKDIR landscaper/web
RUN echo $PYTHONPATH
CMD ["gunicorn", "-b", "0.0.0.0:9001", "-w", "2", "application:APP"]


