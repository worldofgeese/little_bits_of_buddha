FROM gitpod/workspace-base:latest

USER root
RUN addgroup --system nixbld \
  && adduser gitpod nixbld \
  && for i in $(seq 1 30); do useradd -ms /bin/bash nixbld$i &&  adduser nixbld$i nixbld; done \
  && mkdir -m 0755 /nix && chown gitpod /nix \
  && mkdir -p /etc/nix && echo 'sandbox = false' > /etc/nix/nix.conf

USER gitpod
ENV USER gitpod
WORKDIR /home/gitpod

# Step 2: Installing Nix
RUN touch .bash_profile \
 && curl https://nixos.org/releases/nix/nix-2.17.0/install | sh

RUN echo '. /home/gitpod/.nix-profile/etc/profile.d/nix.sh' >> /home/gitpod/.bashrc

# Install cachix
RUN . /home/gitpod/.nix-profile/etc/profile.d/nix.sh \
  && nix-env -iA cachix -f https://cachix.org/api/v1/install \
  && cachix use cachix

# Use unstable nixpkgs
RUN . /home/gitpod/.nix-profile/etc/profile.d/nix.sh \
  && nix-channel --add https://nixos.org/channels/nixpkgs-unstable unstable \
  && nix-channel --update \
  && nix-env -iA nixpkgs.nixUnstable

# Step 3: Installing devbox, direnv, and garden dependencies
RUN . /home/gitpod/.nix-profile/etc/profile.d/nix.sh \
  && nix-env -i git git-lfs rsync devbox direnv \
  && direnv hook bash >> /home/gitpod/.bashrc

WORKDIR /code
RUN sudo chown $USER:$USER /code
COPY --chown=$USER pyproject.toml .
COPY --chown=$USER src src
COPY --chown=$USER devbox.json devbox.json
COPY --chown=$USER devbox.lock devbox.lock

# Step 4: Installing your devbox project
RUN . /home/gitpod/.nix-profile/etc/profile.d/nix.sh \
  && devbox run -- echo "Installed Packages."

RUN . /home/gitpod/.nix-profile/etc/profile.d/nix.sh \
  && devbox shellenv --init-hook >> ~/.profile
# Step 5: Install garden
RUN curl -sL https://get.garden.io/install.sh | bash
ENV PATH=/home/$USER/.garden/bin:$PATH
