import logging
import sys
from functools import cached_property

from loguru import logger
from pydantic_settings import BaseSettings


class WeixinMpConfig(BaseSettings):
    token: str = ""
    encoding_aes_key: str = ""
    app_id: str = ""
    proxy: None | str = None  # TODO

    @cached_property
    def crypto(self):
        from wechatpy.crypto import WeChatCrypto

        return WeChatCrypto(
            self.token,
            self.encoding_aes_key,
            self.app_id,
        )

    class Config:
        env_prefix = "WEIXIN_MP_"


class WeixinWorkConfig(BaseSettings):
    corp_id: str = ""
    secret: str = ""

    token: str = ""
    encoding_aes_key: str = ""

    proxy: None | str = None

    @cached_property
    def crypto(self):
        from wechatpy.work.crypto import WeChatCrypto

        return WeChatCrypto(
            self.token,
            self.encoding_aes_key,
            self.corp_id,
        )

    @cached_property
    def client(self):
        from wechatpy.work import WeChatClient

        client = WeChatClient(
            self.corp_id,
            self.secret,
        )

        if self.proxy:
            client._http.proxies.update(
                {
                    "http": self.proxy,
                    "https": self.proxy,
                }
            )
        return client

    class Config:
        env_prefix = "WEIXIN_WORK_"


class LoggingConfig(BaseSettings):
    level: str = "WARN"

    class Config:
        env_prefix = "LOGGING_"


class MongoConfig(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 27017
    user: str = ""
    password: str = ""
    db_name: str = "weixin_404"

    class Config:
        env_prefix = "MONGO_"


class Settings(BaseSettings):
    weixin_mp: WeixinMpConfig = WeixinMpConfig()
    weixin_work: WeixinWorkConfig = WeixinWorkConfig()

    mongo: MongoConfig = MongoConfig()

    logging: LoggingConfig = LoggingConfig()
    host: str = "127.0.0.1"
    port: int = 5001

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


LOGGER_NAMES = (
    "LiteLLM Proxy",
    "LiteLLM Router",
    "LiteLLM",
)

LOGURU_FORMAT = "<g>{time:YY/MM/DD HH:mm:ss}</g> | <lvl>{level:.1s}</lvl> | <c>{name}:{function}:{line}</c> - <lvl>{message}</lvl>"


logger.remove()
logger.add(
    sys.stderr,
    format=LOGURU_FORMAT,
    colorize=True,
)


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def init_logging():
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(settings.logging.level)
    for logger_name in [
        *logging.root.manager.loggerDict.keys(),
        *LOGGER_NAMES,
    ]:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = []
        logging_logger.propagate = True
