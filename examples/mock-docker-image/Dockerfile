FROM public.ecr.aws/ubuntu/ubuntu:jammy as base

RUN apt update && \
    apt install -y --no-install-recommends hello

FROM public.ecr.aws/ubuntu/ubuntu:jammy
COPY --from=base /usr/bin/hello /usr/bin/hello

ENTRYPOINT ["hello"]
CMD ["-t"]
