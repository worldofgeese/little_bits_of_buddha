{
  description = "Application packaged using poetry2nix";

  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs";
  inputs.poetry2nix.url = "github:nix-community/poetry2nix";

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        app = pkgs.poetry2nix.mkPoetryApplication { projectDir = ./.; };

        packageName = "lbob";

        env = pkgs.poetry2nix.mkPoetryEnv { projectDir = ./.; };
      in {
        packages.${packageName} = app;

        defaultPackage = self.packages.${system}.${packageName};

        packages.container = pkgs.dockerTools.streamLayeredImage {
          name = "lbob";
          tag = self.packages.${system}.${packageName}.version;
          contents = [ self.packages.${system}.${packageName} ];
          created = "now";
          config = {
            ExposedPorts."5000/tcp" = { };
            Cmd = [ "lbob" ];
          };
        };

        devShell = with pkgs;
          pkgs.mkShell {
            buildInputs = [
              env
              python3
              poetry
              (python3.withPackages (ps:
                with ps; [
                  flask
                  isort
                  pyflakes
                  pytest
                  pytest-mock
                  black
                  debugpy
                  ipython
                ]))
              nodePackages.pyright # Type checker for the Python language
              openshift
            ];
          };
      });
}
