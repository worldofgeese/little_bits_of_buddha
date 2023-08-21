FROM mcr.microsoft.com/devcontainers/base:buster

# Step 1: Installing dependencies
RUN apt-get update \
 && apt-get -y install bash binutils git gnupg2 xz-utils wget sudo rsync

USER vscode

# Step 2: Installing Nix
RUN wget --quiet --output-document=/dev/stdout https://nixos.org/nix/install | sh -s -- --no-daemon
RUN . ~/.nix-profile/etc/profile.d/nix.sh
ENV PATH="/home/vscode/.nix-profile/bin:$PATH"

# Step 3: Installing devbox
RUN wget --quiet --output-document=/dev/stdout https://get.jetpack.io/devbox | bash -s -- -f

WORKDIR /code
RUN sudo chown vscode:root /code
COPY --chown=vscode devbox.json devbox.json
COPY --chown=vscode devbox.lock devbox.lock

# Step 4: Installing your devbox project

RUN devbox run -- echo "Installed Packages."

RUN devbox shellenv --init-hook >> ~/.profile

# Step 5: Install garden
RUN curl -sL https://get.garden.io/install.sh | bash