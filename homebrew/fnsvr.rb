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

  # Resource stanzas generated via: pip install homebrew-pypi-poet && poet fnsvr
  # SHA256 hashes are placeholders until PyPI publish. Regenerate with:
  #   poet fnsvr > resources.rb
  resource "click" do
    url "https://pypi.io/packages/source/c/click/click-8.1.7.tar.gz"
    sha256 "PLACEHOLDER_CLICK_SHA256"
  end

  resource "google-api-python-client" do
    url "https://pypi.io/packages/source/g/google-api-python-client/google-api-python-client-2.131.0.tar.gz"
    sha256 "PLACEHOLDER_GOOGLE_API_SHA256"
  end

  resource "google-auth-httplib2" do
    url "https://pypi.io/packages/source/g/google-auth-httplib2/google-auth-httplib2-0.2.0.tar.gz"
    sha256 "PLACEHOLDER_GOOGLE_AUTH_HTTPLIB2_SHA256"
  end

  resource "google-auth-oauthlib" do
    url "https://pypi.io/packages/source/g/google-auth-oauthlib/google-auth-oauthlib-1.2.0.tar.gz"
    sha256 "PLACEHOLDER_GOOGLE_AUTH_OAUTHLIB_SHA256"
  end

  resource "PyYAML" do
    url "https://pypi.io/packages/source/p/PyYAML/PyYAML-6.0.1.tar.gz"
    sha256 "PLACEHOLDER_PYYAML_SHA256"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"fnsvr", "--help"
  end
end
