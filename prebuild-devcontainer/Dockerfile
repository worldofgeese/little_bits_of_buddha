FROM alpine:3

# setting up devbox user
ENV DEVBOX_USER=devbox
RUN adduser -h /home/$DEVBOX_USER -D -s /bin/bash $DEVBOX_USER
RUN addgroup sudo
RUN addgroup $DEVBOX_USER sudo
RUN echo " $DEVBOX_USER      ALL=(ALL:ALL) NOPASSWD: ALL" >> /etc/sudoers

# copy Garden to the image from Garden's Alpine image as the devbox user
COPY --from=gardendev/garden:0.12.52-0 --chown=$DEVBOX_USER /garden /garden
RUN ln -s /garden/garden /usr/local/bin/garden

# installing dependencies
RUN apk add --no-cache bash binutils git libstdc++ xz sudo rsync

USER $DEVBOX_USER

# installing devbox
RUN wget --quiet --output-document=/dev/stdout https://get.jetpack.io/devbox | bash -s -- -f
RUN chown -R "${DEVBOX_USER}:${DEVBOX_USER}" /usr/local/bin/devbox

# nix installer script
RUN wget --quiet --output-document=/dev/stdout https://nixos.org/nix/install | sh -s -- --no-daemon
RUN . ~/.nix-profile/etc/profile.d/nix.sh
# updating PATH
ENV PATH="/home/${DEVBOX_USER}/.nix-profile/bin:/home/${DEVBOX_USER}/.devbox/nix/profile/default/bin:${PATH}"

WORKDIR /code
RUN sudo chown $DEVBOX_USER:root /code
COPY devbox.json devbox.json
RUN devbox shell -- echo "Installing packages"
CMD ["devbox", "shell"]
