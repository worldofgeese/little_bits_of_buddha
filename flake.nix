{
  description = "Application packaged using poetry2nix";

  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs";
  inputs.poetry2nix.url = "github:nix-community/poetry2nix";

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    {
      # Nixpkgs overlay providing the application
      overlay = nixpkgs.lib.composeManyExtensions [
        poetry2nix.overlay
        (final: prev: {
          # The application
          myapp = prev.poetry2nix.mkPoetryApplication { projectDir = ./.; };
        })
      ];
    } // (flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ self.overlay ];
        };
      in {
        apps = { myapp = pkgs.myapp; };

        defaultApp = pkgs.myapp;

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
      }));
}
