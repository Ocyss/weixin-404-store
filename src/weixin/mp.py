from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from loguru import logger
from wechatpy import create_reply, parse_message
from wechatpy.exceptions import InvalidAppIdException, InvalidSignatureException
from wechatpy.utils import check_signature

from env import settings

router = APIRouter()


@router.get("/mp")
async def weixin_mp_verify(
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
    encrypt_type: Optional[str] = Query(None),
    msg_signature: Optional[str] = Query(None),
):
    """微信公众号服务器验证"""
    logger.info(
        f"公众号验证请求 - signature: {signature}, timestamp: {timestamp}, nonce: {nonce}"
    )

    try:
        check_signature(settings.weixin_mp.token, signature, timestamp, nonce)
        logger.info("公众号签名验证成功")
        return echostr
    except InvalidSignatureException:
        logger.error("公众号签名验证失败")
        raise HTTPException(status_code=403, detail="Invalid signature")


@router.post("/mp")
async def weixin_mp_message(
    request: Request,
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    encrypt_type: Optional[str] = Query(None),
    msg_signature: Optional[str] = Query(None),
):
    """处理微信公众号消息"""
    logger.info(
        f"收到公众号消息 - encrypt_type: {encrypt_type}, msg_signature: {msg_signature}"
    )

    try:
        check_signature(settings.weixin_mp.token, signature, timestamp, nonce)
    except InvalidSignatureException:
        logger.error("公众号签名验证失败")
        raise HTTPException(status_code=403, detail="Invalid signature")

    raw_data = await request.body()
    logger.debug(f"公众号原始消息: {raw_data}")

    try:
        decrypted_msg = settings.weixin_mp.crypto.decrypt_message(
            raw_data, msg_signature, timestamp, nonce
        )
        logger.debug(f"公众号解密后消息: {decrypted_msg}")
    except (InvalidSignatureException, InvalidAppIdException) as e:
        logger.error(f"公众号消息解密失败: {e}")
        raise HTTPException(status_code=403, detail="Message decryption failed")

    msg = parse_message(decrypted_msg)
    if msg is None:
        return

    logger.info(f"公众号解析消息类型: {msg.type}")

    if msg.type == "text":
        reply = create_reply(msg.content, msg)
        logger.info(f"公众号回复文本消息: {msg.content}")
    else:
        reply = create_reply("Sorry, can not handle this for now", msg)
        logger.info(f"公众号暂不支持的消息类型: {msg.type}")

    if reply:
        if isinstance(reply, str):
            return HTMLResponse(reply)
        encrypted_reply = settings.weixin_mp.crypto.encrypt_message(
            reply.render(), nonce, timestamp
        )
        return HTMLResponse(encrypted_reply)
