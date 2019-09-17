# Use an official Python runtime as a parent image
FROM continuumio/miniconda3

WORKDIR /wshds

RUN apt-get update && apt-get install -y gdb

COPY environment.yml /wshds
RUN conda env create -f /wshds/environment.yml
ENV PATH /opt/conda/envs/wshdsenv/bin:$PATH
RUN /bin/bash -c "source activate wshdsenv"

COPY src /wshds/src
