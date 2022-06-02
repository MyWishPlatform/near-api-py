from setuptools import setup, find_packages

META_DATA = dict(
    name="near-api-py",
    version="0.2.0",
    license="MIT",

    author="NEAR Inc, MyWish.io",

    url="https://github.com/MyWishPlatform/near-api-py",

    packages=find_packages(),

    install_requires=["requests", "base58", "ed25519"]
)

if __name__ == "__main__":
    setup(**META_DATA)
