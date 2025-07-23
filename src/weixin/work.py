from fastapi import APIRouter, HTTPException, Query, Request
from loguru import logger
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.work import parse_message
from wechatpy.work.events import KFMsgOrEventEvent
from wechatpy.work.exceptions import InvalidCorpIdException

from env import settings
from model.key_value import KeyValue
from model.message import Message

router = APIRouter()


@router.get("/work")
async def weixin_work_verify(
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
):
    """企业微信服务器验证"""
    logger.info(
        f"企业微信验证请求 - msg_signature: {msg_signature}, timestamp: {timestamp}, nonce: {nonce}"
    )

    try:
        echo_str = settings.weixin_work.crypto.check_signature(
            msg_signature, timestamp, nonce, echostr
        )
        logger.info("企业微信签名验证成功")
        return echo_str
    except InvalidSignatureException:
        logger.error("企业微信签名验证失败")
        raise HTTPException(status_code=403, detail="Invalid signature")


@router.post("/work")
async def weixin_work_message(
    request: Request,
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
):
    """处理企业微信消息"""
    logger.info(f"收到企业微信消息 - msg_signature: {msg_signature}")

    raw_data = await request.body()
    logger.debug(f"企业微信原始消息: {raw_data}")

    try:
        decrypted_msg = settings.weixin_work.crypto.decrypt_message(
            raw_data, msg_signature, timestamp, nonce
        )
        logger.debug(f"企业微信解密后消息: {decrypted_msg}")
    except (InvalidSignatureException, InvalidCorpIdException) as e:
        logger.error(f"企业微信消息解密失败: {e}")
        raise HTTPException(status_code=403, detail="Message decryption failed")

    msg = parse_message(decrypted_msg)
    if msg is None:
        return

    if isinstance(msg, KFMsgOrEventEvent):
        logger.debug(f"企业微信客服消息: {msg}")
        cursorDoc = await KeyValue[str].get_config("message_cursor", "")

        message = settings.weixin_work.client.kf.sync_msg(
            msg.token, msg._data["OpenKfId"], cursor=cursorDoc.value, limit=1000
        )
        if errcode := message.get("errcode") != 0:
            logger.error(
                f"企业微信客服消息获取失败[{errcode}]: {message.get('errmsg')}"
            )
            return

        if next_cursor := message.get("next_cursor"):
            await cursorDoc.update_value(next_cursor)
        for msg in message.get("msg_list", []):
            await Message(**msg).insert()
    else:
        logger.debug(f"企业微信暂不支持的消息类型: {msg}")
