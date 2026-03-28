# Homebrew formula for fnsvr
# To publish: copy to madho/homebrew-fnsvr tap repo
# User installs via: brew tap madho/fnsvr && brew install fnsvr

class Fnsvr < Formula
  include Language::Python::Virtualenv

  desc "Local-first Gmail scanner that catches financial emails you can't afford to miss"
  homepage "https://github.com/madho/fnsvr"
  url "https://pypi.io/packages/source/f/fnsvr/fnsvr-0.1.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"fnsvr", "--help"
  end
end
