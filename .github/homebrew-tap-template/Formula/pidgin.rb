class Pidgin < Formula
  include Language::Python::Virtualenv

  desc "AI conversation research tool for studying emergent communication patterns"
  homepage "https://github.com/tensegrity-ai/pidgin"
  url "https://files.pythonhosted.org/packages/source/p/pidgin-ai/pidgin_ai-1.0.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"pidgin", "--version"
  end
end
