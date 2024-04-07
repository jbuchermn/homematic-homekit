{
  description = "HomeMatic HomeKit integration server";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";

    simplix.url = "github:jbuchermn/simplix";
    simplix.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, flake-utils, simplix }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };
      in
      {
        packages = {
          simplix = simplix.outputs.packages.${system}.simplix (hw: {
            withHost = false;
            userPkgs = with hw.pkgs-cross; [
              (python3.withPackages
                (ps: with ps; [
                  hap-python
                ]))
            ];
          });
        };

        devShell =
          let
            python-with-my-packages = pkgs.python3.withPackages (ps: with ps; [
              hap-python

              python-lsp-server
              (pylsp-mypy.overrideAttrs (old: { pytestCheckPhase = "true"; }))
              mypy
            ]);
          in
          pkgs.mkShell {
            buildInputs = [ python-with-my-packages ];
          };
      }
    );
}
