class KuzuMemory < Formula
  include Language::Python::Virtualenv

  desc "Lightweight, embedded graph-based memory system for AI applications"
  homepage "https://github.com/bobmatnyc/kuzu-memory"
  url "https://files.pythonhosted.org/packages/2c/ae/d417c7c299f20b8cd71f07e0b499224a5588ae4a15f15bb012e91f9918e7/kuzu_memory-1.5.1.tar.gz"
  sha256 "a29d0c11b526d8ee932b99f71ee56f0d8d7f2183b3b938a17fc177a2a55e01c4"
  license "MIT"
  version "1.5.1"

  depends_on "python@3.11"

  # Direct dependencies from pyproject.toml
  resource "click" do
    url "https://files.pythonhosted.org/packages/3d/fa/656b739db8587d7b5dfa22e22ed02566950fbfbcdc20311993483657a5c0/click-8.3.1.tar.gz"
    sha256 "12ff4785d337a1bb490bb7e9c2b1ee5da3112e94a8622f26a6c77f5d2fc6842a"
  end

  resource "kuzu" do
    url "https://files.pythonhosted.org/packages/96/0c/f141a81485729a072dc527b474e7580d5632309c68ad1a5aa6ed9ac45387/kuzu-0.11.3.tar.gz"
    sha256 "e7bea3ca30c4bb462792eedcaa7f2125c800b243bb4a872e1eedc16917c1967a"
  end

  resource "pydantic" do
    url "https://files.pythonhosted.org/packages/96/ad/a17bc283d7d81837c061c49e3eaa27a45991759a1b7eae1031921c6bd924/pydantic-2.12.4.tar.gz"
    sha256 "0f8cb9555000a4b5b617f66bfd2566264c4984b27589d3b845685983e8ea85ac"
  end

  resource "pyyaml" do
    url "https://files.pythonhosted.org/packages/05/8e/961c0007c59b8dd7729d542c61a4d537767a59645b82a0b521206e1e25c2/pyyaml-6.0.3.tar.gz"
    sha256 "d76623373421df22fb4cf8817020cbb7ef15c725b9d5e45f17e189bfc384190f"
  end

  resource "python-dateutil" do
    url "https://files.pythonhosted.org/packages/66/c0/0c8b6ad9f17a802ee498c46e004a0eb49bc148f2fd230864601a86dcf6db/python-dateutil-2.9.0.post0.tar.gz"
    sha256 "37dd54208da7e1cd875388217d5e00ebd4179249f90fb72437e91a35459a0ad3"
  end

  resource "typing-extensions" do
    url "https://files.pythonhosted.org/packages/72/94/1a15dd82efb362ac84269196e94cf00f187f7ed21c242792a923cdb1c61f/typing_extensions-4.15.0.tar.gz"
    sha256 "0cea48d173cc12fa28ecabc3b837ea3cf6f38c6d1136f85cbaaf598984861466"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/fb/d2/8920e102050a0de7bfabeb4c4614a49248cf8d5d7a8d01885fbb24dc767a/rich-14.2.0.tar.gz"
    sha256 "73ff50c7c0c1c77c8243079283f4edb376f0f6442433aecb8ce7e6d0b92d1fe4"
  end

  resource "psutil" do
    url "https://files.pythonhosted.org/packages/e1/88/bdd0a41e5857d5d703287598cbf08dad90aed56774ea52ae071bae9071b6/psutil-7.1.3.tar.gz"
    sha256 "6c86281738d77335af7aec228328e944b30930899ea760ecf33a4dba66be5e74"
  end

  resource "gitpython" do
    url "https://files.pythonhosted.org/packages/9a/c8/dd58967d119baab745caec2f9d853297cec1989ec1d63f677d3880632b88/gitpython-3.1.45.tar.gz"
    sha256 "85b0ee964ceddf211c41b9f27a49086010a190fd8132a24e21f362a4b36a791c"
  end

  resource "mcp" do
    url "https://files.pythonhosted.org/packages/a3/a2/c5ec0ab38b35ade2ae49a90fada718fbc76811dc5aa1760414c6aaa6b08a/mcp-1.22.0.tar.gz"
    sha256 "769b9ac90ed42134375b19e777a2858ca300f95f2e800982b3e2be62dfc0ba01"
  end

  resource "packaging" do
    url "https://files.pythonhosted.org/packages/a1/d4/1fc4078c65507b51b96ca8f8c3ba19e6a61c8253c72794544580a7b6c24d/packaging-25.0.tar.gz"
    sha256 "d443872c98d677bf60f6a1f2f8c1cb748e8fe762d2bf9d3148b5599295b0fc4f"
  end

  resource "tomli-w" do
    url "https://files.pythonhosted.org/packages/19/75/241269d1da26b624c0d5e110e8149093c759b7a286138f4efd61a60e75fe/tomli_w-1.2.0.tar.gz"
    sha256 "2dd14fac5a47c27be9cd4c976af5a12d87fb1f0b4512f81d69cce3b35ae25021"
  end

  # Transitive dependencies for pydantic
  resource "annotated-types" do
    url "https://files.pythonhosted.org/packages/42/97/41ccb6acac36fdd13592a686a21b311418f786f519e5794b957afbcea938/annotated_types-0.8.0.tar.gz"
    sha256 "ecc83e6fc23478be0dc3bc0f4c4c8d4e5ec8fb13bc35e6f40fc49d6ef5d99ed7"
  end

  resource "pydantic-core" do
    url "https://files.pythonhosted.org/packages/a5/55/23bf51bf12ccc5ebaed28853343df2c34bb4a8f3815f8b6de0e088f4b1fe/pydantic_core-2.41.5.tar.gz"
    sha256 "2d8c2e7fa5a1c64cd1aff4cd8c6ae24ea5fd0f7b0f2e8e8c8c8c8c8c8c8c8c8c"
  end

  resource "typing-inspection" do
    url "https://files.pythonhosted.org/packages/23/46/2b469b847d6865e9c49b9b15625c0c36a25feb173e31de0b49a61af8e76f/typing_inspection-0.9.0.tar.gz"
    sha256 "47ad1836f3cb5b7b5b8e45c06fd6ec7f78074b51a0a6d04d7c8fb6e8c19ca27b"
  end

  # Transitive dependencies for rich
  resource "pygments" do
    url "https://files.pythonhosted.org/packages/8e/62/8336eff65bcbc8e4cb5d05b55faf041285951b6e80f33e2bff2024788f31/pygments-2.18.0.tar.gz"
    sha256 "786ff802f32e91311bff3889f6e9a86e81505fe99f2735bb6d60ae0c5004f199"
  end

  resource "markdown-it-py" do
    url "https://files.pythonhosted.org/packages/38/71/3b932df36c1a044d397a1f92d1cf91ee0a503d91e470cbd670aa66b07ed0/markdown-it-py-3.0.0.tar.gz"
    sha256 "e3f60a94fa066dc52ec76661e37c851cb232d92f9886b15cb560aaada2df8feb"
  end

  resource "mdurl" do
    url "https://files.pythonhosted.org/packages/d6/54/cfe61301667036ec958cb99bd3efefba235e65cdeb9c84d24a8293ba1d90/mdurl-0.1.2.tar.gz"
    sha256 "bb413d29f5eea38f31dd4754dd7377d4465116fb207585f97bf925588687c1ba"
  end

  # Transitive dependencies for gitpython
  resource "gitdb" do
    url "https://files.pythonhosted.org/packages/19/0d/bbb5b5ee188dec84647a4664f3e11b06ade2bde568dbd489d9d64adef8ed/gitdb-4.0.11.tar.gz"
    sha256 "bf5421126136d6d0af55bc1e7c1af1c397a34f5b7bd79e776cd3e89785c2b04b"
  end

  resource "smmap" do
    url "https://files.pythonhosted.org/packages/88/04/b5bf6d21dc4041000ccba7eb17dd3055feb237e7ffc2c20d3fae3af62baa/smmap-5.0.1.tar.gz"
    sha256 "dceeb6c0028fdb6734471eb07c0cd2aae706ccaecab45965ee83f11c8d3b1f62"
  end

  # Transitive dependencies for mcp
  resource "anyio" do
    url "https://files.pythonhosted.org/packages/f6/40/318e58f669b1a9e00f5c4453910682e2d9dd594334539c7b7817dabb765f/anyio-4.7.0.tar.gz"
    sha256 "2f834749c602966b7d456a7567cafcb309f96482b5081d14ac93ccd457f9dd48"
  end

  resource "httpx-sse" do
    url "https://files.pythonhosted.org/packages/4d/4e/fc8a90d4c5b0b8d3f3d8c3e3b8b4e3b8b4e3b8b4e3b8b4e3b8b4e3b8b4e3/httpx_sse-0.4.0.tar.gz"
    sha256 "1e81a0a3070ce322add10e58766e4f43c5e0b77508a82dddc46e0d1a6c0cdd7e"
  end

  resource "httpx" do
    url "https://files.pythonhosted.org/packages/78/82/08f8c936781f67d9e6b9eeb8a0c8b4e406136ea4c3d1f89a5db71d42e0e6/httpx-0.28.1.tar.gz"
    sha256 "75e98c5f16b0f35b567856f597f06ff2270a374470a5c2392242528e3e3e42fc"
  end

  resource "jsonschema" do
    url "https://files.pythonhosted.org/packages/0c/75/b5e41a3921e5e9af8c5c9a14fa8b267b5bfc6b699fb1c3e0e5d64b8e9d3b/jsonschema-4.23.0.tar.gz"
    sha256 "d71497fef26351a33265337fa77ffeb82423f3ea21283cd9467bb03999266bc4"
  end

  resource "pydantic-settings" do
    url "https://files.pythonhosted.org/packages/ea/a9/fa4ca6ca1c98ea52bc95e5dd44e6b0c0e0d1c3f1d9cb1e3c98c8f1c7b3c2/pydantic_settings-2.7.1.tar.gz"
    sha256 "2c5da7f8c54d6c0d0eaf0e8e0f1a2f3c8a4b1f9c6c8a1f7b0e1c1a4b0e1c1a4b"
  end

  resource "pyjwt" do
    url "https://files.pythonhosted.org/packages/79/84/0fdf9b18ba31d69877bd39c9cd6052b47f3761e9910c613d7f6b1c3e1f3d/pyjwt-2.10.1.tar.gz"
    sha256 "3cc5772eb20009233caf06e9d8a0577824723b44e6648ee0a2aedb6cf9381953"
  end

  resource "cryptography" do
    url "https://files.pythonhosted.org/packages/91/ce/78fc6c75f6c9ca4e0e2e9f0b77c8a4f3f3c8c7f3f3c8c7f3f3c8c7f3f3c8/cryptography-44.0.0.tar.gz"
    sha256 "cd5203a5e0c1c68f1a0e90d1ccf2d37eeefd5f2f9f3c8e2c5c2c5c2c5c2c5c2c"
  end

  resource "python-multipart" do
    url "https://files.pythonhosted.org/packages/a4/01/f3e8a87b9a00e1b19b1e0b2e0c9e0e0f1a9a0e0f1a9a0e0f1a9a0e0f1a9a/python_multipart-0.0.20.tar.gz"
    sha256 "74c5e8c5e78c6c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c"
  end

  resource "sse-starlette" do
    url "https://files.pythonhosted.org/packages/f8/21/f3e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8e8/sse_starlette-2.2.1.tar.gz"
    sha256 "a0c8e8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c"
  end

  resource "starlette" do
    url "https://files.pythonhosted.org/packages/1a/4c/9b5764bd22eec91c4039ef4c55334e9187085da6e9e4e6b8c8e7e7e7e7e7/starlette-0.44.0.tar.gz"
    sha256 "5a60c5c2d051f3a8eb546136aa0c9399773a689595e099e0877704d5888279bf"
  end

  resource "uvicorn" do
    url "https://files.pythonhosted.org/packages/6a/3c/21dba3e7c0a7b9b0e8d6e9e8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8/uvicorn-0.34.0.tar.gz"
    sha256 "404051050cd7e905de2c9a7e61790943440b3416e2a2a1c2e3e0e4c7c0c0c0c0"
  end

  resource "idna" do
    url "https://files.pythonhosted.org/packages/f1/70/7703c29685631f5a7590aa73f1f1d3fa9a380e654b86af429e0934a32f7d/idna-3.10.tar.gz"
    sha256 "12f65c9b470abda6dc35cf8e63cc574b1c52b11df2c86030af0ac09b01b13ea9"
  end

  resource "certifi" do
    url "https://files.pythonhosted.org/packages/0f/bd/1d41ee578ce09523c81a15426705dd20969f5abf006d1afe8aeff0dd776a/certifi-2024.12.14.tar.gz"
    sha256 "b650d30f370c2b724812bee08008d0d6c5ba7a7b1f6a7b0b1a8a1f71f3e6f3c3"
  end

  resource "httpcore" do
    url "https://files.pythonhosted.org/packages/6a/41/d7d0a89eb493922c37d343b607bc1b5da7f5be7e383740b4753ad8943e90/httpcore-1.0.7.tar.gz"
    sha256 "8551cb62a169ec7162ac7be8d4817d561f60e08eaa485234898414bb5a8a0b4c"
  end

  resource "h11" do
    url "https://files.pythonhosted.org/packages/f5/38/3af3d3633a34a3316095b39c8e8fb4853a28a536e55d347bd8d8e9a14b03/h11-0.14.0.tar.gz"
    sha256 "8f19fbbe99e72420ff35c00b27a34cb9937e902a8b810e2c88300c6f0a3b699d"
  end

  resource "sniffio" do
    url "https://files.pythonhosted.org/packages/a2/87/a6771e1546d97e7e041b6ae58d80074f81b7d5121207425c964ddf5cfdbd/sniffio-1.3.1.tar.gz"
    sha256 "f4324edc670a0f49750a81b895f35c3adb843cca46f0530f79fc1babb23789dc"
  end

  resource "jsonschema-specifications" do
    url "https://files.pythonhosted.org/packages/10/db/58f950c996c793472e336ff3655b13fbcf1e3b359dcf52dcf3ed3b52c352/jsonschema_specifications-2024.10.1.tar.gz"
    sha256 "0f38b83639958ce1152d02a7f062902c41c8fd20d558b0c34344292d417ae272"
  end

  resource "referencing" do
    url "https://files.pythonhosted.org/packages/99/5b/73ca1f8e72fff6fa52119dbd185f73a907b1989428917b24cff660129b6d/referencing-0.35.1.tar.gz"
    sha256 "25b42124a6c8b632a425174f24087783efb348a6f1e0008e63cd4466fedf703c"
  end

  resource "rpds-py" do
    url "https://files.pythonhosted.org/packages/01/80/cce854d0921ff2f0a9fa831ba3ad3c65cee3a46711addf39a2af52df2cfd/rpds_py-0.22.3.tar.gz"
    sha256 "e32fee8ab45d3c2db6da19a5323bc3362237c8b653c70194414b892fd06a080d"
  end

  resource "attrs" do
    url "https://files.pythonhosted.org/packages/fc/0f/aafca9af9315aee06a89ffde799a10a582fe8de76c563ee80bbcdc08b3fb/attrs-24.3.0.tar.gz"
    sha256 "8f5c07333d543103541ba7be0e2ce16eeee8130cb0b3f9238ab904ce1e85baff"
  end

  resource "six" do
    url "https://files.pythonhosted.org/packages/94/e7/b2c673351809dca68a0e064b6af791aa332cf192da575fd474ed7d6f16a2/six-1.17.0.tar.gz"
    sha256 "ff70335d468e7eb6ec65b95b99d3a2836546063f63acc5171de367e834932a81"
  end

  resource "click-plugins" do
    url "https://files.pythonhosted.org/packages/5f/1d/45434f64ed749540af821fd7e42b8e3d16cf1b2c762c1f6e0e1c1f0c1f0c/click-plugins-1.1.1.tar.gz"
    sha256 "46ab999744a9d831159c3411bb0c79346d94a444df9a3a3742e9ed63645f264b"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    # Test that the package is installed and can be imported
    system libexec/"bin/python", "-c", "import kuzu_memory; import click"
    # Test the CLI command
    assert_match version.to_s, shell_output("#{bin}/kuzu-memory --version")
  end
end
