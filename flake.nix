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
              python39Packages.isort # A Python utility / library to sort Python imports
              python39Packages.pyflakes # A simple program which checks Python source files for errors
              python39Packages.nose # A unittest-based testing framework for python that makes writing and running tests easier
              python39Packages.pytest # Framework for writing tests
              nodePackages.pyright # Type checker for the Python language
              python39Packages.black # The uncompromising Python code formatter
            ];
          };
      }));
}
