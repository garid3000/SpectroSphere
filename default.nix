{
  pkgs ? import <nixpkgs> { },
}:

pkgs.mkShell {
  packages = [
    (pkgs.python3.withPackages (python-pkgs: [
      pkgs.pyright
      pkgs.ruff
      python-pkgs.dash
      python-pkgs.dash-bootstrap-components
      python-pkgs.numpy
      python-pkgs.opencv4
      python-pkgs.pillow
      python-pkgs.plotly
      python-pkgs.qrcode
      python-pkgs.pyserial
    ])
    )
  ];
}
