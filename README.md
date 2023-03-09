# Little Bits of Buddha

<figure>
  <img src="https://us-east-1.linodeobjects.com/kinopio-uploads/wvF4LRNvUWaQyrINvklmE/little-bits-of-buddha-telegram-bot-logo--SNM.jpg" alt="A robotic monk with a wheel-maze for a head against a blue field" width="250" />
</figure>

[![Managed by PDM](https://img.shields.io/badge/pdm-managed-blueviolet)](https://pdm.fming.dev)
[![Built with Devbox](https://camo.githubusercontent.com/44007cdd3b58909b59b9d6ba003533cd620f85245a2aa4c84081e511b9c3b405/68747470733a2f2f6a65747061636b2e696f2f646576626f782f696d672f736869656c645f67616c6178792e737667)](https://jetpack.io/devbox/docs/contributor-quickstart/)

# What is Little Bits of Buddha?

Little Bits of Buddha is a Telegram bot that offers daily bits of Buddhist scriptures to its users.

## Quickstart

You can access Little Bits of Buddha at https://t.me/LittleBitsOfBuddhaBot.

## Developing

### Built With

![Python 3.11](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)
![FastAPI](https://img.shields.io/badge/fastapi-109989?style=for-the-badge&logo=FASTAPI&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)

### Prerequisites

- Install Garden with `curl -sL https://get.garden.io/install.sh | bash`
- Install Devbox with `curl -fsSL https://get.jetpack.io/devbox | bash`
- A registered user on https://gitlab.hansen.agency with permissions to contribute to the Little Bits of Buddha project
- A `$GITLAB_TOKEN` with the `api` and `write_repository` scopes generated at https://gitlab.hansen.agency/-/profile/personal_access_tokens or an [SSH key added to your account on this GitLab instance](https://gitlab.hansen.agency/-/profile/keys)
- A `$LOFT_ACCESS_KEY` generated by @worldofgeese granting access to this project's Kubernetes cluster

Contact @worldofgeese if you need help getting set up 😊

### Setting up Dev

This project does _not_ use a Python virtual environment you may be accustomed to if you've worked on Python projects before. Instead, this project makes use of the draft Python Enhancement Proposal (PEP) 582, which installs Python dependencies to a local project `__pypackages__` folder. We use PDM, a modern, standards-compliant Python package and dependency manager that ships with support for this PEP. More information can be found at [PDM's docs](https://pdm.fming.dev/latest/usage/pep582/).

In order to get started developing run the following in your shell from inside the project directory:

⚠️ **If you are using 1Password**: consider [using 1Password CLI to securely authenticate GitLab](https://developer.1password.com/docs/cli/shell-plugins/gitlab/) and to [generate your SSH key](https://docs.gitlab.com/ee/user/ssh.html#generate-an-ssh-key-pair-with-1password).

```shell
devbox shell
glab auth login -h gitlab.hansen.agency -t $GITLAB_TOKEN
glab repo clone worldofgeese/little_bits_of_buddha
cd little_bits_of_buddha
export TF_VAR_loft_access_key=$LOFT_ACCESS_KEY
```

Devbox will offer to install Nix if not already installed. `devbox shell` will install all other requirements into an isolated development environment and launch you into it.

Now run `garden deploy` when you're ready to deploy your app to your own private user namespace 🚀

Alternatively, open a cloud development environment in your browser with [Devbox Cloud](https://www.jetpack.io/devbox/docs/devbox_cloud/) _or_ open in [GitHub Codespaces](https://docs.github.com/en/codespaces/overview) by clicking their buttons below 👇.

[![Open In Devbox.sh](https://jetpack.io/img/devbox/open-in-devbox.svg)](https://devbox.sh/github.com/worldofgeese/little_bits_of_buddha)

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/codespaces/new?hide_repo_select=true&ref=main&repo=603759732&machine=standardLinux32gb&devcontainer_path=.devcontainer%2Fdevcontainer.json&location=WestEurope)

### Setting up your Editor

#### VS Code

If you use VS Code as your editor, please run `devbox shell` _before_ launching VS Code from your shell with `code .`. This ensures Devbox's shell variables are exported into your editor session. You may alternatively choose to use the [Dev Container](https://containers.dev/) this project ships with.

#### Emacs

For Emacs, this project ships with a `.envrc` file that can be used by the `envrc` package to auto-load a Devbox shell on navigating to the project. Instructions for use by Doom Emacs users can be found at the [docs page](https://docs.doomemacs.org/latest/modules/tools/direnv/). Other Emacs users can visit the [`envrc` GitHub repository](https://github.com/purcell/envrc).
