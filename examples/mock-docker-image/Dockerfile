FROM public.ecr.aws/ubuntu/ubuntu:jammy

RUN apt update && \
    apt install -y hello && \
    rm -fr /var/lib/apt/lists/*

ENTRYPOINT ["hello"]
CMD ["-t"]
