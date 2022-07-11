{
  description = "NixOS simple deploy";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
  flake-utils.lib.eachDefaultSystem (
    system:
    let
      pkgs = import nixpkgs {
        inherit system;
      };
    in
    {
      # packages.homematic-homekit =
      #   pkgs.python3.pkgs.buildPythonApplication rec {
      #     pname = "homematic-homekit";
      #     version = "0.1";
      #
      #     src = ./.;
      #
      #     propagatedBuildInputs = with pkgs.python3Packages; [
      #       hap-python
      #     ];
      #   };

      devShell = let
        my-python = pkgs.python3;
        python-with-my-packages = my-python.withPackages (ps: with ps; [
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
