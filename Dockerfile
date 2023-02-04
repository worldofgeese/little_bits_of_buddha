FROM alpine
RUN apk add --no-cache bash tar curl && \
    curl -sSL https://nixpacks.com/install.sh | bash

COPY builder/* /
