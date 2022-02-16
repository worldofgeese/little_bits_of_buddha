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

        # DON'T FORGET TO PUT YOUR PACKAGE NAME HERE, REMOVING `throw`
        packageName = "lbob";

      in {
        packages.${packageName} = app;

        defaultPackage = self.packages.${system}.${packageName};

        packages.container = pkgs.dockerTools.streamLayeredImage {
          name = "lbob";
          contents = [
            self.packages.${system}.${packageName}
            pkgs.bash
            pkgs.coreutils
            pkgs.which
          ];
          config.Cmd = [ "lbob" ];
        };

        devShell = with pkgs;
          pkgs.mkShell {
            buildInputs = [
              python3
              poetry
              (python3.withPackages
                (ps: with ps; [ flask isort pyflakes nose pytest black ]))
              nodePackages.pyright # Type checker for the Python language
            ];
          };
      });
}
