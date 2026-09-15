"""Export WeChat / Weixin 4.x custom emoticons from local data.

This package locates the local WeChat data directory, recovers the per-account
AES key from the running ``Weixin.exe`` process, decrypts the emoticon files and
(optionally) transcodes WeChat's proprietary ``.wxgf`` animated stickers to GIF.

The tool only ever *reads* WeChat data. It never modifies the WeChat database or
any file owned by WeChat.
"""

__version__ = "0.2.0"

__all__ = ["__version__"]
